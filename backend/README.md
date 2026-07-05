# ⚙️ 多品牌录单系统 — 后端

基于 FastAPI + SQLAlchemy 的多品牌录单打印系统后端 API 服务。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.111+ | Web 框架 |
| Uvicorn | 0.30+ | ASGI 服务器 |
| SQLAlchemy | 2.0+ | ORM |
| PyMySQL | 1.1+ | MySQL 驱动 |
| Pydantic | 2.7+ | 数据校验 / 序列化 |
| Alembic | 1.13+ | 数据库迁移（预留） |
| python-dotenv | 1.0+ | 环境变量加载 |

## 目录结构

```
backend/
├── main.py             # 应用入口（FastAPI 实例、CORS、路由注册、自动建表迁移）
├── database.py         # 数据库连接（SQLAlchemy engine / session）
├── models.py           # SQLAlchemy ORM 模型（Brand, Store, Product, Order, OrderItem）
├── schemas.py          # Pydantic 请求/响应模型
├── crud.py             # 数据库 CRUD 操作函数
├── routers/
│   ├── __init__.py
│   ├── brands.py       # /api/brands  品牌路由
│   ├── products.py     # /api/products 商品路由
│   ├── stores.py       # /api/stores  店铺路由
│   └── orders.py       # /api/orders  订单路由
├── .env                # 环境变量配置
├── requirements.txt    # Python 依赖
└── venv/               # 虚拟环境（不提交到版本库）
```

## 快速开始

### 1. 准备数据库

确保 MySQL 已运行，并创建数据库：

```sql
CREATE DATABASE print_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置环境变量

编辑 `.env` 文件（已提供默认值）：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=print_system
```

### 3. 创建虚拟环境 & 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 启动服务

```bash
# 开发模式（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

启动后：
- API 服务：http://127.0.0.1:8000
- Swagger 文档：http://127.0.0.1:8000/docs
- ReDoc 文档：http://127.0.0.1:8000/redoc

## 自动建表 & 迁移

首次启动时，`main.py` 会自动执行：

1. **`Base.metadata.create_all()`** — 自动创建所有不存在的表
2. **`_run_migrations()`** — 安全补列迁移，对已存在的表添加新列（如 `orders.store_id`、`orders.status`、`orders.printed_at`）

> 迁移逻辑会先检查 `information_schema.COLUMNS`，列已存在则跳过，不会重复执行。

## 数据模型

### Brand（品牌）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| name | VARCHAR(50) | 品牌名称 |

### Store（店铺）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| name | VARCHAR(100) | 店铺名称 |
| contact | VARCHAR(50) | 联系人 |
| phone | VARCHAR(30) | 电话 |
| address | VARCHAR(200) | 地址 |

### Product（商品）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| brand_id | INT | 外键 → brands.id |
| code | VARCHAR(20) | 商品序号 |
| name | VARCHAR(100) | 商品名称 |
| spec | VARCHAR(50) | 规格 |
| price | DECIMAL(10,2) | 价格 |

### Order（订单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| brand_id | INT | 外键 → brands.id |
| store_id | INT | 外键 → stores.id |
| customer | VARCHAR(100) | 客户名（冗余存储店铺名） |
| created_at | DATETIME | 创建时间 |
| status | VARCHAR(20) | 状态：pending / printed |
| printed_at | DATETIME | 打印时间 |

### OrderItem（订单明细）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| order_id | INT | 外键 → orders.id |
| product_code | VARCHAR(20) | 商品序号 |
| product_name | VARCHAR(100) | 商品名称 |
| spec | VARCHAR(50) | 规格 |
| qty | DECIMAL(10,2) | 数量 |
| price | DECIMAL(10,2) | 单价 |
| manual_price | BOOLEAN | 是否手动改价 |

### 模型关系

```
Brand ──< Product        (一对多)
Brand ──< Order          (一对多)
Store  ──< Order         (一对多)
Order  ──< OrderItem     (一对多，级联删除)
```

## API 接口

### 品牌 `/api/brands`

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/brands/` | 获取品牌列表 | — | `BrandOut[]` |
| POST | `/api/brands/` | 创建品牌 | `BrandCreate` | `BrandOut` |

### 商品 `/api/products`

| 方法 | 路径 | 说明 | 参数 | 请求体 | 响应 |
|------|------|------|------|--------|------|
| GET | `/api/products/` | 获取商品列表 | `brand_id?`, `search?` | — | `ProductOut[]` |
| POST | `/api/products/` | 创建商品 | — | `ProductCreate` | `ProductOut` |
| PUT | `/api/products/{id}` | 更新商品 | — | `ProductUpdate` | `ProductOut` |
| DELETE | `/api/products/{id}` | 删除商品 | — | — | `{ok: true}` |

### 店铺 `/api/stores`

| 方法 | 路径 | 说明 | 参数 | 请求体 | 响应 |
|------|------|------|------|--------|------|
| GET | `/api/stores/` | 获取店铺列表 | `search?` | — | `StoreOut[]` |
| POST | `/api/stores/` | 创建店铺 | — | `StoreCreate` | `StoreOut` |
| PUT | `/api/stores/{id}` | 更新店铺 | — | `StoreUpdate` | `StoreOut` |
| DELETE | `/api/stores/{id}` | 删除店铺 | — | — | `{ok: true}` |

### 订单 `/api/orders`

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/orders/` | 获取订单列表 | — | `OrderOut[]` |
| GET | `/api/orders/{id}` | 获取订单详情 | — | `OrderOut` |
| POST | `/api/orders/` | 创建订单 | `OrderCreate` | `OrderOut` |
| PUT | `/api/orders/{id}` | 更新订单明细 | `OrderUpdate` | `OrderOut` |
| POST | `/api/orders/{id}/print` | 标记已打印 | — | `OrderOut` |

## CORS 配置

开发阶段允许所有来源跨域访问（`allow_origins=["*"]`），生产环境请在 `main.py` 中修改为具体的前端域名。

## Pydantic Schemas

所有请求/响应模型定义在 `schemas.py` 中，遵循以下命名规范：

- `*Base` — 基础字段
- `*Create` — 创建请求
- `*Update` — 更新请求（所有字段 Optional）
- `*Out` — 响应输出（含 id，`from_attributes = True`）

## 注意事项

- 订单创建时，`customer` 字段由后端根据 `store_id` 自动填充店铺名称
- 订单更新采用"删除旧行 + 插入新行"策略替换明细项
- `OrderOut.brand_name` 通过 SQLAlchemy relationship 动态获取
- 数据库连接使用 `pymysql` 驱动，字符集为 `utf8mb4`
