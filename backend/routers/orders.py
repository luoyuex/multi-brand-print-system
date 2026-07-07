from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
from database import get_db
from print_service import service

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _build_print_data(order: models.Order) -> dict:
    """把订单模型转成打印模板所需的数据结构。

    - 单价/小计保留两位小数（模板里再格式化）；
    - 合计取整（与前端页面显示一致）。
    - 数量为整数时去掉小数尾巴，显示更干净。
    """
    def fmt_qty(q):
        f = float(q)
        return int(f) if f == int(f) else round(f, 2)

    items = []
    total = 0.0
    for i, it in enumerate(order.items, start=1):
        is_replacement = bool(it.is_replacement)
        qty = float(it.qty)
        # 补货行免费补发：单价/小计强制为 0，不计入合计
        price = 0.0 if is_replacement else float(it.price)
        subtotal = price * qty
        total += subtotal
        items.append({
            "index": i,
            "product_name": it.product_name,
            "spec": it.spec or "",
            "qty": fmt_qty(qty),
            "price": price,
            "subtotal": subtotal,
            "is_replacement": is_replacement,
        })

    created = order.created_at
    created_str = created.strftime("%Y-%m-%d %H:%M") if created else ""

    return {
        "brand_name": order.brand_name,
        "customer": order.customer,
        "order_id": order.id,
        "created_at": created_str,
        "items": items,
        "total": round(total),
    }


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
def print_order(order_id: int, db: Session = Depends(get_db)):
    """静默打印订单：渲染 → 打印机出纸，成功后才标记已打印。

    打印服务异常（未装 SumatraPDF / 打印机离线等）返回 502，前端提示，
    订单状态保持不变，可重试。
    """
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    data = _build_print_data(order)
    try:
        service.submit("delivery_a5", data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"打印失败：{e}")

    crud.mark_printed(db, order_id)
    return crud.get_order(db, order_id)
