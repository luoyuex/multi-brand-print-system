"""打印服务编排：串行化打印队列 + 编排「构造数据 → 送打印机」。

对外暴露 submit() 与 print_test()。

送货单走 gdi_printer：pywin32 直接在打印机 DC 上绘制，方向和走纸由代码定死
（背景见 docs/gdi-print-plan.md）。账单小票图片改由前端 html2canvas 生成，后端不再渲染。

打印任务用一把 threading.Lock 串行化，保证不并发（针式连续纸不能并发送纸）。
"""

import threading

from . import config, gdi_printer


def build_print_data(order) -> dict:
    """把订单模型（models.Order）转成打印模板所需的数据结构。

    单打路由与一键批量打印共用，保证两条路径打出的凭证格式完全一致。

    - 单价/小计保留两位小数（模板里再格式化）；
    - 合计保留两位小数（与前端页面显示一致）；
    - 数量为整数时去掉小数尾巴，显示更干净；
    - 补货行免费补发：单价/小计强制为 0，不计入合计。
    """
    def fmt_qty(q):
        f = float(q)
        return int(f) if f == int(f) else round(f, 2)

    # 小票上商品倒序展示：先录入的排在后面（最新录入在最上）。
    items = []
    total = 0.0
    for i, it in enumerate(reversed(order.items), start=1):
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
        "total": round(total, 2),
    }


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
    """应用退出时清理：GDI 直接打印无需清理，保留接口兼容 main.py 的 shutdown 钩子。"""
    pass
