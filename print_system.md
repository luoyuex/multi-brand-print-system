# 🖨️ 订单打印服务方案（本地静默打印）

> 目标：把当前「浏览器 `window.print()` 弹框打印」升级为「主机本地代理静默打印」，
> 支持平板远程操作、主机端 A4/A5 打印机出纸。

---

## 一、现状与问题

当前实现（`frontend/src/views/PrintQueue.vue`）：

- 点「打印」→ 设置 `printingOrder` → `window.print()` → 走 `@media print` CSS 只显示 `#print-area`。
- 依赖浏览器打印对话框，用户要手动选打印机、点确定。

**问题**：实际部署是「平板访问网页、打印机接在主机上」。平板浏览器的
`window.print()` 只能调用平板本地的打印能力，**打不到主机上的打印机**。所以必须
换成「主机本地打印」架构。

---

## 二、部署形态（已确认）

| 项 | 结论 |
|----|------|
| 打印机位置 | 接在一台 Windows 主机上 |
| 后端 / 前端 | 部署在同一台主机上 |
| 操作端 | 平板通过局域网访问网页 UI |
| 打印机类型 | A4 / A5 普通打印机（激光/喷墨） |
| 触发方式 | 手动点「打印」按钮 |

```
   平板(浏览器)                主机 (同一台电脑)
 ┌────────────┐   LAN     ┌──────────────────────────────────┐
 │  Vue UI    │ ───────▶  │  FastAPI 后端 :8000               │
 │  点「打印」 │           │        │ 127.0.0.1 转发            │
 └────────────┘           │        ▼                          │
                          │  打印代理 PrintAgent :17777        │
                          │        │ 静默渲染 HTML + 打印       │
                          │        ▼                          │
                          │   A4/A5 打印机                     │
                          └──────────────────────────────────┘
```

**关键点**：平板只跟后端说话，后端在本机通过 `127.0.0.1` 把任务转发给打印代理。
好处：
- 平板不需要知道打印代理的地址、不涉及跨端 CORS。
- 打印代理只监听 `127.0.0.1`，不对外暴露，安全。
- 单一入口，前端逻辑简单。

---

## 三、技术选型

打印代理需要「高保真渲染 HTML/CSS + 在 Windows 上静默打印到指定打印机」。

### ✅ 推荐：Electron 打印代理

- 用 Chromium 渲染，模板所见即所得，CSS 分页、表格都稳。
- `webContents.print({ silent: true, deviceName })` 原生支持**静默打印**、指定打印机。
- `webContents.getPrintersAsync()` 可枚举系统打印机，供前端选择。
- 系统托盘常驻、开机自启、测试打印都很自然。
- 可用 `electron-builder` 打成单个 `PrintAgent.exe`，主机上双击即用。

### 备选：Python + 无头浏览器/SumatraPDF

- 后端已是 Python，可在后端内直接渲染 HTML → PDF（`playwright`/无头 Edge）→
  用 `SumatraPDF -print-to` 静默打印。省一个进程、单语言。
- 缺点：需额外打包 SumatraPDF 或 Playwright 浏览器内核；打印机枚举/状态反馈不如
  Electron 顺手。

> **建议采用 Electron 代理**（与原始设计一致、维护心智负担最低）。下文按此展开。

---

## 四、组件职责

### 1) PrintAgent（Electron，主机常驻）

监听 `http://127.0.0.1:17777`，接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/health`   | 健康检查，返回 `{ ok: true, version }` |
| GET  | `/printers` | 返回系统打印机列表 + 当前默认打印机 |
| POST | `/print`    | 接收打印任务，入队 → 渲染 → 静默打印 |
| POST | `/test`     | 打印一张测试页（托盘菜单也可触发） |

内部：
- **打印队列**：任务串行执行，避免并发抢打印机。
- **模板渲染**：隐藏 `BrowserWindow` 载入模板 HTML，注入订单数据后 `print`。
- **托盘菜单**：选择默认打印机、查看队列状态、测试打印、退出。
- **配置持久化**：默认打印机、纸张（A4/A5）存本地 `config.json`。

### 2) FastAPI 后端（新增转发层）

- 新增配置：`PRINT_AGENT_URL=http://127.0.0.1:17777`。
- 改造 `POST /api/orders/{id}/print`：
  1. 查订单（含 items、品牌名、店铺名）。
  2. 组装打印任务 JSON，`POST` 给打印代理。
  3. 代理返回成功 → `mark_printed` 标记已打印 → 返回订单。
  4. 代理离线/失败 → 返回 4xx/5xx，`detail` 说明「打印服务未启动」，前端提示。
