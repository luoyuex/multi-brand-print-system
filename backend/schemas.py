from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ── Brand ──────────────────────────────────────────────
class BrandBase(BaseModel):
    name: str

class BrandCreate(BrandBase):
    pass

class BrandOut(BrandBase):
    id: int
    class Config:
        from_attributes = True


# ── Store ──────────────────────────────────────────────
class StoreBase(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StoreOut(StoreBase):
    id: int
    class Config:
        from_attributes = True


# ── Product ────────────────────────────────────────────
class ProductBase(BaseModel):
    brand_id: int
    code: str
    name: str
    spec: Optional[str] = None
    price: float

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    spec: Optional[str] = None
    price: Optional[float] = None

class ProductOut(ProductBase):
    id: int
    class Config:
        from_attributes = True


# ── OrderItem ──────────────────────────────────────────
class OrderItemIn(BaseModel):
    product_code: Optional[str] = None
    product_name: str
    spec: Optional[str] = None
    qty: float
    price: float
    manual_price: bool = False
    is_replacement: bool = False   # 补货行：坏损补发，单价/小计为 0

class OrderItemOut(OrderItemIn):
    id: int
    class Config:
        from_attributes = True


# ── Order ──────────────────────────────────────────────
class OrderCreate(BaseModel):
    brand_id: int
    store_id: int           # 选店铺，后端自动填 customer 字段
    items: List[OrderItemIn]

class OrderUpdate(BaseModel):
    items: List[OrderItemIn]

class OrderOut(BaseModel):
    id: int
    brand_id: int
    brand_name: str         # 关联品牌名称
    store_id: Optional[int] = None
    customer: str
    created_at: datetime
    status: str             # pending | printed
    printed_at: Optional[datetime] = None
    items: List[OrderItemOut]
    class Config:
        from_attributes = True
