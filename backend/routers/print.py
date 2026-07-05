"""打印相关路由 /api/print

- GET  /api/print/printers  枚举系统打印机 + 默认打印机
- GET  /api/print/config    读取打印配置
- PUT  /api/print/config    更新打印配置（默认打印机 / 纸张 / 份数 / SumatraPDF 路径）
- POST /api/print/test      打印测试页
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from print_service import config, printer, service

router = APIRouter(prefix="/api/print", tags=["print"])


class PrintConfigOut(BaseModel):
    default_printer: str
    paper: str
    copies: int
    sumatra_path: str


class PrintConfigUpdate(BaseModel):
    default_printer: Optional[str] = None
    paper: Optional[str] = None
    copies: Optional[int] = None
    sumatra_path: Optional[str] = None


class PrintersOut(BaseModel):
    printers: List[str]
    default: str


class TestPrintIn(BaseModel):
    printer: Optional[str] = None


@router.get("/printers", response_model=PrintersOut)
def get_printers():
    return printer.list_printers()


@router.get("/config", response_model=PrintConfigOut)
def get_config():
    return config.load_config()


@router.put("/config", response_model=PrintConfigOut)
def update_config(data: PrintConfigUpdate):
    return config.save_config(data.model_dump(exclude_unset=True))


@router.post("/test")
def test_print(data: TestPrintIn):
    try:
        return service.print_test(printer_name=data.printer)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"测试打印失败：{e}")
