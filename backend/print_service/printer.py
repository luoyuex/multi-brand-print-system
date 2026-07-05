"""打印机操作：枚举系统打印机 + 用 SumatraPDF 静默打印 PDF。

Windows 下：
- list_printers(): 通过 pywin32 (win32print) 枚举本机打印机与默认打印机。
- print_pdf(): 调 SumatraPDF 命令行静默打印（不弹对话框），支持指定打印机/份数。
"""

import subprocess
import sys
from typing import List, Optional

from . import config


def list_printers() -> dict:
    """返回 { printers: [name...], default: name }。

    优先用 pywin32；不可用时降级用 PowerShell。
    """
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = [p[2] for p in win32print.EnumPrinters(flags)]
        try:
            default = win32print.GetDefaultPrinter()
        except Exception:
            default = ""
        return {"printers": printers, "default": default}
    except ImportError:
        return _list_printers_powershell()


def _list_printers_powershell() -> dict:
    """pywin32 缺失时的降级方案：PowerShell 枚举。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10,
        )
        printers = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        default = ""
        try:
            dout = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Printer | Where-Object Default -eq $true).Name"],
                capture_output=True, text=True, timeout=10,
            )
            default = dout.stdout.strip()
        except Exception:
            pass
        return {"printers": printers, "default": default}
    except Exception:
        return {"printers": [], "default": ""}


def print_pdf(pdf_path: str, printer: Optional[str] = None, copies: int = 1) -> None:
    """用 SumatraPDF 静默打印 PDF。

    printer: 打印机名，空/None = 用系统默认打印机。
    copies:  份数，通过多次调用实现（SumatraPDF 命令行无直接份数参数）。

    抛出异常表示打印失败（找不到 SumatraPDF / 命令返回非 0）。
    """
    sumatra = config.get_sumatra_path()
    if not sumatra:
        raise RuntimeError(
            "未找到 SumatraPDF，请安装后重试，或在打印配置中指定 sumatra_path。"
        )

    # 组装命令：静默打印到指定/默认打印机
    if printer:
        base = [sumatra, "-print-to", printer, "-silent"]
    else:
        base = [sumatra, "-print-to-default", "-silent"]
    base += ["-exit-when-done", pdf_path]

    copies = max(1, int(copies or 1))
    for _ in range(copies):
        result = subprocess.run(
            base,
            capture_output=True, text=True, timeout=60,
            creationflags=_no_window_flag(),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"SumatraPDF 打印失败 (code {result.returncode}): "
                f"{result.stderr or result.stdout or '无输出'}"
            )


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
