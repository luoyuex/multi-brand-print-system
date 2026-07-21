# 打印方案改造：从 PDF/SumatraPDF 换成 pywin32 GDI 直接绘制

## 背景与决策

送货单打印机是 **EPSON LQ-730KII ESC/P2**（针式，连续纸，针孔在长边）。
纸张物理尺寸 **241mm 宽 × 140mm 高**（横躺，行沿 241mm 长边水平走）。

### 旧方案为什么不行

旧链路：

```
Jinja2 HTML → Playwright 出 PDF → pymupdf 烤入旋转 → SumatraPDF -print → 驱动 → 打印机
```

实测暴露了两个 PDF 打印在这台针式机上无法解决的硬伤：

1. **方向不可控**。无论在 PDF 里把内容转 0° / 90° / 270°，SumatraPDF 在送进驱动前都会
   把页面「归一化」贴合驱动纸张方向，我们烤进 PDF 的旋转被无视——`print_rotate` 改任何
   值，打出来的朝向都一样（都是文字竖躺，和针孔差 90°）。驱动里切横向/纵向只是 180° 互翻，
   转不出想要的朝向。
2. **走纸长度不可控**。SumatraPDF 走普通 PDF 打印，不认针式连续纸的 139.5mm 分页，
   打完吐出一整张（约整页），浪费纸且撕纸位置错乱。

根因：**这两个毛病都发生在「我们代码管不到的最后一段」——SumatraPDF ↔ 打印机驱动。**
继续在 PDF 层调角度是死路。

### 新方案：pywin32 GDI 直接在打印机 DC 上绘制

用 `win32ui` 创建打印机 Device Context，直接用 GDI 画线、画文字，
不再经过 HTML / PDF / SumatraPDF / Playwright。

好处：

- **方向由代码定死**。坐标系原点在纸的左上角，x 沿 241mm 长边、y 沿 140mm 短边，
  文字天然沿针孔长边水平走。需要额外旋转时可用 `SetWorldTransform`，但标定已确认
  当前坐标系方向即为目标方向，**无需任何旋转**。
- **走纸长度由代码定死**。一张凭证 = 一个 `StartPage`/`EndPage`，只走一页（约 140mm），
  不吐整张。
- **少一大堆依赖和进程**。不再需要 Playwright（子进程 + Chromium）、pymupdf、SumatraPDF。

已用 `_gdi_test.py` 打样验证：方向正确（文字沿长边水平正读）、走纸只走一页。**方案可行，采用。**

## 关键设备参数（EPSON LQ-730KII，实测）

| 参数 | 值 |
|---|---|
| DPI (LOGPIXELSX/Y) | 180 × 180 |
| 可打印区 (HORZRES × VERTRES) | 1664 × 932 点 |
| 物理纸张 (PHYSICALWIDTH × HEIGHT) | 1707 × 992 点（≈ 241 × 140 mm）|
| 不可打印边距 (PHYSICALOFFSETX/Y) | 21 × 30 点 |
| 可打印区物理尺寸 (HORZSIZE × VERTSIZE) | 235 × 132 mm |

单位换算：

- `mm → dots`：`round(mm / 25.4 * 180)`
- `pt(磅) → dots`：`round(pt / 72 * 180)`

坐标系原点 (0,0) 是**可打印区**左上角，即物理左上角内缩 (21, 30) 点。
用 GetDeviceCaps 拿 HORZRES/VERTRES 作为可用画布宽高，不写死。

## 目标改动范围

只替换「把凭证送上打印机」这一层，**上层数据构造与路由完全不动**。

### 保持不变

- `service.build_print_data(order)` —— 订单 → 打印数据的转换（字段：`brand_name`,
  `customer`, `order_id`, `created_at`, `items[]`, `total`；item 字段：`index`,
  `product_name`, `spec`, `qty`, `price`, `subtotal`, `is_replacement`）。
- `routers/orders.py:84` 的 `service.submit("delivery_a5", data)` 调用签名。
- `batch.py` 的批量编排：`print_lock` 串行、`wait_until_idle` 等出纸、SSE 进度、失败跳过。
- `routers/print.py` 的 `/test`、`/config`、`/printers`、`/status` 接口。
- 账单小票（bill）走 Playwright 截图那条路 **不受影响**，继续保留 renderer 的 `html_to_image`。

### 需要新增

新增 `print_service/gdi_printer.py`，提供一个绘制送货单的函数，例如：

