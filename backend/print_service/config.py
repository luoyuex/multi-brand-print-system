"""打印配置：默认打印机、份数。

配置持久化到 backend/print_config.json，可通过 /api/print/config 接口读写。
首次运行时若文件不存在，用默认值创建。

送货单走 GDI 直接绘制（见 docs/gdi-print-plan.md），纸张方向和走纸由代码定死，
不再需要 paper_size / SumatraPDF 路径 / 旋转角度等配置。
"""

import json
from pathlib import Path
from threading import Lock

# 配置文件与本模块同级放在 backend/ 下
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "print_config.json"

_lock = Lock()

_DEFAULTS = {
    "default_printer": "",   # 空字符串 = 用系统默认打印机
    "copies": 1,
}


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
