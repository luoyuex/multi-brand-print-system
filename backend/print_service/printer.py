"""打印机操作：枚举系统打印机 + 用 SumatraPDF 静默打印 PDF / WPS 静默打印 xlsx。

Windows 下：
- list_printers(): 通过 PowerShell 枚举本机打印机与默认打印机（中文友好）。
- print_pdf(): 调 SumatraPDF 命令行静默打印（不弹对话框）。
- print_xlsx(): 调 WPS ET 命令行静默打印 xlsx（走纸准确，推荐用于针式打印机）。
"""

import glob
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

from . import config


# win32print.GetPrinter(h, 2) 的 Status 位标志 → 中文说明。
# 参考 Windows PRINTER_STATUS_* 常量，只列出批量打印需要拦截的几种。
_PRINTER_STATUS_FLAGS = [
    (0x00000001, "暂停"),        # PAUSED
    (0x00000002, "错误"),        # ERROR
    (0x00000080, "离线"),        # OFFLINE
    (0x00000010, "缺纸"),        # PAPER_OUT
    (0x00000008, "卡纸"),        # PAPER_JAM
    (0x00000400, "输出仓已满"),  # OUTPUT_BIN_FULL
    (0x00000200, "门未关"),      # DOOR_OPEN
]

# 视为「无法打印，应跳过本单」的致命状态位。
_FATAL_STATUS_MASK = 0x00000002 | 0x00000080 | 0x00000010 | 0x00000008 | 0x00000200


def get_status(printer_name: Optional[str] = None) -> dict:
    """查询打印机状态。

    返回 { ok, status_code, status_text, jobs, ready, reason }：
    - ok:          是否成功读到状态（读不到时 ok=False，不阻断打印，交给上层决定）
    - status_code: 原始 Status 位标志（int）
    - status_text: 人类可读的状态描述（多个状态用「、」连接，正常为「就绪」）
    - jobs:        当前打印队列里的任务数（cJobs），>0 表示还在打印/排队
    - ready:       是否可以送新任务（无致命状态位）
    - reason:      不可打印时的原因（ready=True 时为空）

    读取失败（非 Windows / 无 pywin32 / 打印机名错误）时返回 ok=False、
    ready=True——宁可放行也不误伤，让实际打印命令去暴露真正的错误。
    """
    try:
        import win32print
    except ImportError:
        return {"ok": False, "status_code": 0, "status_text": "未知",
                "jobs": 0, "ready": True, "reason": ""}

    target = printer_name or ""
    try:
        if not target:
            target = win32print.GetDefaultPrinter()
        hp = win32print.OpenPrinter(target)
        try:
            info = win32print.GetPrinter(hp, 2)
        finally:
            win32print.ClosePrinter(hp)
    except Exception:
        return {"ok": False, "status_code": 0, "status_text": "未知",
                "jobs": 0, "ready": True, "reason": ""}

    status_code = int(info.get("Status", 0))
    jobs = int(info.get("cJobs", 0))

    labels = [text for bit, text in _PRINTER_STATUS_FLAGS if status_code & bit]
    status_text = "、".join(labels) if labels else "就绪"

    fatal = status_code & _FATAL_STATUS_MASK
    ready = not fatal
    reason = ("、".join(t for b, t in _PRINTER_STATUS_FLAGS if fatal & b)
              if fatal else "")

    return {
        "ok": True,
        "status_code": status_code,
        "status_text": status_text,
        "jobs": jobs,
        "ready": ready,
        "reason": reason,
    }


def wait_until_idle(printer_name: Optional[str] = None,
                    timeout: float = 60.0,
                    poll_interval: float = 0.5) -> bool:
    """轮询打印队列，直到队列清空（上一单真正出纸完成）或超时。

    针式连续纸必须等打印机消化完当前任务再送下一单，否则任务堆积、走纸错乱。
    通过 GetPrinter 的 cJobs 判断：cJobs 归零即认为当前任务已打完。

    返回 True 表示队列已空闲；False 表示超时（队列仍有任务）或无法读取状态。
    读不到状态（非 Windows / 无 pywin32）时立即返回 True，不阻塞流程。
    """
    try:
        import win32print  # noqa: F401
    except ImportError:
        return True

    deadline = time.monotonic() + max(0.0, timeout)
    # spool 后打印机需要一点时间把任务登记进队列，先给个短暂缓冲，
    # 避免刚提交就读到 cJobs=0 而误判「已打完」。
    time.sleep(min(poll_interval, 0.3))

    while True:
        st = get_status(printer_name)
        if not st["ok"]:
            return True  # 读不到就不阻塞
        if st["jobs"] <= 0:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)


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


