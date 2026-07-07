"""模板渲染：Jinja2 填充 HTML → Chromium 命令行转 PDF。

不使用 Playwright Python API（它在 asyncio 事件循环线程上会抛 NotImplementedError），
而是直接调用 Chromium 可执行文件的 --print-to-pdf 参数生成 PDF，
完全绕开 asyncio 兼容性问题。
"""

import os
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def _find_chromium() -> str:
    """动态查找 Chromium 可执行文件路径。"""
    # 1. 环境变量指定
    env_path = os.environ.get("CHROMIUM_PATH", "")
    if env_path and os.path.isfile(env_path):
        return env_path
    # 2. Playwright 安装目录
    pw_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
    if pw_dir.exists():
        for d in sorted(pw_dir.glob("chromium-*")):
            chrome = d / "chrome-win" / "chrome.exe"
            if chrome.is_file():
                return str(chrome)
    return ""


def render_html(template: str, data: dict) -> str:
    """渲染模板为 HTML 字符串。"""
    tpl = _env.get_template(f"{template}.html")
    return tpl.render(**data)


def html_to_pdf(html: str, out_path: str, paper: str = "241x140") -> str:
    """把 HTML 渲染成 PDF 写到 out_path，返回该路径。

    直接调用 Chromium --print-to-pdf，不依赖 Playwright Python API，
    彻底避免 asyncio 事件循环兼容性问题。
    """
    # 1. 写 HTML 到临时文件（Chromium 需要文件路径或 URL）
    import tempfile
    fd, html_path = tempfile.mkstemp(suffix=".html", prefix="print_")
    os.close(fd)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        # 2. 调 Chromium 生成 PDF
        chrome = _find_chromium()
        if not chrome:
            raise RuntimeError(
                "Chromium 未找到。请运行: playwright install chromium"
            )

        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={out_path}",
            "--print-to-pdf-no-header",     # 不加 Chrome 默认页眉页脚
            html_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
            creationflags=_no_window_flag(),
        )
        # Chromium headless 返回码 0 表示成功
        if not os.path.isfile(out_path):
            raise RuntimeError(
                f"Chromium PDF 生成失败 (code {result.returncode}): "
                f"{result.stderr.decode('gbk', errors='replace')[:300] if result.stderr else '无输出'}"
            )
    finally:
        try:
            os.remove(html_path)
        except OSError:
            pass

    return out_path


def ensure_initialized():
    """兼容接口：Chromium 命令行模式无需预初始化，此函数为空操作。"""
    pass


def shutdown():
    """兼容接口：Chromium 命令行模式无需关闭，此函数为空操作。"""
    pass


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
