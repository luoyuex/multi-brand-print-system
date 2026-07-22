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
def get_stores(db: Session, search: Optional[str] = None, brand_id: Optional[int] = None):
    q = db.query(models.Store)
    if brand_id is not None:
        q = q.filter(models.Store.brand_id == brand_id)
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


# ── Bill（对账单）──────────────────────────────────────
def _day_range(start: date, end: date):
    """把日期区间转成 [start, end+1) 的时间区间：end 那天整天都算在内。

    与 routers/orders.py 里的换算规则一致，保证按天筛选口径统一。
    """
    s = datetime.combine(start, datetime.min.time())
    e = datetime.combine(end + timedelta(days=1), datetime.min.time())
    return s, e


def _iter_bill_lines(orders):
    """把订单列表拍平成明细流，应用补货免费规则（与 service.build_print_data 一致）：
    补货行单价/小计强制为 0、不计入合计。逐条 yield (order, item, qty, price, subtotal)。
    """
    for order in orders:
        for it in order.items:
            is_rep = bool(it.is_replacement)
            qty = float(it.qty)
            price = 0.0 if is_rep else float(it.price)
            subtotal = price * qty
            yield order, it, qty, price, subtotal


def get_unbilled_orders(db: Session, store_id: int, start: date, end: date,
                        include_bill_id: int = None):
    """某客户账期区间内、尚未出账（bill_id 为空）的订单，按下单时间升序。

    include_bill_id 用于编辑账单改期：把已被该账单认领的订单也算作「可用」，
    否则改期预览/重算时看不到本账单原有的订单。
    """
    s, e = _day_range(start, end)
    if include_bill_id is not None:
        avail = or_(models.Order.bill_id.is_(None),
                    models.Order.bill_id == include_bill_id)
    else:
        avail = models.Order.bill_id.is_(None)
    return (
        _order_q(db)
        .filter(
            models.Order.store_id == store_id,
            avail,
            models.Order.created_at >= s,
            models.Order.created_at < e,
        )
        .order_by(models.Order.created_at.asc())
        .all()
    )


