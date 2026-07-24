from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date


# ── User（账号）─────────────────────────────────────────
class UserBase(BaseModel):
    username: str
    name: Optional[str] = None
    role: str = "staff"          # admin | staff

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None   # 传入则重置密码

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class LoginIn(BaseModel):
    username: str
    password: str

class LoginOut(BaseModel):
    token: str
    user: UserOut

class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


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
    brand_id: Optional[int] = None   # 所属品牌（一店一品牌）
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    brand_id: Optional[int] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StoreOut(StoreBase):
    id: int
    brand_name: Optional[str] = None   # 关联品牌名称（列表展示用）
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
    bill_id: Optional[int] = None   # 已出账则非空
    items: List[OrderItemOut]
    class Config:
        from_attributes = True


# ── Bill（对账单）────────────────────────────────────────
class BillItemOut(BaseModel):
    id: int
    order_id: Optional[int] = None
    order_date: Optional[date] = None
    product_name: Optional[str] = None
    spec: Optional[str] = None
    qty: float
    price: float
    subtotal: float
    is_replacement: bool = False
    class Config:
        from_attributes = True

class BillOut(BaseModel):
    id: int
    store_id: Optional[int] = None
    customer: str
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    period_start: date
    period_end: date
    total_amount: float
    order_count: int
    sent: bool
    sent_at: Optional[datetime] = None
    paid: bool
    paid_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    items: List[BillItemOut] = []
    class Config:
        from_attributes = True

# 生成/预览入参：某客户 + 账期区间（含首尾两天）
class BillPreviewIn(BaseModel):
    store_id: int
    start: date
    end: date
    # 编辑账单改期时传入：预览时把「已属于本账单」的订单也算进来（否则被认领的订单看不到）
    bill_id: Optional[int] = None

class BillCreate(BillPreviewIn):
    note: Optional[str] = None

# 编辑账单：改账期（重算明细）/ 备注
class BillUpdate(BaseModel):
    start: date
    end: date
    note: Optional[str] = None

# 预览用的轻量明细行（未落库）
class BillLine(BaseModel):
    product_name: Optional[str] = None
    spec: Optional[str] = None
    qty: float
    price: float
    subtotal: float
    is_replacement: bool = False

class BillPreviewDay(BaseModel):
    date: date
    items: List[BillLine]
    subtotal: float

class BillPreviewOut(BaseModel):
    store_id: int
    customer: str
    brand_name: Optional[str] = None
    period_start: date
    period_end: date
    order_count: int
    total: float
    days: List[BillPreviewDay]

# 标记已发送 / 已回款复用（value=True 置位，False 取消）
class MarkStatusIn(BaseModel):
    value: bool
