"""对账单相关路由 /api/bills

- GET    /api/bills/                查询账单列表（客户/账期/发送/回款 多条件筛选）
- POST   /api/bills/preview         预览某客户某账期的未出账汇总（不落库）
- POST   /api/bills/                生成账单（认领未出账订单）
- POST   /api/bills/generate-today  一键生成今日账单（每个有未出账订单的客户各一张）
- GET    /api/bills/{id}            账单详情
- PATCH  /api/bills/{id}/sent       标记/取消「已发送客户」
- PATCH  /api/bills/{id}/paid       标记/取消「已回款」
- DELETE /api/bills/{id}            删除账单（释放订单可重新出账）

账单小票图片改由前端 html2canvas 生成（见 frontend BillReceipt.vue），后端不再出图。
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("/", response_model=List[schemas.BillOut])
def list_bills(
    store_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None, description="按客户名模糊搜索"),
    start_date: Optional[date] = Query(None, description="账期起 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="账期止 YYYY-MM-DD"),
    sent: Optional[bool] = Query(None, description="是否已发送（留空=全部）"),
    paid: Optional[bool] = Query(None, description="是否已回款（留空=全部）"),
    db: Session = Depends(get_db),
):
    return crud.get_bills(
        db, store_id=store_id, keyword=keyword,
        start=start_date, end=end_date, sent=sent, paid=paid,
    )


@router.post("/preview", response_model=schemas.BillPreviewOut)
def preview_bill(data: schemas.BillPreviewIn, db: Session = Depends(get_db)):
    """预览某客户某账期内未出账订单的汇总（按天分组），不写库。"""
    if not crud.get_store(db, data.store_id):
        raise HTTPException(status_code=404, detail="店铺不存在")
    if data.end < data.start:
        raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
    return crud.preview_bill(db, data.store_id, data.start, data.end,
                             include_bill_id=data.bill_id)


@router.post("/summary", response_model=schemas.BillPreviewOut)
def summary_bill(data: schemas.BillPreviewIn, db: Session = Depends(get_db)):
    """回款对账汇总（只读）：把某客户账期内**所有**订单（无视是否已出账）按天汇总。

    专供要回款时拉一张多天总账发客户，不落库、不认领订单，与日常出账流程解耦。
    """
    if not crud.get_store(db, data.store_id):
        raise HTTPException(status_code=404, detail="店铺不存在")
    if data.end < data.start:
        raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
    return crud.summary_bill(db, data.store_id, data.start, data.end)


@router.post("/", response_model=schemas.BillOut, status_code=201)
def create_bill(data: schemas.BillCreate, db: Session = Depends(get_db)):
    if not crud.get_store(db, data.store_id):
        raise HTTPException(status_code=404, detail="店铺不存在")
    if data.end < data.start:
        raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
    bill = crud.create_bill(db, data.store_id, data.start, data.end, data.note)
    if not bill:
        raise HTTPException(status_code=400, detail="该客户在所选账期内没有未出账的订单")
    return crud.get_bill(db, bill.id)


@router.post("/generate-today")
def generate_today(db: Session = Depends(get_db)):
    """一键生成今日账单：对今天有未出账订单的每个客户各出一张。"""
    today = datetime.now().date()
    store_ids = crud.get_unbilled_store_ids(db, today, today)
    created = 0
    for sid in store_ids:
        if crud.create_bill(db, sid, today, today, None):
            created += 1
    return {"created": created, "customers": len(store_ids)}


@router.get("/{bill_id}", response_model=schemas.BillOut)
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    obj = crud.get_bill(db, bill_id)
    if not obj:
        raise HTTPException(status_code=404, detail="账单不存在")
    return obj


@router.patch("/{bill_id}", response_model=schemas.BillOut)
def update_bill(bill_id: int, data: schemas.BillUpdate, db: Session = Depends(get_db)):
    """编辑账单：改账期（会释放原订单、按新账期重新认领并重算明细）/ 备注。

    账单 id、发送/回款状态、生成时间保持不变。新账期内没有可用订单时报 400。
    """
    if not crud.get_bill(db, bill_id):
        raise HTTPException(status_code=404, detail="账单不存在")
    if data.end < data.start:
        raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
    bill = crud.update_bill(db, bill_id, data.start, data.end, data.note)
    if bill is None:
        raise HTTPException(status_code=404, detail="账单不存在")
    if bill == "empty":
        raise HTTPException(status_code=400, detail="新账期内没有可归入该客户的订单")
    return crud.get_bill(db, bill_id)


@router.patch("/{bill_id}/sent", response_model=schemas.BillOut)
def mark_sent(bill_id: int, data: schemas.MarkStatusIn, db: Session = Depends(get_db)):
    obj = crud.mark_bill_sent(db, bill_id, data.value)
    if not obj:
        raise HTTPException(status_code=404, detail="账单不存在")
    return obj


@router.patch("/{bill_id}/paid", response_model=schemas.BillOut)
def mark_paid(bill_id: int, data: schemas.MarkStatusIn, db: Session = Depends(get_db)):
    obj = crud.mark_bill_paid(db, bill_id, data.value)
    if not obj:
        raise HTTPException(status_code=404, detail="账单不存在")
    return obj


@router.delete("/{bill_id}", status_code=204)
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    obj = crud.delete_bill(db, bill_id)
    if not obj:
        raise HTTPException(status_code=404, detail="账单不存在")
    return None
