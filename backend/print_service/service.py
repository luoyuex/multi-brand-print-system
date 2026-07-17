"""打印服务编排：独立线程 + 渲染 → 打印。

对外暴露 submit() 与 print_test()。

Playwright sync API 不能在 asyncio 事件循环线程里执行（会抛 NotImplementedError），
而 FastAPI 的 def 路由有时会被 uvicorn 放在事件循环线程上执行，
所以统一用独立线程执行打印任务，彻底避免线程冲突。

打印任务用一把 threading.Lock 串行化，保证不并发。
"""

import os
import tempfile
import threading

from . import config, renderer, printer

# 串行锁：保证打印任务不并发
_print_lock = threading.Lock()

# 纸张尺寸代码 → (宽mm, 高mm) 映射
PAPER_SIZES = {
    "241x140": (241, 139.5), # 一联记账凭证（横版，方向与纸一致）：默认，商品行沿走纸方向向下、超页自动续联
    "140x241": (140, 241),   # 旧竖版渲染（打印时旋转90°回到走纸140），保留兼容
    "241x280": (241, 279),   # 二联记账凭证（整切）
    "A5":      (148, 210),
    "A4":      (210, 297),
}


def _resolve_paper(paper_code: str):
    """把纸张代码解析成 (宽mm, 高mm)。"""
    if paper_code in PAPER_SIZES:
        return PAPER_SIZES[paper_code]
    # 兼容自定义格式 "宽x高"，如 "241x140"
    try:
        parts = paper_code.lower().split("x")
        if len(parts) == 2:
            return (float(parts[0]), float(parts[1]))
    except (ValueError, AttributeError):
        pass
    # 默认一联记账凭证（横版 241x140，方向与纸一致，无需旋转）
    return PAPER_SIZES["241x140"]


def _do_print(template: str, data: dict, paper_code: str, printer_name: str, copies: int) -> dict:
    """渲染 + 打印一份任务（持锁执行）。"""
    width, height = _resolve_paper(paper_code)
    data = {**data, "paper": paper_code, "paper_width": width, "paper_height": height}
    html = renderer.render_html(template, data)

    fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix="print_")
    os.close(fd)
    try:
        renderer.html_to_pdf(html, pdf_path, paper=paper_code)
        printer.print_pdf(pdf_path, printer=printer_name or None, copies=copies)
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass
    return {"ok": True}


def _run_in_new_thread(fn, *args, **kwargs):
    """在新建线程中执行 fn，阻塞等待结果，异常会重新抛出。"""
    result = [None]
    exc = [None]

    def _worker():
        try:
            result[0] = fn(*args, **kwargs)
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=_worker, name="print-async-helper")
    t.start()
    t.join()
    if exc[0] is not None:
        raise exc[0]
    return result[0]


def submit(template: str, data: dict, *,
           printer_name: str = None,
           paper_size: str = None,
           copies: int = None) -> dict:
    """提交一个打印任务并同步等待完成。"""
    cfg = config.load_config()
    printer_name = printer_name if printer_name is not None else cfg["default_printer"]
    paper_size = paper_size or cfg.get("paper_size", "241x140")
    copies = copies or cfg["copies"]

    with _print_lock:
        return _do_print(template, data, paper_size, printer_name, copies)


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
    return submit("delivery_a5", data, printer_name=printer_name, copies=1)


def shutdown() -> None:
    """应用退出时清理：关闭 Playwright。"""
    renderer.shutdown()
