import os
os.chdir("D:/code/HBProject/multi-brand-print-system/backend")
from print_service import renderer
data = {
    "brand_name": "测试品牌", "customer": "长宁", "order_id": 1,
    "created_at": "2026-07-20 01:49",
    "items": [{"index": 1, "product_name": "西瓜", "spec": "斤", "qty": 1, "price": 2.0, "subtotal": 2.0, "is_replacement": False}],
    "total": 2, "paper": "241x140", "paper_width": 241, "paper_height": 139.5,
}
html = renderer.render_html("delivery_a5", data)
renderer.html_to_pdf(html, "_chk.pdf", paper="241x140")
import pymupdf
d = pymupdf.open("_chk.pdf")
print("pages:", d.page_count)
for i,p in enumerate(d):
    r = p.rect
    print(i, round(r.width/72*25.4,1), "x", round(r.height/72*25.4,1), "mm")
