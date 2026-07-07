"""打印机操作：枚举系统打印机 + 用 SumatraPDF 静默打印 PDF。

Windows 下：
- list_printers(): 通过 PowerShell 枚举本机打印机与默认打印机（中文友好）。
- print_pdf(): 调 SumatraPDF 命令行静默打印（不弹对话框），支持指定打印机/份数。
"""

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
    # 有指定打印机时用 -print-to <name>，否则用 -print-to-default
    if printer:
        base = [sumatra, "-print-to", printer, "-silent"]
    else:
        base = [sumatra, "-print-to-default", "-silent"]
    # 记账凭证纸横向打印 + 指定纸张尺寸
    base += ["-print-settings", "241x140mm,Landscape,1x"]
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


def _no_window_flag() -> int:
    """Windows 下避免弹出子进程控制台窗口。"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
