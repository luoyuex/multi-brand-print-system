from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    products = relationship("Product", back_populates="brand")
    orders = relationship("Order", back_populates="brand")
    stores = relationship("Store", back_populates="brand")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)      # 店铺名称
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)  # 所属品牌（一店一品牌）
    contact = Column(String(50))                    # 联系人
    phone = Column(String(30))                      # 电话
    address = Column(String(200))                   # 地址

    orders = relationship("Order", back_populates="store")
    brand = relationship("Brand", back_populates="stores")

    @property
    def brand_name(self):
        return self.brand.name if self.brand else ""


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    spec = Column(String(50))
    price = Column(Numeric(10, 2), nullable=False)

    brand = relationship("Brand", back_populates="products")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    customer = Column(String(100), nullable=False)  # 冗余存储店铺名，方便历史查询
    created_at = Column(DateTime, server_default=func.now())
    status = Column(String(20), nullable=False, default="pending")   # pending | printed
    printed_at = Column(DateTime, nullable=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)  # 已出账则非空，防止同一单重复出账

    brand = relationship("Brand", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def brand_name(self):
        return self.brand.name if self.brand else ""


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_code = Column(String(20))
    product_name = Column(String(100))
    spec = Column(String(50))
    qty = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    manual_price = Column(Boolean, default=False)
    is_replacement = Column(Boolean, default=False)   # 补货（东西坏了免费补发，单价小计为 0）

    order = relationship("Order", back_populates="items")


class Bill(Base):
    """对账单：把某客户一段账期内尚未出账的订单，快照成一张不可变凭证。

    快照 total_amount / 明细，账单一旦生成即固定，不随订单后续增删改变动，
    作为「发给客户的账单」的真实留档；sent / paid 两个标记独立跟踪发送与回款。
    """
    __tablename__ = "bills"

    id            = Column(Integer, primary_key=True, index=True)
    store_id      = Column(Integer, ForeignKey("stores.id"), nullable=True)
    customer      = Column(String(100), nullable=False)   # 快照店铺名，方便历史查询
    brand_id      = Column(Integer, ForeignKey("brands.id"), nullable=True)
    brand_name    = Column(String(50))                    # 快照品牌名（小票标题用）
    period_start  = Column(Date, nullable=False)          # 账期起（含当天）
    period_end    = Column(Date, nullable=False)          # 账期止（含当天）
    total_amount  = Column(Numeric(10, 2), nullable=False, default=0)   # 快照总额
    order_count   = Column(Integer, nullable=False, default=0)
    sent          = Column(Boolean, nullable=False, default=False)      # 是否已发送给客户
    sent_at       = Column(DateTime, nullable=True)
    paid          = Column(Boolean, nullable=False, default=False)      # 是否已回款
    paid_at       = Column(DateTime, nullable=True)
    note          = Column(String(255), nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    """账单明细快照：出账时从订单明细逐行拷入，之后与订单解耦。"""
    __tablename__ = "bill_items"

    id             = Column(Integer, primary_key=True, index=True)
    bill_id        = Column(Integer, ForeignKey("bills.id"), nullable=False)
    order_id       = Column(Integer, nullable=True)   # 溯源用，不设 FK（订单可能被删）
    order_date     = Column(Date, nullable=True)      # 归到哪一天（多天账单按天分组用）
    product_name   = Column(String(100))
    spec           = Column(String(50))
    qty            = Column(Numeric(10, 2))
    price          = Column(Numeric(10, 2))
    subtotal       = Column(Numeric(10, 2))
    is_replacement = Column(Boolean, default=False)

    bill = relationship("Bill", back_populates="items")
