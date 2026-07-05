from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import engine, Base
from routers import brands, products, orders, stores

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
        ]
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
        conn.commit()

_run_migrations()

app = FastAPI(title="多品牌录单系统", version="1.0.0")

# 跨域（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brands.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(orders.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "多品牌录单系统后端运行中"}
