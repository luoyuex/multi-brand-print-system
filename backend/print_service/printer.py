"""打印机操作：枚举系统打印机 + 用 SumatraPDF 静默打印 PDF / WPS 静默打印 xlsx。

Windows 下：
- list_printers(): 通过 PowerShell 枚举本机打印机与默认打印机（中文友好）。
- print_pdf(): 调 SumatraPDF 命令行静默打印（不弹对话框）。
- print_xlsx(): 调 WPS ET 命令行静默打印 xlsx（走纸准确，推荐用于针式打印机）。
"""

import glob
import subprocess
import sys
from typing import Optional

from . import config


def list_printers() -> dict:
    """返回 { printers: [name...], default: name }。

    用 PowerShell 枚举，避免 pywin32 在中文 Windows 下打印机名乱码。
    """
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, timeout=10,
        )
        # Windows 中文系统 PowerShell 输出默认是 GBK (cp936)
        text = out.stdout.decode("gbk", errors="replace")
        printers = [ln.strip() for ln in text.splitlines() if ln.strip()]
    except Exception:
        printers = []

    default = ""
    try:
        dout = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Printer | Where-Object Default -eq $true).Name"],
            capture_output=True, timeout=10,
        )
        default = dout.stdout.decode("gbk", errors="replace").strip()
    except Exception:
        pass

    return {"printers": printers, "default": default}


def _set_form_length(printer_name: str, mm: float = 140.0) -> None:
    """用 ESC/P 命令设置 EPSON 打印机的走纸长度。

    在每次打印任务前调用，确保针式打印机按指定 mm 分页走纸。
    失败时静默忽略，不影响主打印任务。
    """
    try:
        import win32print
        # 6 LPI（每英寸6行）是 EPSON 默认行距
        lines = max(1, round(mm / 25.4 * 6))  # 140mm → 33行
        # ESC C 0 n：设置走纸长度为 n 行
        cmd = b'\x1b\x43\x00' + bytes([lines])
        target = printer_name or win32print.GetDefaultPrinter()
        hp = win32print.OpenPrinter(target)
        try:
            # RAW 任务直接写入，不调用 StartPagePrinter/EndPagePrinter
            # 否则 EndPage 会触发一次走纸，导致双倍走纸
            win32print.StartDocPrinter(hp, 1, ("form_length_setup", None, "RAW"))
            win32print.WritePrinter(hp, cmd)
            win32print.EndDocPrinter(hp)
        finally:
            win32print.ClosePrinter(hp)
    except Exception:
        pass  # 静默失败，不影响主流程


def print_pdf(pdf_path: str, printer: Optional[str] = None, copies: int = 1) -> None:
    """用 SumatraPDF 静默打印 PDF。

    printer: 打印机名，空/None = 用系统默认打印机（-print-to-default）。
    copies:  份数，通过多次调用实现（SumatraPDF 命令行无直接份数参数）。

    抛出异常表示打印失败（找不到 SumatraPDF / 命令返回非 0）。
    """
    sumatra = config.get_sumatra_path()
    if not sumatra:
        raise RuntimeError(
            "未找到 SumatraPDF，请安装后重试，或在打印配置中指定 sumatra_path。"
        )

    # 组装命令：静默打印
    if printer:
        base = [sumatra, "-print-to", printer, "-silent"]
    else:
        base = [sumatra, "-print-to-default", "-silent"]
    # noscale：1:1打印，不缩放
    # 不加 landscape：驱动已配置横向，SumatraPDF 再加会导致PDF被旋转，
    # 驱动收到241mm"高"的页面后走纸变成241mm而非140mm
    base += ["-print-settings", "noscale"]
    base += ["-exit-when-done", pdf_path]

    copies = max(1, int(copies or 1))
    for _ in range(copies):
        result = subprocess.run(
            base,
            capture_output=True, text=True, timeout=60,
            creationflags=_no_window_flag(),
        )
        # SumatraPDF 返回 0 或 1 都可能表示成功（1 有时只是信息提示），
        # 真正的失败通常有 stderr 内容。这里只在明显错误时抛异常。
        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"SumatraPDF 打印失败 (code {result.returncode}): "
                f"{result.stderr or result.stdout or '无输出'}"
            )


def _find_wps_et() -> Optional[str]:
    """查找 WPS Office ET（表格）可执行文件路径。"""
    patterns = [
        r"F:\wps\WPS Office\*\office6\et.exe",            # 本机自定义安装路径
        r"C:\Program Files (x86)\Kingsoft\WPS Office\*\office6\et.exe",
        r"C:\Program Files\Kingsoft\WPS Office\*\office6\et.exe",
        r"C:\Users\*\AppData\Local\Kingsoft\WPS Office\*\office6\et.exe",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]   # 取版本最新的
    return None


def print_xlsx(xlsx_path: str, printer: Optional[str] = None, copies: int = 1) -> None:
    """用 WPS ET 静默打印 xlsx。

    paperSize=132 已在 xlsx 内配置好（EPSON连续纸），WPS 会直接用正确走纸参数打印。
    printer: 打印机名，空/None = 用系统默认打印机。
    copies:  份数，通过多次调用实现。

    找不到 WPS ET 时抛 RuntimeError。
    """
    et = _find_wps_et()
    if not et:
        raise RuntimeError(
            "未找到 WPS Office ET，请安装 WPS Office 后重试。"
        )

    # WPS ET 静默打印命令：et.exe -pt "<打印机>" "<文件>"
    # 不指定打印机时用 -p（默认打印机）
    copies = max(1, int(copies or 1))
    for _ in range(copies):
        if printer:
            cmd = [et, "-pt", printer, xlsx_path]
        else:
            cmd = [et, "-p", xlsx_path]

        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=60,
            creationflags=_no_window_flag(),
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"WPS ET 打印失败 (code {result.returncode}): "
                f"{result.stderr or result.stdout or '无输出'}"
            )


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
