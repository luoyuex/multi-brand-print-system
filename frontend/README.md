# 🖥️ 多品牌录单系统 — 前端

基于 Vue 3 + Element Plus 的多品牌录单打印系统前端应用，支持 PC / 平板 / 手机多端适配。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| Vite | 5.2+ | 构建工具 |
| Element Plus | 2.7+ | UI 组件库 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.3+ | 路由 |
| Axios | 1.7+ | HTTP 请求 |

## 目录结构

```
frontend/
├── index.html              # HTML 入口
├── vite.config.js          # Vite 配置（含 API 代理）
├── package.json
├── src/
│   ├── main.js             # 应用入口，注册 Pinia / Router / Element Plus
│   ├── App.vue             # 根组件（顶部导航 + 底部 Tab 栏）
│   ├── api/
│   │   └── index.js        # Axios 实例 + API 封装（brand/store/product/order）
│   ├── composables/
│   │   └── useBreakpoint.js # 响应式断点检测（isMobile / isTablet）
│   ├── stores/
│   │   ├── brand.js        # 品牌状态（品牌列表、当前品牌切换）
│   │   └── order.js        # 订单草稿状态（localStorage 持久化）
│   ├── views/
│   │   ├── OrderEntry.vue  # 📝 录单页（核心页面）
│   │   ├── PrintQueue.vue  # 🖨️ 打印列表页
│   │   ├── Products.vue    # 📦 商品管理页
│   │   ├── Brands.vue      # 🏷️ 品牌管理页
│   │   └── Stores.vue      # 🏪 店铺管理页
│   ├── router/
│   │   └── index.js        # 路由配置
│   └── styles/
│       └── global.css      # 全局样式
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

启动后访问 http://localhost:5173。

> Vite 开发服务器已配置代理：`/api` → `http://127.0.0.1:8000`，无需手动处理跨域。

### 生产构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## API 代理配置

开发环境下，`vite.config.js` 中配置了 API 代理：

```js
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
}
```

所有 `/api/*` 请求会自动转发到后端 FastAPI 服务。

## 状态管理

### brand store (`stores/brand.js`)

管理品牌列表和当前选中品牌：

- `brands` — 品牌列表
- `currentBrand` — 当前选中品牌
- `fetchBrands()` — 从 API 加载品牌列表
- `selectBrand(brand)` — 切换当前品牌

### order store (`stores/order.js`)

管理订单草稿，自动持久化到 localStorage：

- `storeId` — 选中的店铺 ID
- `brandId` — 当前品牌 ID
- `items` — 订单明细项列表
- `total` — 订单总金额（计算属性）
- `addItem(product, qty)` — 添加商品到订单
- `updateItem(index, field, value)` — 修改明细项（改价时自动标记 manual_price）
- `removeItem(index)` — 删除明细项
- `clear()` — 清空草稿

> 草稿数据通过 `watch` 自动写入 `localStorage`，刷新页面不丢失。

## 响应式设计

通过 `useBreakpoint` 组合式函数实现：

- **移动端** (`< 768px`) — 底部 Tab 栏导航
- **平板** (`768px ~ 1024px`) — 顶部水平导航
- **桌面** (`≥ 1024px`) — 顶部水平导航

## API 接口

前端通过 `src/api/index.js` 统一封装了所有后端接口：

| 模块 | 方法 | 说明 |
|------|------|------|
| `brandApi.list()` | GET | 获取品牌列表 |
| `brandApi.create(data)` | POST | 创建品牌 |
| `storeApi.list(params)` | GET | 获取店铺列表 |
| `storeApi.create(data)` | POST | 创建店铺 |
| `storeApi.update(id, data)` | PUT | 更新店铺 |
| `storeApi.remove(id)` | DELETE | 删除店铺 |
| `productApi.list(params)` | GET | 获取商品列表 |
| `productApi.create(data)` | POST | 创建商品 |
| `productApi.update(id, data)` | PUT | 更新商品 |
| `productApi.remove(id)` | DELETE | 删除商品 |
| `orderApi.list()` | GET | 获取订单列表 |
| `orderApi.get(id)` | GET | 获取订单详情 |
| `orderApi.create(data)` | POST | 创建订单 |
| `orderApi.update(id, data)` | PUT | 更新订单 |
| `orderApi.markPrinted(id)` | POST | 标记已打印 |

## 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | OrderEntry | 录单（默认首页） |
| `/print` | PrintQueue | 打印列表 |
| `/stores` | Stores | 店铺管理 |
| `/products` | Products | 商品管理 |
| `/brands` | Brands | 品牌管理 |
