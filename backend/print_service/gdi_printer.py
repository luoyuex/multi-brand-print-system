"""用 pywin32 GDI 直接在打印机 DC 上绘制送货单。

背景见 docs/gdi-print-plan.md：针式打印机(EPSON LQ-730KII, 连续纸, 针孔在长边)
走 PDF/SumatraPDF 时方向和走纸都不可控。改为用 win32ui 创建打印机 Device Context，
直接用 GDI 画线画字：坐标系原点在可打印区左上角，x 沿 241mm 长边、y 沿 140mm 短边，
文字天然沿针孔长边水平走，无需旋转。一张凭证 = 一个 StartPage/EndPage，只走一页，
不吐整张。

本模块只负责「把送货单画到打印机」这一层，数据由 service.build_print_data() 提供，
不涉及 HTML / PDF / 任何子进程。

【本次修复要点】
1. 原代码只取了 LOGPIXELSY（纵向 DPI）一个值，横向、纵向坐标换算全部共用它。
   针式打印机横纵向物理分辨率往往不同，这会导致横向尺寸（页宽、列宽、外框
   横线长度）整体算错，误差随纸张尺寸放大，表现为"横线明显超出表格区域"。
   现在分别取 LOGPIXELSX / LOGPIXELSY，横向量用 mmx()，纵向量用 mmy()。
2. 画外框/横线时右边界用了 `x0 + table_w - 1`，但画竖线、写字用的是
   `x0 + table_w`，两处相差 1px，逻辑不统一。现在统一为同一个 right 值。
3. 画笔线宽如果 > 1px，GDI 简单画笔（cosmetic pen）默认是圆头端帽，端点会
   向外凸出半个线宽，边框转角处会看到"戳出去"的线头。现在固定为 1px 实线，
   如需更粗的线条，需改用 ExtCreatePen 并指定 PS_ENDCAP_FLAT（本文件未做，
   针式打印机 1px 通常已经足够清晰）。
4. 增加了一段可选的调试日志（DEBUG_PRINT_GEOMETRY 开关），方便核对
   canvas 尺寸换算成 mm 后是否与预期的 241mm x 140mm 纸张一致，
   便于快速定位"代码换算错" vs "驱动纸张设置错"。
"""

import win32con
import win32ui

# GetDeviceCaps 索引（见 wingdi.h）
_HORZRES = 8      # 可打印区宽（点）
_VERTRES = 10     # 可打印区高（点）
_LOGPIXELSX = 88  # 每英寸像素（横向 DPI）
_LOGPIXELSY = 90  # 每英寸像素（纵向 DPI）

_FONT_NAME = "Microsoft YaHei"
_FONT_WEIGHT = 700  # 粗体

# 六列相对宽度（占可打印区总宽的比例，和为 1）：序号 / 品种 / 数量 / 售价 / 金额 / 规格
_COL_FRACS = [0.08, 0.40, 0.12, 0.13, 0.15, 0.12]
_COL_TITLES = ["序号", "品种", "数量", "售价", "金额", "规格"]

# 明细最少行数：短单补空行铺满整页，观感与旧 HTML 版一致（行高按实际页高自适应）。
_MIN_BODY_ROWS = 13

# 各区字号（磅）
_SZ_META = 10.5
_SZ_HEAD = 10.5
_SZ_BODY = 10.0
_SZ_NOTE = 9.0
_SZ_TOTAL = 11.0

_NOTE_TEXT = "水果质量问题24小时内包赔"

# 页面留白(mm)
LEFT_MARGIN_MM = 2
RIGHT_MARGIN_MM = 10
TOP_MARGIN_MM = 1
BOTTOM_MARGIN_MM = 10

# 表格总宽(mm)。None = 用可打印区全宽减左右边距(旧行为)；
# 给具体数值则表格固定这么宽，右侧多出来的部分留白。
TABLE_WIDTH_MM = 200

# 排查"横线超出表格区域"之类问题时，把这个改成 True，会在控制台打印
# canvas / DPI 的换算结果，方便确认是代码算错了还是驱动纸张设置有问题。
DEBUG_PRINT_GEOMETRY = False


