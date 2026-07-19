import sys, os
os.chdir("D:/code/HBProject/multi-brand-print-system/backend")
sys.path.insert(0, ".")
from print_service import renderer
data = {
    "brand_name":"测试品牌","customer":"长宁","order_id":1,
    "created_at":"2026-07-20 01:49",
    "items":[{"index":1,"product_name":"西瓜","spec":"斤","qty":1,"price":2.0,"subtotal":2.0,"is_replacement":False}],
    "total":2,"paper":"241x140","paper_width":241,"paper_height":139.5,
}
html = renderer.render_html("delivery_a5", data)
open("_preview.html","w",encoding="utf-8").write(html)
renderer.html_to_pdf(html, os.path.abspath("_preview.pdf"), paper="241x140")
import pymupdf
doc = pymupdf.open("_preview.pdf")
p = doc[0]
print("mm:", round(p.rect.width/72*25.4,1), "x", round(p.rect.height/72*25.4,1))
pix = p.get_pixmap(dpi=200)
pix.save("_preview.png")
print("saved", pix.width, pix.height)
