"""本地静默打印模块。

职责划分：
- config   打印配置（默认打印机、纸张、SumatraPDF 路径），持久化到 print_config.json
- renderer Jinja2 渲染 HTML → Playwright(Chromium) 转 PDF
- printer  枚举系统打印机 + 调 SumatraPDF 静默打印 PDF
- service  串行打印队列，编排 渲染 → 打印，供路由调用
"""
