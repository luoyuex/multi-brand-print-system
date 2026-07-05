"""打印服务编排：单工作线程 + 渲染 → 打印。

对外暴露 submit()（同步执行，返回结果）与 print_test()。

为什么用单工作线程而不是简单的锁：
- Playwright 的 sync API 不能在 asyncio 事件循环线程里调用；
- 且浏览器实例必须始终由创建它的同一个线程驱动。
FastAPI 会把 `def` 路由丢到线程池，不同请求可能落在不同线程上，
若直接在这些线程里用共享的浏览器单例就会崩溃。

因此这里用一个专属的单线程执行器（max_workers=1）独占 Playwright：
- 所有渲染/打印都在这唯一的线程上执行 → 浏览器实例线程安全；
- 单线程天然串行 → 任务不会并发抢打印机；
- 路由线程通过 future.result() 阻塞等待结果。

打印流程：
  订单数据 → render_html → html_to_pdf(临时文件) → SumatraPDF 静默打印 → 清理临时文件
"""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from . import config, renderer, printer

# 专属单工作线程：独占 Playwright，保证同线程驱动 + 串行执行
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="print-worker")


def _do_print(template: str, data: dict, paper: str, printer_name: str, copies: int) -> None:
    """渲染 + 打印一份任务（运行在专属工作线程上）。"""
    data = {**data, "paper": paper}
    html = renderer.render_html(template, data)

    # 临时 PDF 文件
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix="print_")
    os.close(fd)
    try:
        renderer.html_to_pdf(html, pdf_path, paper=paper)
        printer.print_pdf(pdf_path, printer=printer_name, copies=copies)
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass


def submit(template: str, data: dict, *,
           printer_name: str = None,
           paper: str = None,
           copies: int = None) -> dict:
    """提交一个打印任务并同步等待完成。

    未显式传入的参数回退到 print_config.json 里的默认值。
    成功返回 {"ok": True}，失败抛出异常由上层转成 HTTP 错误。
    """
    cfg = config.load_config()
    printer_name = printer_name if printer_name is not None else cfg["default_printer"]
    paper = paper or cfg["paper"]
    copies = copies or cfg["copies"]

    # 丢到专属工作线程执行，阻塞等待其完成；异常会在 result() 处重新抛出
    future = _executor.submit(_do_print, template, data, paper, printer_name, copies)
    future.result()
    return {"ok": True}


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
    """应用退出时清理：关闭 Playwright 并停掉工作线程。"""
    # renderer 的关闭也必须在工作线程上执行（同线程驱动约束）
    try:
        _executor.submit(renderer.shutdown).result(timeout=10)
    except Exception:
        pass
    _executor.shutdown(wait=False)
