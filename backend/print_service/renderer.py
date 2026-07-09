"""模板渲染：Jinja2 填充 HTML → Playwright 子进程转 PDF。

通过启动独立 Python 子进程来运行 Playwright，
彻底避免 asyncio 事件循环冲突（uvicorn --reload 模式下的问题）。
子进程没有 asyncio 事件循环，Playwright sync API 可以正常工作，
且 page.pdf() 支持 @page { size } 自定义纸张尺寸。
"""

import json
import os
import subprocess
import sys
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


def html_to_pdf(html: str, out_path: str, paper: str = "241x140") -> str:
    """把 HTML 渲染成 PDF 写到 out_path，返回该路径。

    通过独立子进程运行 Playwright，避免 asyncio 事件循环冲突。
    Playwright 的 page.pdf() 支持 @page { size } 自定义纸张尺寸。
    """
    import tempfile

    # 1. 写 HTML 到临时文件
    fd, html_path = tempfile.mkstemp(suffix=".html", prefix="print_")
    os.close(fd)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        # 2. 启动子进程运行 Playwright
        python_exe = sys.executable
        result = subprocess.run(
            [python_exe, str(_WORKER_SCRIPT)],
            input=json.dumps({"html_path": html_path, "pdf_path": out_path}),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            creationflags=_no_window_flag(),
        )

        if not os.path.isfile(out_path):
            err = result.stderr or result.stdout or "无输出"
            raise RuntimeError(f"PDF 生成失败: {err[:300]}")

        # 检查子进程返回的结果
        try:
            resp = json.loads(result.stdout.strip())
            if not resp.get("ok"):
                raise RuntimeError(f"Playwright 报错: {resp.get('error', '未知错误')}")
        except (json.JSONDecodeError, ValueError):
            pass  # 子进程可能没输出 JSON，但 PDF 文件已生成即可

    finally:
        try:
            os.remove(html_path)
        except OSError:
            pass

    return out_path


def ensure_initialized():
    """兼容接口：子进程模式无需预初始化。"""
    pass


def shutdown():
    """兼容接口：子进程模式无需关闭。"""
    pass


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
