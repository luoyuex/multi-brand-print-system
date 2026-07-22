"""模板渲染：Jinja2 填充 HTML → Playwright 子进程截图（账单小票用）。

送货单已改走 gdi_printer（pywin32 直接绘制），不再经过 HTML/PDF。
本模块现在只服务账单小票 bill.html：渲染成 HTML 再由独立子进程截图成 PNG。

通过启动独立 Python 子进程运行 Playwright，彻底避免 asyncio 事件循环冲突
（uvicorn --reload 模式下 sync API 不能在事件循环线程上运行）。
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_WORKER_SCRIPT = Path(__file__).resolve().parent / "_pdf_worker.py"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_html(template: str, data: dict) -> str:
    """渲染模板为 HTML 字符串。"""
    tpl = _env.get_template(f"{template}.html")
    return tpl.render(**data)


def html_to_image(html: str, out_path: str) -> str:
    """把 HTML 渲染成 PNG 图片写到 out_path，返回该路径（账单小票图片用）。

    通过独立子进程运行 Playwright 截图，绕开 asyncio 事件循环冲突。
    """
    fd, html_path = tempfile.mkstemp(suffix=".html", prefix="bill_")
    os.close(fd)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        result = subprocess.run(
            [sys.executable, str(_WORKER_SCRIPT)],
            input=json.dumps({"html_path": html_path, "img_path": out_path}),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            creationflags=_no_window_flag(),
        )

        if not os.path.isfile(out_path):
            err = result.stderr or result.stdout or "无输出"
            raise RuntimeError(f"图片生成失败: {err[:300]}")

    finally:
        try:
            os.remove(html_path)
        except OSError:
            pass

    return out_path


def shutdown():
    """兼容接口：子进程模式无需关闭。"""
    pass


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
