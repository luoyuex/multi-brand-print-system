"""模板渲染：Jinja2 填充 HTML → Playwright(Chromium) 转 PDF。

- render_html(): 把订单数据注入 HTML 模板，返回 HTML 字符串。
- html_to_pdf(): 用 headless Chromium 把 HTML 渲染成 PDF 文件（A4/A5）。

Playwright 的浏览器实例较重，这里在进程内复用单例，避免每次打印都冷启动。
"""

from pathlib import Path
from threading import Lock

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

# Playwright 单例（懒加载）
_pw = None
_browser = None
_pw_lock = Lock()


def render_html(template: str, data: dict) -> str:
    """渲染模板为 HTML 字符串。

    template: 模板名（不含扩展名），如 'delivery_a5'。
    data: 注入变量（brand_name, customer, order_id, created_at, items, total, paper）。
    """
    tpl = _env.get_template(f"{template}.html")
    return tpl.render(**data)


def _ensure_browser():
    """懒加载并复用 Chromium 实例。"""
    global _pw, _browser
    if _browser is not None and _browser.is_connected():
        return _browser
    with _pw_lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        from playwright.sync_api import sync_playwright
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(args=["--no-sandbox"])
        return _browser


def html_to_pdf(html: str, out_path: str, paper: str = "A5") -> str:
    """把 HTML 渲染成 PDF 写到 out_path，返回该路径。

    纸张大小由 CSS @page 控制，这里 prefer_css_page_size=True 让其生效。
    """
    browser = _ensure_browser()
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=out_path,
            prefer_css_page_size=True,   # 用模板里 @page 的尺寸
            print_background=True,
        )
    finally:
        page.close()
    return out_path


def shutdown():
    """关闭 Playwright（应用退出时调用）。"""
    global _pw, _browser
    with _pw_lock:
        if _browser is not None:
            try:
                _browser.close()
            except Exception:
                pass
            _browser = None
        if _pw is not None:
            try:
                _pw.stop()
            except Exception:
                pass
            _pw = None
