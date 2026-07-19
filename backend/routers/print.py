"""打印相关路由 /api/print

- GET  /api/print/printers  枚举系统打印机 + 默认打印机
- GET  /api/print/config    读取打印配置
- PUT  /api/print/config    更新打印配置（默认打印机 / 纸张 / 份数 / SumatraPDF 路径）
- POST /api/print/test      打印测试页
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

import crud
from database import get_db
from print_service import config, printer, service, batch

router = APIRouter(prefix="/api/print", tags=["print"])


class PrintConfigOut(BaseModel):
    default_printer: str
    paper_size: str
    copies: int
    sumatra_path: str


class PrintConfigUpdate(BaseModel):
    default_printer: Optional[str] = None
    paper_size: Optional[str] = None
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
    import traceback
    try:
        return service.print_test(printer_name=data.printer)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"测试打印失败：{type(e).__name__}: {repr(e)}")


class PrinterStatusOut(BaseModel):
    ok: bool
    status_code: int
    status_text: str
    jobs: int
    ready: bool
    reason: str


class BatchPrintIn(BaseModel):
    order_ids: List[int]                 # 打印顺序即数组顺序
    printer: Optional[str] = None        # 空 = 用配置里的默认打印机


@router.get("/status", response_model=PrinterStatusOut)
def get_printer_status(printer_name: Optional[str] = None):
    """查询打印机当前状态（就绪/离线/缺纸/卡纸 + 队列任务数）。"""
    return printer.get_status(printer_name)


@router.post("/batch")
def start_batch_print(data: BatchPrintIn, db: Session = Depends(get_db)):
    """启动一键批量打印：后台 worker 串行逐单打印，返回初始进度快照。

    前端拿到 batch_id 后连 /batch/{id}/stream 订阅实时进度。
    只把存在的订单纳入批次；order_ids 顺序即打印顺序。
    """
    if not data.order_ids:
        raise HTTPException(status_code=400, detail="没有要打印的订单")

    orders = []
    for oid in data.order_ids:
        o = crud.get_order(db, oid)
        if o:
            orders.append({
                "order_id": o.id,
                "customer": o.customer,
                "brand_name": o.brand_name,
            })

    if not orders:
        raise HTTPException(status_code=404, detail="订单都不存在")

    batch.cleanup_old()   # 顺手清理旧批次，防内存堆积
    return batch.start_batch(orders, printer_name=data.printer)


@router.get("/batch/{batch_id}")
def get_batch_snapshot(batch_id: str):
    """一次性拉取批次当前进度快照（SSE 断线后的兜底轮询）。"""
    b = batch.get_batch(batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="批次不存在或已过期")
    return b.snapshot()


@router.get("/batch/{batch_id}/stream")
async def stream_batch_progress(batch_id: str):
    """SSE 推送批量打印进度：状态有变化即推送快照，完成后自动收尾关闭。

    实现：worker 线程在每次状态变动时 bump 版本号，这里在线程池里阻塞
    等待版本号变化（wait_for_change），有变化就推一帧，无变化则定期发心跳。
    """
    b = batch.get_batch(batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="批次不存在或已过期")

    async def event_gen():
        last_version = -1
        # 先立即推一帧当前快照，前端连上就能看到初始状态。
        snap = b.snapshot()
        last_version = snap["version"]
        yield f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"

        while True:
            # 在线程池等待状态变化，避免阻塞事件循环；15s 无变化则发心跳。
            version = await asyncio.to_thread(b.wait_for_change, last_version, 15.0)
            if version > last_version:
                last_version = version
                snap = b.snapshot()
                yield f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"
                if snap["done"]:
                    break
            else:
                # 心跳注释帧，保持连接不被代理断开
                yield ": keep-alive\n\n"
                if b.done:
                    # 完成后可能错过最后一次 bump，补推一帧再退出
                    snap = b.snapshot()
                    yield f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"
                    break

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
