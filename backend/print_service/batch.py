"""一键批量打印：后台 worker 线程串行处理多张订单，进度可被 SSE 订阅。

设计要点：
- 严格串行：所有打印任务与单打共用 service.print_lock，绝不并发送打印机。
- 等出纸：每打一单后 printer.wait_until_idle 轮询队列清空，确认针式连续纸
  真正走完再送下一单，避免任务堆积、走纸错乱。
- 失败跳过：某单打印机异常（离线/缺纸/卡纸）或渲染失败时，标记该单失败并
  继续下一单，不阻断整批。
- 进度可观测：每张订单状态变化都会 bump 一个版本号，SSE 端轮询版本号推送快照。

批量状态只存在内存里（_batches），进程重启即清空——批量打印是即时操作，
不需要持久化；订单本身的 printed 状态已落库。
"""

import threading
import time
import uuid
from datetime import datetime

from . import config, service, printer

# batch_id -> Batch，进程内存储
_batches = {}
_lock = threading.Lock()

# 每单打印后等待出纸的超时（秒）。针式打印一联凭证通常几秒内走完，
# 60s 足够；超时后不再无限等待，直接进入下一单（视为已送出）。
_WAIT_IDLE_TIMEOUT = 60.0


class Batch:
    """一次批量打印任务的内存状态。

    items 里每个元素形如：
        {order_id, customer, brand_name, status, error}
    status: queued | printing | printed | failed | skipped
    """

    def __init__(self, batch_id, printer_name, items):
        self.id = batch_id
        self.printer_name = printer_name
        self.items = items
        self.created_at = datetime.now()
        self.done = False
        # 版本号：任何状态变化 +1，SSE 端据此判断是否有新进度要推送
        self.version = 0
        self._cond = threading.Condition()

    def bump(self):
        """状态有变动时调用：递增版本号并唤醒等待的订阅者。"""
        with self._cond:
            self.version += 1
            self._cond.notify_all()

    def wait_for_change(self, since_version, timeout):
        """阻塞等待版本号超过 since_version，或超时。返回当前版本号。

        SSE 生成器用它实现「有变化立即推送、无变化则超时发心跳」。
        """
        with self._cond:
            if self.version > since_version:
                return self.version
            self._cond.wait(timeout=timeout)
            return self.version

    def snapshot(self):
        """返回可 JSON 序列化的进度快照。"""
        total = len(self.items)
        done_cnt = sum(1 for it in self.items
                       if it["status"] in ("printed", "failed", "skipped"))
        printed_cnt = sum(1 for it in self.items if it["status"] == "printed")
        failed_cnt = sum(1 for it in self.items
                         if it["status"] in ("failed", "skipped"))
        return {
            "batch_id": self.id,
            "version": self.version,
            "done": self.done,
            "total": total,
            "processed": done_cnt,
            "printed": printed_cnt,
            "failed": failed_cnt,
            "items": [dict(it) for it in self.items],
        }


def _set_item(batch, order_id, **fields):
    """更新某单状态并 bump 版本。"""
    for it in batch.items:
        if it["order_id"] == order_id:
            it.update(fields)
            break
    batch.bump()


def _worker(batch, template):
    """后台线程：串行处理批量里的每一张订单。"""
    # worker 线程内用独立 DB session，避免跨线程复用请求级 session。
    from database import SessionLocal
    import crud

    s = service.resolve_print_settings(printer_name=batch.printer_name)
    printer_name = s["printer_name"]
    paper_size = s["paper_size"]
    copies = s["copies"]

    db = SessionLocal()
    try:
        for it in batch.items:
            order_id = it["order_id"]
            _set_item(batch, order_id, status="printing", error="")

            order = crud.get_order(db, order_id)
            if not order:
                _set_item(batch, order_id, status="failed", error="订单不存在")
                continue

            # 打印前查打印机状态：离线/缺纸/卡纸等致命状态直接跳过本单。
            st = printer.get_status(printer_name)
            if st["ok"] and not st["ready"]:
                _set_item(batch, order_id, status="skipped",
                          error=f"打印机{st['reason']}")
                continue

            data = service.build_print_data(order)
            try:
                # 与单打共用同一把锁，全局串行；打印后等出纸完成再放下一单。
                with service.print_lock:
                    service.render_and_print(template, data, paper_size,
                                             printer_name, copies)
                    printer.wait_until_idle(printer_name,
                                            timeout=_WAIT_IDLE_TIMEOUT)
            except Exception as e:
                _set_item(batch, order_id, status="failed",
                          error=f"{type(e).__name__}: {e}")
                continue

            # 出纸成功，落库标记已打印。
            try:
                crud.mark_printed(db, order_id)
            except Exception:
                db.rollback()
            _set_item(batch, order_id, status="printed", error="")
    finally:
        db.close()
        batch.done = True
        batch.bump()


def start_batch(orders, printer_name=None, template="delivery_a5"):
    """创建批量任务并启动后台 worker。

    orders: [{order_id, customer, brand_name}, ...]，调用方（路由）从 DB 查好传入，
    保证顺序即打印顺序。

    返回新批次的初始快照。
    """
    batch_id = uuid.uuid4().hex
    items = [{
        "order_id": o["order_id"],
        "customer": o.get("customer", ""),
        "brand_name": o.get("brand_name", ""),
        "status": "queued",
        "error": "",
    } for o in orders]

    batch = Batch(batch_id, printer_name, items)
    with _lock:
        _batches[batch_id] = batch

    t = threading.Thread(target=_worker, args=(batch, template),
                         name=f"print-batch-{batch_id[:8]}", daemon=True)
    t.start()
    return batch.snapshot()


def get_batch(batch_id):
    """按 id 取批次对象，不存在返回 None。"""
    with _lock:
        return _batches.get(batch_id)


def cleanup_old(max_age_seconds=3600):
    """清理超过 max_age 且已完成的批次，防止内存无限增长。"""
    now = time.time()
    with _lock:
        stale = [bid for bid, b in _batches.items()
                 if b.done and (now - b.created_at.timestamp()) > max_age_seconds]
        for bid in stale:
            del _batches[bid]
