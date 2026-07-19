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
    从 stdin 读取 JSON:
      PDF 模式（打印）: { html_path, pdf_path }
      截图模式（账单小票图片）: { html_path, img_path }
    用 Playwright 渲染 HTML，生成 PDF 或 PNG。
    成功输出 JSON: { ok: true }
    失败输出 JSON: { ok: false, error: "..." }
    """
    try:
        data = json.loads(sys.stdin.read())
        html_path = data["html_path"]
        file_url = f"file:///{html_path.replace(chr(92), '/')}"

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])

            if data.get("img_path"):
                # 截图模式：小票是固定窄幅（body 420px），只截 body 元素，
                # 避免默认 1280 视口把小票截成一角带大片留白。device_scale_factor=2 更清晰。
                ctx = browser.new_context(
                    viewport={"width": 460, "height": 900},
                    device_scale_factor=2,
                )
                page = ctx.new_page()
                page.goto(file_url, wait_until="networkidle")
                body = page.query_selector("body")
                if body:
                    body.screenshot(path=data["img_path"])
                else:
                    page.screenshot(path=data["img_path"], full_page=True)
            else:
                page = browser.new_page()
                page.goto(file_url, wait_until="networkidle")
                page.pdf(
                    path=data["pdf_path"],
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
