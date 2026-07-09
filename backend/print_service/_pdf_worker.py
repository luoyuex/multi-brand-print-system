"""通过独立子进程调用 Playwright 生成 PDF。

问题：Playwright sync API 不能在 asyncio 事件循环线程上运行，
而 uvicorn --reload 模式下所有路由都在事件循环线程上执行。
解决方案：用 subprocess 启动独立 Python 进程来运行 Playwright，
主进程只需等待子进程完成即可，完全绕开 asyncio 冲突。
"""

import sys
import json


def main():
    """
    从 stdin 读取 JSON: { html_path, pdf_path }
    用 Playwright 渲染 HTML 并生成 PDF。
    成功输出 JSON: { ok: true }
    失败输出 JSON: { ok: false, error: "..." }
    """
    try:
        data = json.loads(sys.stdin.read())
        html_path = data["html_path"]
        pdf_path = data["pdf_path"]

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(f"file:///{html_path.replace(chr(92), '/')}", wait_until="networkidle")
            page.pdf(
                path=pdf_path,
                prefer_css_page_size=True,
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()

        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
