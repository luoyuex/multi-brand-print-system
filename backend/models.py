from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    products = relationship("Product", back_populates="brand")
    orders = relationship("Order", back_populates="brand")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)      # 店铺名称
    contact = Column(String(50))                    # 联系人
    phone = Column(String(30))                      # 电话
    address = Column(String(200))                   # 地址

    orders = relationship("Order", back_populates="store")


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