def print_delivery(data: dict, printer: str = None, copies: int = 1) -> None:
    """用 GDI 直接把送货单数据画到打印机 DC 上并输出。

    data:    service.build_print_data() 的产物。
    printer: 打印机名，None = 系统默认打印机。
    copies:  份数，每份 = 一个 StartPage/EndPage，只走一页。
    """
    dc = win32ui.CreateDC()
    if printer:
        dc.CreatePrinterDC(printer)
    else:
        dc.CreatePrinterDC()

    try:
        dc.StartDoc("送货单")
        try:
            for _ in range(max(1, int(copies or 1))):
                dc.StartPage()
                _draw_page(dc, data)
                dc.EndPage()
        finally:
            dc.EndDoc()
    finally:
        dc.DeleteDC()


def _draw_page(dc, data: dict) -> None:
    """在当前页(StartPage 之后)画出完整的一张送货单。"""
    # 横向、纵向分别取 DPI，不能共用一个值。
    dpi_x = dc.GetDeviceCaps(_LOGPIXELSX) or 180
    dpi_y = dc.GetDeviceCaps(_LOGPIXELSY) or 180

    def mmx(v):
        """毫米 -> 横向像素。"""
        return int(round(v / 25.4 * dpi_x))

    def mmy(v):
        """毫米 -> 纵向像素。"""
        return int(round(v / 25.4 * dpi_y))

    def pt(v):
        """磅 -> 像素（字体高度按纵向 DPI 换算）。"""
        return int(round(v / 72.0 * dpi_y))

    canvas_w = dc.GetDeviceCaps(_HORZRES)
    canvas_h = dc.GetDeviceCaps(_VERTRES)

    if DEBUG_PRINT_GEOMETRY:
        print(
            f"[gdi_printer] dpi_x={dpi_x} dpi_y={dpi_y} "
            f"canvas_w={canvas_w}px({canvas_w / dpi_x * 25.4:.1f}mm) "
            f"canvas_h={canvas_h}px({canvas_h / dpi_y * 25.4:.1f}mm)"
        )

    # 转换成打印机像素（横向用 mmx，纵向用 mmy）
    left = mmx(LEFT_MARGIN_MM)
    right_margin = mmx(RIGHT_MARGIN_MM)
    top = mmy(TOP_MARGIN_MM)
    bottom = mmy(BOTTOM_MARGIN_MM)

    # 表格起点
    x0 = left
    y0 = top

    # 实际绘制宽高：TABLE_WIDTH_MM 指定则固定该宽度，否则用全宽减左右边距。
    if TABLE_WIDTH_MM:
        table_w = mmx(TABLE_WIDTH_MM)
    else:
        table_w = canvas_w - left - right_margin
    table_h = canvas_h - top - bottom

    if DEBUG_PRINT_GEOMETRY:
        print(
            f"[gdi_printer] table_w={table_w}px({table_w / dpi_x * 25.4:.1f}mm) "
            f"table_h={table_h}px({table_h / dpi_y * 25.4:.1f}mm)"
        )

    items = data.get("items") or []
    body_rows = max(_MIN_BODY_ROWS, len(items))
    # 行分布：2 行表头(日期/客户) + 1 行列标题 + body 行 + 备注 + 总计
    total_rows = body_rows + 5
    row_h = table_h / total_rows

    # 行 y 边界（0..total_rows），用浮点行高逐行取整，保证整体铺满页高
    def row_y(i):
        return y0 + int(round(i * row_h))

    R_META1, R_META2, R_HEAD, R_BODY0 = 0, 1, 2, 3
    R_NOTE = R_BODY0 + body_rows
    R_TOTAL = R_NOTE + 1

    # 表格右边界：统一用这一个值，画线、画字都用它，避免 1px 误差。
    right = x0 + table_w

    # 列 x 边界（0..6）
    col_x = [x0]
    cum = 0.0
    for f in _COL_FRACS:
        cum += f
        col_x.append(x0 + int(round(cum * table_w)))
    col_x[-1] = right  # 消除累积误差，右边界对齐

    # ---- 画线 ----
    # 线宽固定为 1px：GDI 简单画笔线宽>1时端帽是圆头，会在线段端点外凸，
    # 边框转角、横线与外框交界处会看起来"戳出去"一截。1px 实线足够清晰。
    pen = win32ui.CreatePen(win32con.PS_SOLID, 1, 0)
    dc.SelectObject(pen)

    def line(ax, ay, bx, by):
        dc.MoveTo(ax, ay)
        dc.LineTo(bx, by)

    # 外框
    line(x0, y0, right, y0)
    line(x0, y0 + table_h, right, y0 + table_h)
    line(x0, y0, x0, y0 + table_h)
    line(right, y0, right, y0 + table_h)

    # 横向分隔线
    for i in range(1, total_rows):
        line(x0, row_y(i), right, row_y(i))

    # 竖向分隔线：表头区(2 行)只在标签列后有一条
    line(col_x[1], row_y(R_META1), col_x[1], row_y(R_HEAD))
    # 列标题 + 明细区：全部 6 列分隔线
    for k in range(1, 6):
        line(col_x[k], row_y(R_HEAD), col_x[k], row_y(R_NOTE))
    # 总计行：总计(前 4 列) | 金额(后 2 列) 之间一条分隔
    line(col_x[4], row_y(R_TOTAL), col_x[4], row_y(R_TOTAL + 1))

    # ---- 画字 ----
    dc.SetTextColor(0)
    dc.SetBkMode(win32con.TRANSPARENT)
    _fonts = {}  # 缓存字体对象（被 SelectObject 选中期间需保持存活）

    def use_font(size_pt):
        f = _fonts.get(size_pt)
        if f is None:
            f = win32ui.CreateFont({
                "name": _FONT_NAME,
                "height": -pt(size_pt),
                "weight": _FONT_WEIGHT,
            })
            _fonts[size_pt] = f
        dc.SelectObject(f)

    pad = mmx(1.5)

    def fit(text, max_w):
        """按像素宽度截断文本，超宽末尾加省略号。"""
        if not text:
            return ""
        if dc.GetTextExtent(text)[0] <= max_w:
            return text
        ell = "…"
        while text and dc.GetTextExtent(text + ell)[0] > max_w:
            text = text[:-1]
        return (text + ell) if text else ell

    def cell(text, left, right, row_top, align="c"):
        """在 [left,right] x [row_top,row_top+row_h] 的单元格里画文本。"""
        text = fit(str(text), right - left - 2 * pad)
        w, h = dc.GetTextExtent(text)
        if align == "l":
            tx = left + pad
        elif align == "r":
            tx = right - pad - w
        else:
            tx = left + (right - left - w) // 2
        ty = row_top + (int(round(row_h)) - h) // 2
        dc.TextOut(tx, ty, text)

    # 表头：日期 / 客户
    use_font(_SZ_META)
    cell("日期", col_x[0], col_x[1], row_y(R_META1))
    meta = f"{data.get('created_at', '')}    单号：#{data.get('order_id', '')}"
    cell(meta, col_x[1], right, row_y(R_META1), align="l")
    cell("客户", col_x[0], col_x[1], row_y(R_META2))
    cell(data.get("customer", ""), col_x[1], right, row_y(R_META2), align="l")

    # 列标题
    use_font(_SZ_HEAD)
    for k, title in enumerate(_COL_TITLES):
        cell(title, col_x[k], col_x[k + 1], row_y(R_HEAD))

    # 明细行
    use_font(_SZ_BODY)
    for r, it in enumerate(items):
        top = row_y(R_BODY0 + r)
        is_rep = it.get("is_replacement")
        name = it.get("product_name", "")
        if is_rep:
            name = f"{name}  补"
        cell(it.get("index", ""), col_x[0], col_x[1], top)
        cell(name, col_x[1], col_x[2], top, align="l")
        cell(it.get("qty", ""), col_x[2], col_x[3], top)
        if is_rep:
            cell("—", col_x[3], col_x[4], top)
            cell("—", col_x[4], col_x[5], top)
        else:
            cell(f"{float(it.get('price', 0)):.2f}", col_x[3], col_x[4], top)
            cell(f"{float(it.get('subtotal', 0)):.2f}", col_x[4], col_x[5], top)
        cell(it.get("spec", ""), col_x[5], col_x[6], top)

    # 备注（跨全行居中）
    use_font(_SZ_NOTE)
    cell(_NOTE_TEXT, col_x[0], right, row_y(R_NOTE))

    # 总计
    use_font(_SZ_TOTAL)
    cell("总计", col_x[0], col_x[4], row_y(R_TOTAL), align="r")
    cell(f"¥{float(data.get('total', 0)):.2f}", col_x[4], right, row_y(R_TOTAL))