- 新增 `GET /api/print/printers` → 透传代理的打印机列表（供前端设置页）。

### 3) 前端 PrintQueue.vue（改造）

- `handlePrint(order)`：改为 `await orderApi.print(id)`，根据结果 `ElMessage` 成功/失败。
- 移除 `window.print()` / `#print-area` / `@media print` 这套浏览器打印逻辑
  （或保留为「无代理时的降级打印」，可选）。
- 可选：设置页选择目标打印机、纸张大小。

---

## 五、打印任务数据契约

后端 → 代理 `POST /print` body：

```json
{
  "job_id": "order-128",
  "template": "delivery_a5",
  "printer": "",                      // 空=用代理默认打印机
  "paper": "A5",
  "copies": 1,
  "data": {
    "brand_name": "MISS",
    "customer": "客户A",
    "order_id": 128,
    "created_at": "2026-07-05 14:30",
    "items": [
      { "index": 1, "product_name": "西瓜", "spec": "个", "qty": 10, "price": 1.80, "subtotal": 18.00 }
    ],
    "total": 18                       // 合计取整（与现有页面一致）
  }
}
```

代理响应：`{ "ok": true, "job_id": "order-128" }` 或 `{ "ok": false, "error": "..." }`。

---

## 六、模板方案

- 模板为独立 HTML 文件（`templates/delivery_a5.html`），用轻量引擎渲染
  （Handlebars 或原生模板字符串）。
- A4/A5 页面样式，含：品牌抬头、客户、日期、单号、商品表格、合计（整数）。
- **多模板可扩展**：按 `template` 字段或按品牌选择不同模板，后续加「小票模板」也
  只是多一个 HTML + 一套 `@page` 尺寸。
- 页面用 `@page { size: A5; margin: 8mm; }` 控制纸张与页边距。

---

## 七、实施步骤（分阶段）

**Phase 1 — 打印代理骨架**
- [ ] 新建 `print-agent/`（Electron 项目）：主进程 + 本地 HTTP 服务 + 托盘。
- [ ] 实现 `/health`、`/printers`、`/test`。
- [ ] 隐藏窗口渲染 + `webContents.print({ silent, deviceName })` 打通静默打印。

**Phase 2 — 模板与打印队列**
- [ ] `templates/delivery_a5.html` + 渲染注入数据。
- [ ] 打印任务队列（串行）+ 错误处理。
- [ ] `/print` 接口跑通「JSON → 出纸」。

**Phase 3 — 后端转发层**
- [ ] 配置 `PRINT_AGENT_URL`，改造 `POST /api/orders/{id}/print` 转发 + 标记已打印。
- [ ] 新增 `GET /api/print/printers`。
- [ ] 代理离线时的友好错误。

**Phase 4 — 前端接入**
- [ ] `orderApi.print` 走后端转发，替换 `window.print()`。
- [ ] 成功/失败提示；可选打印机选择设置页。

**Phase 5 — 打包与部署**
- [ ] `electron-builder` 打包 `PrintAgent.exe`，配开机自启。
- [ ] 主机部署说明：启动后端、启动代理、平板访问网页。
- [ ] 测试打印 + 真实订单端到端验证。

---

## 八、待确认 / 可选项

1. 是否需要「提交订单后自动打印」（当前定为手动，架构已兼容，后续加即可）。
2. 是否需要按品牌用不同模板 / 是否要小票模板（当前只做 A4/A5 发货单）。
3. 打印代理是否需要开机自启、是否需要打印失败重试策略。
4. 是否保留浏览器打印作为「代理未启动」的降级方案。
