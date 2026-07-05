# 🧾 多品牌录单打印系统

面向门店/批发/配送场景的高频录单 + 本地自动打印系统。

## 核心能力

- **多品牌商品体系** — 切换品牌即切换商品体系，各品牌商品独立管理
- **快速录单** — 支持序号输入、名称搜索、模糊匹配，回车即加入订单
- **手动改价** — 默认使用商品价格，支持逐项手动修改
- **订单打印** — 对接 Electron 本地打印服务，支持多模板打印
- **店铺管理** — 客户/店铺信息维护，录单时快速选择
- **响应式布局** — 桌面端水平导航 + 移动端底部 Tab 栏，适配 PC/平板/手机

## 系统架构

```
┌──────────────────┐
│  Vue3 前端 (5173) │  ← Element Plus + Pinia
└────────┬─────────┘
         │ /api 代理
┌────────▼─────────┐
│ FastAPI 后端(8000)│  ← SQLAlchemy + PyMySQL
└────────┬─────────┘
         │
┌────────▼─────────┐
│   MySQL 数据库    │  ← print_system
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Electron 打印服务 │  ← 本地打印机
└──────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy + Pydantic + Uvicorn |
| 数据库 | MySQL (PyMySQL 驱动) |
| 桌面打印 | Electron PrintService |

## 项目结构

```
multi-brand-print-system/
├── frontend/          # Vue3 前端应用
│   ├── src/
│   │   ├── api/       # Axios API 封装
│   │   ├── composables/  # 组合式函数 (useBreakpoint)
│   │   ├── stores/    # Pinia 状态管理 (brand, order)
│   │   ├── views/     # 页面组件
│   │   ├── router/    # 路由配置
│   │   └── styles/    # 全局样式
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── backend/           # FastAPI 后端服务
│   ├── routers/       # API 路由 (brands, products, orders, stores)
│   ├── models.py      # SQLAlchemy 数据模型
│   ├── schemas.py     # Pydantic 请求/响应模型
│   ├── crud.py        # 数据库 CRUD 操作
│   ├── database.py    # 数据库连接配置
│   ├── main.py        # 应用入口
│   ├── .env           # 环境变量
│   └── requirements.txt
└── print_system.md    # 原始需求文档
```

## 快速开始

### 前置条件

- **Node.js** ≥ 16
- **Python** ≥ 3.10
- **MySQL** ≥ 5.7，并创建数据库 `print_system`

### 1. 初始化数据库

```sql
CREATE DATABASE print_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

首次启动后端时会自动建表。

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 .env（按需修改数据库连接信息）
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=root
# DB_PASSWORD=root
# DB_NAME=print_system

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端启动后访问 http://127.0.0.1:8000 可验证服务状态，访问 http://127.0.0.1:8000/docs 查看自动生成的 API 文档。

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后访问 http://localhost:5173，`/api` 请求会自动代理到后端 `http://127.0.0.1:8000`。

### 4. 构建生产版本

```bash
cd frontend
npm run build
```

构建产物输出到 `frontend/dist/`。

## API 概览

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 品牌 | GET | `/api/brands/` | 获取品牌列表 |
| 品牌 | POST | `/api/brands/` | 创建品牌 |
| 商品 | GET | `/api/products/` | 获取商品列表（支持 brand_id, search 筛选） |
| 商品 | POST | `/api/products/` | 创建商品 |
| 商品 | PUT | `/api/products/{id}` | 更新商品 |
| 商品 | DELETE | `/api/products/{id}` | 删除商品 |
| 店铺 | GET | `/api/stores/` | 获取店铺列表（支持 search 筛选） |
| 店铺 | POST | `/api/stores/` | 创建店铺 |
| 店铺 | PUT | `/api/stores/{id}` | 更新店铺 |
| 店铺 | DELETE | `/api/stores/{id}` | 删除店铺 |
| 订单 | GET | `/api/orders/` | 获取订单列表 |
| 订单 | GET | `/api/orders/{id}` | 获取订单详情 |
| 订单 | POST | `/api/orders/` | 创建订单 |
| 订单 | PUT | `/api/orders/{id}` | 更新订单 |
| 订单 | POST | `/api/orders/{id}/print` | 标记订单已打印 |

完整 API 文档请启动后端后访问 `/docs`（Swagger UI）或 `/redoc`（ReDoc）。

## 数据模型

```
Brand ──< Product        一个品牌下有多个商品
  │
  └──< Order ──< OrderItem   一个品牌下有多个订单，一个订单有多个明细项
        │
Store ──┘                     一个店铺有多个订单
```

## 页面功能

| 页面 | 路径 | 功能 |
|------|------|------|
| 录单 | `/` | 品牌切换、商品选择、数量输入、手动改价、提交订单 |
| 打印列表 | `/print` | 查看订单、标记已打印 |
| 店铺管理 | `/stores` | 店铺 CRUD |
| 商品管理 | `/products` | 商品 CRUD（按品牌筛选） |
| 品牌管理 | `/brands` | 品牌 CRUD |

## License

Private — 内部使用
