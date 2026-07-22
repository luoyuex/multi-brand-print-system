"""打印机查询：枚举系统打印机 + 查状态 + 等出纸。

送货单的实际出纸走 gdi_printer（pywin32 GDI 直接绘制），本模块只负责
围绕打印机的查询能力，供单打/批量打印编排使用：

- list_printers():   枚举本机打印机与默认打印机（PowerShell，中文友好）。
- get_status():      查打印机状态（就绪/离线/缺纸/卡纸 + 队列任务数）。
- wait_until_idle(): 轮询队列清空，确认针式连续纸真正走完再送下一单。
"""

import subprocess
import time
from typing import Optional


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
