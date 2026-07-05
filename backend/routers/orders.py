from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
from database import get_db

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/", response_model=List[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return crud.get_orders(db)


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    obj = crud.get_order(db, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="订单不存在")
    return obj


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
def mark_printed(order_id: int, db: Session = Depends(get_db)):
    obj = crud.mark_printed(db, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="订单不存在")
    return crud.get_order(db, order_id)