```python
def print_delivery(data: dict, printer: str | None = None, copies: int = 1) -> None:
    """用 GDI 直接把送货单数据画到打印机 DC 上并输出。

    data: service.build_print_data() 的产物。
    printer: 打印机名，None = 系统默认。
    copies: 份数。
    每份 = 一个 StartPage/EndPage，只走一页。
    """
```

内部职责：

1. `win32ui.CreateDC()` + `CreatePrinterDC(printer)`，读 HORZRES/VERTRES 作画布。
2. 表头区：日期 / 单号、客户，各占一行。
3. 表格：序号 / 品种 / 数量 / 售价 / 金额 / 规格 六列，列宽按毫米折算成点。
   - 用 `MoveTo`/`LineTo` 画表格边框和分隔线。
   - 用 `TextOut`（配合 `GetTextExtent` 做居中/右对齐）填字。
   - 补货行：售价/金额画「—」，品种后缀「补」标记。
4. 明细不足预定行数时补空行（沿用现有「短单铺满」的观感，行数按 140mm 高度重算）。
5. 底部：备注「水果质量问题24小时内包赔」+ 总计。
6. `StartDoc` → 每份 `StartPage`/`EndPage` → `EndDoc` → `DeleteDC`。

字体：`Microsoft YaHei`，粗体，正文约 10pt、标题略大，用 `CreateFont`
以 `height = -pt(size)` 指定字号（负值表示按字符高度）。

### 需要改的接线

- `service.render_and_print(...)`：把内部的
  `renderer.html_to_pdf(...) + printer.print_pdf(...)`
  替换为 `gdi_printer.print_delivery(data, printer_name, copies)`。
  函数签名和返回值 `{"ok": True}` 保持不变，`paper_code` 参数可保留但不再用于渲染
  （GDI 直接读打印机 DC 的实际可打印区）。
- 这样单打（`submit`）和批量（`batch._worker` 经 `render_and_print`）两条路自动都切到 GDI，
  且仍然共用 `print_lock` 串行、`wait_until_idle` 等出纸。
- `print_test` 的测试页也走同一个 GDI 函数（用样例数据）。

### 可以退役（保留代码但不再调用）

- `printer.print_pdf` / `_rotate_pdf`（PDF 旋转+SumatraPDF 打印）——送货单不再用。
- `renderer.html_to_pdf` / `_pdf_worker.py` 的 PDF 分支——送货单不再用。
- 配置项 `print_rotate`、`sumatra_path`——送货单不再依赖；先保留字段避免破坏
  `/config` 接口和已有 `print_config.json`，后续可清理。
- `templates/delivery_a5.html`——GDI 版不再需要 HTML 模板。

> 注：`printer.list_printers` / `get_status` / `wait_until_idle` 继续保留并使用——
> 它们是 pywin32/PowerShell 查询，和 GDI 方案完全兼容。

## 分步实施计划

1. **打样脚本转正**：以已验证的 `_gdi_test.py` 为基础，写出 `gdi_printer.py` 的
   `print_delivery`，先把真实的表头 + 表格 + 明细 + 合计画出来。
2. **本地打样**：用一条样例订单数据直接调 `print_delivery`，实机打一张核对
   方向、走纸、列宽、字号、补货行、空行填充。
3. **接线单打**：改 `service.render_and_print` 调 GDI；跑 `/api/print/test` 和
   单张订单打印路径验证。
4. **接线批量**：不改 `batch.py`（它经 `render_and_print`），批量打印跑一遍多单，
   确认串行、等出纸、进度、失败跳过都正常。
5. **回归**：账单小票（bill）截图路径确认未受影响。
6. **清理**：删除标定用的 `_orient_test*.py` / `_gdi_test.py` 等临时脚本；
   决定是否移除 PDF/SumatraPDF 相关的死代码与依赖（Playwright / pymupdf / SumatraPDF）。

## 待确认 / 风险点

- **列宽与字号**需要按 241mm 宽、180 DPI 重新排一遍，第 2 步实机打样时定稿。
- **空行填充行数**按 140mm 可用高度重算（旧的 20 行是按 241mm 高算的，不适用）。
- **中文字体**：确认打印机/系统能正确用 `Microsoft YaHei` 渲染，针式点阵下小字号
  清晰度以实机为准。
- **份数 copies**：GDI 里用多次 `StartPage/EndPage` 或多次 `StartDoc` 实现，
  第 3 步验证与 `wait_until_idle` 的配合（避免份数被当成多任务堆积）。
- **依赖清理**是否现在就做，待你决定（保留死代码更稳，删掉更干净）。
