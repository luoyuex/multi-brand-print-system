from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import models, schemas, crud
from database import get_db
from print_service import service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/", response_model=List[schemas.OrderOut])
def list_orders(
    start_date: Optional[date] = Query(None, description="起始日期 YYYY-MM-DD（含当天）"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD（含当天）"),
    db: Session = Depends(get_db),
):
    # 把日期转成 [start, end) 的时间区间：end_date 那天整天都算在内
    start = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time()) if end_date else None
    return crud.get_orders(db, start=start, end=end)


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    obj = crud.get_order(db, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="订单不存在")
    return obj


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    obj = crud.delete_order(db, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="订单不存在")
    return None


@router.post("/", response_model=schemas.OrderOut, status_code=201)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    store = crud.get_store(db, order.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="店铺不存在")

    db_order = models.Order(
        brand_id=order.brand_id,
        store_id=order.store_id,
        customer=store.name,
        status="pending",
    )
    db.add(db_order)
    db.flush()

    for item in order.items:
        db.add(models.OrderItem(order_id=db_order.id, **item.model_dump()))

    db.commit()
    db.refresh(db_order)
    return crud.get_order(db, db_order.id)   # 重新查一次以带上 brand 关联


@router.put("/{order_id}", response_model=schemas.OrderOut)
def update_order(order_id: int, data: schemas.OrderUpdate, db: Session = Depends(get_db)):
    obj = crud.update_order(db, order_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="订单不存在")
    return crud.get_order(db, order_id)


@router.post("/{order_id}/print", response_model=schemas.OrderOut)
def print_order(order_id: int, db: Session = Depends(get_db)):
    """静默打印订单：渲染 → 打印机出纸，成功后才标记已打印。

    打印服务异常（未装 SumatraPDF / 打印机离线等）返回 502，前端提示，
    订单状态保持不变，可重试。
    """
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    data = service.build_print_data(order)
    try:
        service.submit("delivery_a5", data)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"打印失败：{type(e).__name__}: {repr(e)}")

    crud.mark_printed(db, order_id)
    return crud.get_order(db, order_id)
