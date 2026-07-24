# Windows 兼容：ProactorEventLoop 不支持 asyncio.create_subprocess_exec，
# 而 Playwright 内部用它启动浏览器子进程，导致 NotImplementedError。
# 改用 SelectorEventLoop 可以正常创建子进程。
import sys, asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import engine, Base, SessionLocal
from routers import brands, products, orders, stores, print as print_router, bills, auth as auth_router
import auth

# 建表（首次启动自动建表）
Base.metadata.create_all(bind=engine)

# 安全补列迁移（create_all 不会给已存在的表加列）
def _run_migrations():
    # table -> [(column_name, DDL), ...]
    migrations = {
        "orders": [
            ("store_id",   "ALTER TABLE orders ADD COLUMN store_id INT"),
            ("status",     "ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"),
            ("printed_at", "ALTER TABLE orders ADD COLUMN printed_at DATETIME"),
            ("bill_id",    "ALTER TABLE orders ADD COLUMN bill_id INT"),
        ],
        "order_items": [
            ("is_replacement", "ALTER TABLE order_items ADD COLUMN is_replacement TINYINT(1) NOT NULL DEFAULT 0"),
        ],
        "stores": [
            ("brand_id", "ALTER TABLE stores ADD COLUMN brand_id INT"),
        ],
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            for col, ddl in cols:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    f"AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{col}'"
                ))
                if result.scalar() == 0:
                    conn.execute(text(ddl))
                    print(f"[migration] ALTER {table}.{col} — done")
                    # 新增 stores.brand_id：把存量店铺默认关联到品牌 1（Miss）
                    if table == "stores" and col == "brand_id":
                        conn.execute(text(
                            "UPDATE stores SET brand_id = 1 WHERE brand_id IS NULL"))
                        print("[migration] backfill stores.brand_id = 1 — done")
        conn.commit()

_run_migrations()


def _seed_admin():
    """首次启动无账号时，创建默认管理员 admin/admin123（请登录后尽快改密）。"""
    import models
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            db.add(models.User(
                username="admin",
                password_hash=auth.hash_password("admin123"),
                name="管理员",
                role="admin",
                is_active=True,
            ))
            db.commit()
            print("[seed] 已创建默认管理员 admin / admin123，请登录后尽快修改密码")
    finally:
        db.close()

_seed_admin()

app = FastAPI(title="多品牌录单系统", version="1.0.0")

# 跨域（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
# 登录即可访问：录单 / 打印需要读品牌·店铺·商品·订单，写操作在各路由内单独校验管理员
_login = [Depends(auth.get_current_user)]
_admin = [Depends(auth.require_admin)]
app.include_router(brands.router, dependencies=_login)
app.include_router(stores.router, dependencies=_login)
app.include_router(products.router, dependencies=_login)
app.include_router(orders.router, dependencies=_login)
app.include_router(print_router.router, dependencies=_login)
app.include_router(bills.router, dependencies=_admin)   # 账单仅管理员


@app.on_event("shutdown")
def _shutdown_print_service():
    from print_service import service
    service.shutdown()


@app.get("/")
def root():
    return {"status": "ok", "message": "多品牌录单系统后端运行中"}
