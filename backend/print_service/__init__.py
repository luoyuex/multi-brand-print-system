"""本地静默打印模块。

职责划分：
- config       打印配置（默认打印机、份数），持久化到 print_config.json
- gdi_printer  用 pywin32 GDI 直接在打印机 DC 上绘制送货单（方向/走纸由代码定死）
- renderer     Jinja2 渲染账单小票 HTML → Playwright 子进程截图成 PNG
- printer      枚举系统打印机 + 查询打印机状态 / 等待出纸
- service      串行打印队列，编排 构造数据 → 送打印机，供路由调用
"""