def get_unbilled_store_ids(db: Session, start: date, end: date):
    """账期区间内有未出账订单的所有客户 store_id（去重，一键出账用）。"""
    s, e = _day_range(start, end)
    rows = (
        db.query(models.Order.store_id)
        .filter(
            models.Order.bill_id.is_(None),
            models.Order.store_id.isnot(None),
            models.Order.created_at >= s,
            models.Order.created_at < e,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def preview_bill(db: Session, store_id: int, start: date, end: date,
                 include_bill_id: int = None):
    """预览某客户某账期的未出账汇总（按天分组），不写库。"""
    orders = get_unbilled_orders(db, store_id, start, end,
                                 include_bill_id=include_bill_id)
    store = get_store(db, store_id)
    customer = store.name if store else (orders[0].customer if orders else "")
    brand_name = orders[0].brand_name if orders else ""

    days = {}   # date -> {date, items, subtotal}；orders 已按时间升序，天然按天有序
    total = 0.0
    for order, it, qty, price, subtotal in _iter_bill_lines(orders):
        d = order.created_at.date()
        day = days.setdefault(d, {"date": d, "items": [], "subtotal": 0.0})
        day["items"].append({
            "product_name": it.product_name,
            "spec": it.spec or "",
            "qty": qty,
            "price": price,
            "subtotal": subtotal,
            "is_replacement": bool(it.is_replacement),
        })
        day["subtotal"] += subtotal
        total += subtotal

    return {
        "store_id": store_id,
        "customer": customer,
        "brand_name": brand_name,
        "period_start": start,
        "period_end": end,
        "order_count": len(orders),
        "total": total,
        "days": list(days.values()),
    }


def create_bill(db: Session, store_id: int, start: date, end: date, note: str = None):
    """出账：把该客户区间内未出账订单快照成一张账单。

    无未出账订单则返回 None（路由据此报 400）。成功后把这些订单的 bill_id
    指向新账单，之后不再重复计入任何账单。
    """
    orders = get_unbilled_orders(db, store_id, start, end)
    if not orders:
        return None

    store = get_store(db, store_id)
    customer = store.name if store else (orders[0].customer or "")

    bill = models.Bill(
        store_id=store_id,
        customer=customer,
        brand_id=orders[0].brand_id,
        brand_name=orders[0].brand_name,
        period_start=start,
        period_end=end,
        total_amount=0,
        order_count=len(orders),
        note=note,
    )
    db.add(bill)
    db.flush()   # 取到 bill.id

    total = 0.0
    for order, it, qty, price, subtotal in _iter_bill_lines(orders):
        db.add(models.BillItem(
            bill_id=bill.id,
            order_id=order.id,
            order_date=order.created_at.date(),
            product_name=it.product_name,
            spec=it.spec,
            qty=qty,
            price=price,
            subtotal=subtotal,
            is_replacement=bool(it.is_replacement),
        ))
        total += subtotal

    bill.total_amount = total
    for order in orders:
        order.bill_id = bill.id   # 认领，防重复出账

    db.commit()
    db.refresh(bill)
    return bill


def update_bill(db: Session, bill_id: int, start: date, end: date, note: str = None):
    """编辑账单：按新账期重算明细（选错账期时改期用）。

    账单是订单的快照，改期不能只动 period 字段，否则明细对不上。做法：
    先释放本账单原认领的订单，再按新账期在「未出账 + 本账单原有」范围内重新
    认领并重建明细快照。账单 id / created_at / sent / paid 状态全部保留。
    新账期内没有任何订单则返回 "empty"（路由据此报 400，不动原账单）。
    """
    bill = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not bill:
        return None

    orders = get_unbilled_orders(db, bill.store_id, start, end, include_bill_id=bill_id)
    if not orders:
        return "empty"

    # 释放旧认领并清空旧明细快照
    db.query(models.Order).filter(models.Order.bill_id == bill_id).update(
        {models.Order.bill_id: None}, synchronize_session=False)
    for it in list(bill.items):
        db.delete(it)
    db.flush()

    store = get_store(db, bill.store_id)
    bill.customer   = store.name if store else (orders[0].customer or bill.customer)
    bill.brand_id   = orders[0].brand_id
    bill.brand_name = orders[0].brand_name
    bill.period_start = start
    bill.period_end   = end
    bill.order_count  = len(orders)
    if note is not None:
        bill.note = note

    total = 0.0
    for order, it, qty, price, subtotal in _iter_bill_lines(orders):
        db.add(models.BillItem(
            bill_id=bill.id,
            order_id=order.id,
            order_date=order.created_at.date(),
            product_name=it.product_name,
            spec=it.spec,
            qty=qty,
            price=price,
            subtotal=subtotal,
            is_replacement=bool(it.is_replacement),
        ))
        total += subtotal

    bill.total_amount = total
    for order in orders:
        order.bill_id = bill.id   # 重新认领

    db.commit()
    db.refresh(bill)
    return bill


def _bill_q(db: Session):
    return db.query(models.Bill).options(joinedload(models.Bill.items))


def get_bills(db: Session, *, store_id=None, keyword=None, start=None, end=None,
              sent=None, paid=None):
    """账单列表查询。start/end 为账期重叠过滤；sent/paid 为三态（None=全部）。"""
    q = _bill_q(db)
    if store_id is not None:
        q = q.filter(models.Bill.store_id == store_id)
    if keyword:
        q = q.filter(models.Bill.customer.like(f"%{keyword}%"))
    # 账期 [period_start, period_end] 与查询区间 [start, end] 有交集即命中
    if start is not None:
        q = q.filter(models.Bill.period_end >= start)
    if end is not None:
        q = q.filter(models.Bill.period_start <= end)
    if sent is not None:
        q = q.filter(models.Bill.sent == sent)
    if paid is not None:
        q = q.filter(models.Bill.paid == paid)
    return q.order_by(models.Bill.created_at.desc()).all()


def get_bill(db: Session, bill_id: int):
    return _bill_q(db).filter(models.Bill.id == bill_id).first()


def mark_bill_sent(db: Session, bill_id: int, value: bool):
    obj = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not obj:
        return None
    obj.sent = value
    obj.sent_at = datetime.now() if value else None
    db.commit()
    return get_bill(db, bill_id)


def mark_bill_paid(db: Session, bill_id: int, value: bool):
    obj = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not obj:
        return None
    obj.paid = value
    obj.paid_at = datetime.now() if value else None
    db.commit()
    return get_bill(db, bill_id)


def delete_bill(db: Session, bill_id: int):
    obj = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not obj:
        return None
    # 先释放关联订单，允许它们重新出账
    db.query(models.Order).filter(models.Order.bill_id == bill_id).update(
        {models.Order.bill_id: None}, synchronize_session=False)
    db.delete(obj)   # bill_items 随 cascade 删除
    db.commit()
    return obj
