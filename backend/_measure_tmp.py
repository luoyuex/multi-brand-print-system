import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from print_service import renderer, service

def count_pages(n):
    items = [{"index": i + 1, "product_name": f"品类{i+1}号", "spec": "件",
              "qty": i + 1, "price": 1.5, "subtotal": 1.5 * (i + 1)} for i in range(n)]
    data = {"brand_name": "miss", "customer": "古美", "order_id": 5,
            "created_at": "2026-07-06 17:19", "items": items, "total": 123}
    width, height = service._resolve_paper("241x140")
    data = {**data, "paper": "241x140", "paper_width": width, "paper_height": height}
    html = renderer.render_html("delivery_a5", data)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_measure_out.pdf")
    renderer.html_to_pdf(html, out, paper="241x140")
    raw = open(out, "rb").read()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    print(f"{n} items -> {pages} page(s)")

for n in (3, 11, 30, 60):
    count_pages(n)

try:
    os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_measure_out.pdf"))
except OSError:
    pass
print("cleaned")