def _rotate_pdf(src_path: str, degrees: int) -> Optional[str]:
    """把 PDF 每一页旋转 degrees 度，写到新的临时文件，返回其路径。

    用于「渲染出竖版 139.5x241，打印时整体旋转 90° 成横版 241x139.5」的场景。

    关键：不能用 page.set_rotation()（那只写 /Rotate 标志位，页面真实尺寸
    仍是竖版；SumatraPDF 用 noscale 打印时会忽略该标志位，按原始竖版内容打，
    导致「PDF 阅读器里看着转好了、打出来方向却不对」）。

    这里改用「烤入式旋转」：新建一个宽高互换的实体页（rotation=0），用
    show_pdf_page(rotate=deg) 把源页真正画上去。这样 SumatraPDF 看到的就是
    货真价实的横版页，noscale 打出来方向正确。

    degrees 为 0 或非法值时返回 None（表示无需旋转，直接打原文件）。
    旋转失败时返回 None，静默降级为打印原始 PDF。
    """
    if not degrees:
        return None
    try:
        import fitz  # pymupdf
    except ImportError:
        return None

    try:
        src = fitz.open(src_path)
        out = fitz.open()
        swap = degrees in (90, 270)  # 90/270 度需要宽高互换
        for page in src:
            r = page.rect
            if swap:
                new_w, new_h = r.height, r.width
            else:
                new_w, new_h = r.width, r.height
            new_page = out.new_page(width=new_w, height=new_h)
            # 把源页内容旋转 degrees 度画到新页上（铺满整页）
            new_page.show_pdf_page(new_page.rect, src, page.number, rotate=degrees)
        fd, rotated_path = tempfile.mkstemp(suffix=".pdf", prefix="print_rot_")
        os.close(fd)
        out.save(rotated_path)
        out.close()
        src.close()
        return rotated_path
    except Exception:
        return None


def print_pdf(pdf_path: str, printer: Optional[str] = None, copies: int = 1) -> None:
    """用 SumatraPDF 静默打印 PDF。

    printer: 打印机名，空/None = 用系统默认打印机（-print-to-default）。
    copies:  份数，通过多次调用实现（SumatraPDF 命令行无直接份数参数）。

    打印前按配置 print_rotate 旋转 PDF（默认 90°）：渲染出的 241x140 横版
    PDF 不变，只把送打印机的副本转成 140x241 纵向，正对针式连续纸走纸方向。

    抛出异常表示打印失败（找不到 SumatraPDF / 命令返回非 0）。
    """
    sumatra = config.get_sumatra_path()
    if not sumatra:
        raise RuntimeError(
            "未找到 SumatraPDF，请安装后重试，或在打印配置中指定 sumatra_path。"
        )

    # 打印前旋转：渲染不动，只转送打印机的这份
    cfg = config.load_config()
    degrees = int(cfg.get("print_rotate", 0) or 0) % 360
    rotated_path = _rotate_pdf(pdf_path, degrees)
    target_pdf = rotated_path or pdf_path

    try:
        # 组装命令：静默打印
        if printer:
            base = [sumatra, "-print-to", printer, "-silent"]
        else:
            base = [sumatra, "-print-to-default", "-silent"]
        # noscale：1:1打印，不缩放。
        # 旋转已在 PDF 页面层面完成（/Rotate），这里不再让 SumatraPDF/驱动
        # 自行旋转，避免走纸长度被算错。
        # noscale：1:1不缩放。PDF 物理尺寸241×139.5横版，驱动自动识别方向。
        base += ["-print-settings", "noscale"]
        base += ["-exit-when-done", target_pdf]

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
    finally:
        if rotated_path:
            try:
                os.remove(rotated_path)
            except OSError:
                pass


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
