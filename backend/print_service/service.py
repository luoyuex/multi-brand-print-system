"""打印服务编排：串行化打印队列 + 编排「构造数据 → 送打印机」。

对外暴露 submit() 与 print_test()。

送货单走 gdi_printer：pywin32 直接在打印机 DC 上绘制，方向和走纸由代码定死
（背景见 docs/gdi-print-plan.md）。账单小票仍走 renderer 的 Playwright 截图路径。

打印任务用一把 threading.Lock 串行化，保证不并发（针式连续纸不能并发送纸）。
"""

import os
import tempfile
import threading

from . import config, renderer, gdi_printer


def build_print_data(order) -> dict:
    """把订单模型（models.Order）转成打印模板所需的数据结构。

    单打路由与一键批量打印共用，保证两条路径打出的凭证格式完全一致。

    - 单价/小计保留两位小数（模板里再格式化）；
    - 合计取整（与前端页面显示一致）；
    - 数量为整数时去掉小数尾巴，显示更干净；
    - 补货行免费补发：单价/小计强制为 0，不计入合计。
    """
    def fmt_qty(q):
        f = float(q)
        return int(f) if f == int(f) else round(f, 2)

    items = []
    total = 0.0
    for i, it in enumerate(order.items, start=1):
        is_replacement = bool(it.is_replacement)
        qty = float(it.qty)
        price = 0.0 if is_replacement else float(it.price)
        subtotal = price * qty
        total += subtotal
        items.append({
            "index": i,
            "product_name": it.product_name,
            "spec": it.spec or "",
            "qty": fmt_qty(qty),
            "price": price,
            "subtotal": subtotal,
            "is_replacement": is_replacement,
        })

    created = order.created_at
    created_str = created.strftime("%Y-%m-%d %H:%M") if created else ""

    return {
        "brand_name": order.brand_name,
        "customer": order.customer,
        "order_id": order.id,
        "created_at": created_str,
        "items": items,
        "total": round(total),
    }


def build_bill_render_data(bill) -> dict:
    """把账单模型（models.Bill）转成小票模板 bill.html 所需的数据，按天分组。

    - 明细已在出账时快照进 bill.items（含补货免费规则），这里只做展示格式化；
    - 数量整数去尾；金额是整数则不显示小数尾巴，更像小票；
    - 单天账单不显示每日小计，多天账单每天一段并带当日小计。
    """
    def fmt_qty(q):
        f = float(q or 0)
        return int(f) if f == int(f) else round(f, 2)

    def money(v):
        f = float(v or 0)
        return str(int(f)) if f == int(f) else f"{f:.2f}"

    weekdays = ["一", "二", "三", "四", "五", "六", "日"]

    days = {}   # date -> 分组；bill.items 落库时按订单时间顺序写入，天然有序
    total = 0.0
    for it in bill.items:
        d = it.order_date
        key = d.isoformat() if d else "-"
        day = days.setdefault(key, {"date": d, "items": [], "subtotal": 0.0})
        sub = float(it.subtotal or 0)
        day["items"].append({
            "product_name": it.product_name or "",
            "spec": it.spec or "",
            "qty_str": str(fmt_qty(it.qty)),
            "price_str": money(it.price),
            "subtotal_str": money(sub),
            "is_replacement": bool(it.is_replacement),
        })
        day["subtotal"] += sub
        total += sub

    day_list = []
    for d in days.values():
        dt = d["date"]
        day_list.append({
            "date_str": dt.strftime("%m-%d") if dt else "",
            "weekday": weekdays[dt.weekday()] if dt else "",
            "count": len(d["items"]),
            "lines": d["items"],   # 用 lines 命名，避开 Jinja 里 day.items 撞 dict.items 方法名
            "subtotal_str": money(d["subtotal"]),
        })

    ps, pe = bill.period_start, bill.period_end
    created = bill.created_at
    return {
        "brand_name": bill.brand_name or "",
        "customer": bill.customer or "",
        "bill_id": bill.id,
        "period_start": ps.strftime("%Y-%m-%d") if ps else "",
        "period_end": pe.strftime("%Y-%m-%d") if pe else "",
        "single_day": ps == pe,
        "order_count": bill.order_count,
        "days": day_list,
        "total_str": money(total),
        "paid": bool(bill.paid),
        "generated_at": created.strftime("%Y-%m-%d %H:%M") if created else "",
    }


def render_bill_image(bill) -> bytes:
    """渲染账单小票为 PNG 字节流（供路由以 image/png 返回）。

    走 renderer.html_to_image（独立 Playwright 子进程截图），不经过打印机、
    不占用 print_lock，各请求独立互不影响。
    """
    data = build_bill_render_data(bill)
    html = renderer.render_html("bill", data)

    fd, img_path = tempfile.mkstemp(suffix=".png", prefix="bill_")
    os.close(fd)
    try:
        renderer.html_to_image(html, img_path)
        with open(img_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(img_path)
        except OSError:
            pass

# 串行锁：保证打印任务不并发（单打接口与一键批量打印共用同一把锁，
# 避免两条路径同时往打印机送任务导致针式连续纸走纸错乱）。
print_lock = threading.Lock()


def resolve_print_settings(printer_name: str = None,
                           copies: int = None) -> dict:
    """把「未指定」的打印参数用配置补齐，返回 {printer_name, copies}。

    单打与批量打印共用，保证两条路径解析规则一致。
    （纸张由 GDI 直接读打印机 DC 的实际可打印区，不再需要 paper_size。）
    """
    cfg = config.load_config()
    return {
        "printer_name": printer_name if printer_name is not None else cfg["default_printer"],
        "copies": copies or cfg["copies"],
    }


def render_and_print(data: dict, printer_name: str, copies: int) -> dict:
    """送打印机（不持锁、不等待出纸）。

    这是最底层的打印原语：调用方负责持有 print_lock 串行化，
    以及（批量场景下）打印后调用 printer.wait_until_idle 等待出纸完成。

    送货单走 gdi_printer.print_delivery：pywin32 直接在打印机 DC 上绘制，
    方向和走纸由代码定死，不经过 HTML/PDF/子进程。
    """
    gdi_printer.print_delivery(data, printer=printer_name or None, copies=copies)
    return {"ok": True}


def submit(data: dict, *,
           printer_name: str = None,
           copies: int = None) -> dict:
    """提交一个打印任务并同步等待完成（单打路径）。"""
    s = resolve_print_settings(printer_name, copies)
    with print_lock:
        return render_and_print(data, s["printer_name"], s["copies"])


def print_test(printer_name: str = None) -> dict:
    """打印一张测试页，用于验证打印机连通性。"""
    data = {
        "brand_name": "打印测试",
        "customer": "测试客户",
        "order_id": 0,
        "created_at": "—",
        "items": [
            {"index": 1, "product_name": "测试商品", "spec": "个",
             "qty": 1, "price": 1.00, "subtotal": 1.00},
        ],
        "total": 1,
    }
    return submit(data, printer_name=printer_name, copies=1)


def shutdown() -> None:
    """应用退出时清理：关闭 Playwright。"""
    renderer.shutdown()
