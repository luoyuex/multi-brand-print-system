from typing import Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import models, schemas


# ── Brand ──────────────────────────────────────────────
def get_brands(db: Session):
    return db.query(models.Brand).all()

def create_brand(db: Session, brand: schemas.BrandCreate):
    obj = models.Brand(name=brand.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ── Store ──────────────────────────────────────────────
def get_stores(db: Session, search: Optional[str] = None):
    q = db.query(models.Store)
    if search:
        q = q.filter(
            or_(
                models.Store.name.like(f"%{search}%"),
                models.Store.contact.like(f"%{search}%"),
            )
        )
    return q.order_by(models.Store.name).all()

def get_store(db: Session, store_id: int):
    return db.query(models.Store).filter(models.Store.id == store_id).first()

def create_store(db: Session, store: schemas.StoreCreate):
    obj = models.Store(**store.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_store(db: Session, store_id: int, data: schemas.StoreUpdate):
    obj = get_store(db, store_id)
    if not obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_store(db: Session, store_id: int):
    obj = get_store(db, store_id)
    if obj:
        db.delete(obj)
        db.commit()
    return obj


# ── Product ────────────────────────────────────────────
def get_products(db: Session, brand_id: Optional[int] = None, search: Optional[str] = None):
    q = db.query(models.Product)
    if brand_id:
        q = q.filter(models.Product.brand_id == brand_id)
    if search:
        q = q.filter(
            or_(
                models.Product.code.like(f"%{search}%"),
                models.Product.name.like(f"%{search}%"),
            )
        )
    return q.order_by(models.Product.code).all()

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def create_product(db: Session, product: schemas.ProductCreate):
    obj = models.Product(**product.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_product(db: Session, product_id: int, data: schemas.ProductUpdate):
    obj = get_product(db, product_id)
    if not obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_product(db: Session, product_id: int):
    obj = get_product(db, product_id)
    if obj:
        db.delete(obj)
        db.commit()
    return obj


# ── Order ──────────────────────────────────────────────
def _order_q(db: Session):
    """Base query with brand + items eagerly loaded."""
    return db.query(models.Order).options(
        joinedload(models.Order.brand),
        joinedload(models.Order.items),
    )

def get_orders(db: Session, start: Optional[datetime] = None, end: Optional[datetime] = None):
    q = _order_q(db)
    if start is not None:
        q = q.filter(models.Order.created_at >= start)
    if end is not None:
        q = q.filter(models.Order.created_at < end)
    return q.order_by(models.Order.created_at.desc()).all()

def get_order(db: Session, order_id: int):
    return _order_q(db).filter(models.Order.id == order_id).first()

def update_order(db: Session, order_id: int, data: schemas.OrderUpdate):
    obj = get_order(db, order_id)
    if not obj:
        return None
    # 删除旧行，替换为新行
    for item in list(obj.items):
        db.delete(item)
    db.flush()
    for item in data.items:
        db.add(models.OrderItem(order_id=obj.id, **item.model_dump()))
    db.commit()
    db.refresh(obj)
    return obj

def mark_printed(db: Session, order_id: int):
    obj = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not obj:
        return None
    obj.status = "printed"
    obj.printed_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj

def delete_order(db: Session, order_id: int):
    obj = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not obj:
        return None
    db.delete(obj)   # order_items 通过 cascade="all, delete-orphan" 一并删除
    db.commit()
    return obj
