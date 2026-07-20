# -*- coding: utf-8 -*-
"""临时脚本：用现有 renderer 生成一张 delivery_a5 样张 PDF 到桌面，供人工核对。
用完即删。走的是和真实打印完全相同的渲染路径（Jinja2 + Playwright/Chromium）。
"""
import os
from print_service import config, renderer, service

# 造一份接近真实的样例数据（5 个商品，含一个补货行）
data = {
    "brand_name": "小京鲜果",
    "customer": "米西水果店",
    "order_id": 7,
    "created_at": "2026-07-19 22:16",
    "items": [
        {"index": 1, "product_name": "国产油桃", "spec": "斤", "qty": 8,    "price": 12.00, "subtotal": 96.00,  "is_replacement": False},
        {"index": 2, "product_name": "青芒",     "spec": "斤", "qty": 20.2, "price": 5.00,  "subtotal": 101.00, "is_replacement": False},
        {"index": 3, "product_name": "泰国龙眼", "spec": "斤", "qty": 10.3, "price": 10.00, "subtotal": 103.00, "is_replacement": False},
        {"index": 4, "product_name": "赠品西瓜", "spec": "个", "qty": 1,    "price": 0.0,   "subtotal": 0.0,    "is_replacement": True},
        {"index": 5, "product_name": "红富士苹果", "spec": "斤", "qty": 5,  "price": 8.00,  "subtotal": 40.00,  "is_replacement": False},
    ],
    "total": 340,
}

paper_code = config.load_config().get("paper_size", "241x140")
width, height = service._resolve_paper(paper_code)
data = {**data, "paper": paper_code, "paper_width": width, "paper_height": height}

html = renderer.render_html("delivery_a5", data)

out = os.path.join(os.path.expanduser("~"), "Desktop", "sample_delivery_a5.pdf")
renderer.html_to_pdf(html, out, paper=paper_code)
print("PDF ->", out)
print("paper_code =", paper_code, " size =", width, "x", height, "mm")
