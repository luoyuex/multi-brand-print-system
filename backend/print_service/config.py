"""打印配置：默认打印机、纸张、SumatraPDF 路径。

配置持久化到 backend/print_config.json，可通过 /api/print/config 接口读写。
首次运行时若文件不存在，用默认值创建。
"""

import json
import os
import shutil
from pathlib import Path
from threading import Lock

# 配置文件与本模块同级放在 backend/ 下
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "print_config.json"

_lock = Lock()

# SumatraPDF 常见安装路径（静默打印用），按顺序探测
_SUMATRA_CANDIDATES = [
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
]

_DEFAULTS = {
    "default_printer": "",   # 空字符串 = 用系统默认打印机
    "paper_size": "241x140", # 横版直排：241mm宽 × 139.5mm高，内容正向、文字左右阅读。
                             # 与打印机驱动的自定义纸张(241×139.5 横)一致，1:1 送打，不旋转。
    "copies": 1,
    "sumatra_path": "",      # 空 = 自动探测
    "print_rotate": 0,       # 不旋转：渲染即为横版正立，SumatraPDF noscale 直接对上驱动纸张。
}


def _detect_sumatra() -> str:
    """探测 SumatraPDF 可执行文件路径，找不到返回空串。"""
    for p in _SUMATRA_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    # PATH 中查找
    found = shutil.which("SumatraPDF")
    return found or ""


def load_config() -> dict:
    """读取配置，缺失字段用默认值补齐。"""
    cfg = dict(_DEFAULTS)
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f) or {})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(patch: dict) -> dict:
    """合并写入配置，只允许更新已知字段。返回最新完整配置。"""
    with _lock:
        cfg = load_config()
        for key in _DEFAULTS:
            if key in patch and patch[key] is not None:
                cfg[key] = patch[key]
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg


def get_sumatra_path() -> str:
    """返回可用的 SumatraPDF 路径：优先配置，其次自动探测。"""
    cfg = load_config()
    if cfg.get("sumatra_path") and os.path.isfile(cfg["sumatra_path"]):
        return cfg["sumatra_path"]
    return _detect_sumatra()
