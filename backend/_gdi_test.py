"""GDI 直接画标定页：完全绕开 PDF/SumatraPDF，直接往打印机 DC 上画。

验证两件事：
1. 方向 —— 文字是否沿针孔那条长边(241mm)水平正着走。
2. 走纸 —— 打完是否只走一页(约140mm)，不吐整张。

坐标单位 = 设备点(180 DPI)。mm→dots = mm/25.4*180。
"""

import win32ui
import win32con

PRINTER = "EPSON LQ-730KII ESC/P2"
DPI = 180


def mm(v):
    return int(round(v / 25.4 * DPI))


def pt(v):
    # 磅→设备点：pt/72*DPI
    return int(round(v / 72.0 * DPI))


def main():
    dc = win32ui.CreateDC()
    dc.CreatePrinterDC(PRINTER)

    # 可打印区尺寸(点)
    HORZRES = dc.GetDeviceCaps(8)
    VERTRES = dc.GetDeviceCaps(10)
    print(f"printable dots: {HORZRES} x {VERTRES}")

    dc.StartDoc("GDI orient test")
    dc.StartPage()

    # 边框：用黑笔画可打印区边界
    pen = win32ui.CreatePen(win32con.PS_SOLID, mm(0.4), 0)
    dc.SelectObject(pen)
    dc.MoveTo(2, 2)
    for x, y in [(HORZRES - 3, 2), (HORZRES - 3, VERTRES - 3),
                 (2, VERTRES - 3), (2, 2)]:
        dc.LineTo(x, y)

    dc.SetTextColor(0)
    dc.SetBkMode(win32con.TRANSPARENT)

    def draw_centered(text, y, size_pt, weight=700):
        font = win32ui.CreateFont({
            "name": "Microsoft YaHei",
            "height": -pt(size_pt),
            "weight": weight,
        })
        dc.SelectObject(font)
        w, _h = dc.GetTextExtent(text)
        dc.TextOut((HORZRES - w) // 2, y, text)

    def draw_at(text, x, y, size_pt):
        font = win32ui.CreateFont({
            "name": "Microsoft YaHei",
            "height": -pt(size_pt),
            "weight": 700,
        })
        dc.SelectObject(font)
        dc.TextOut(x, y, text)

    draw_centered("↑ 上 TOP ↑", mm(8), 30)
    draw_centered("这行文字应该沿针孔长边水平正着读", VERTRES // 2 - pt(16), 20)
    draw_centered(f"GDI  {HORZRES}x{VERTRES}dots  180dpi", VERTRES - mm(14), 12)

    # 四角标记
    draw_at("A", mm(4), mm(4), 18)
    draw_at("B", HORZRES - mm(12), mm(4), 18)
    draw_at("C", mm(4), VERTRES - mm(14), 18)
    draw_at("D", HORZRES - mm(12), VERTRES - mm(14), 18)

    dc.EndPage()
    dc.EndDoc()
    dc.DeleteDC()
    print("sent OK")


if __name__ == "__main__":
    main()
