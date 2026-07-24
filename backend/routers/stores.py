from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import crud, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/stores", tags=["stores"])


@router.get("/", response_model=List[schemas.StoreOut])
def list_stores(search: Optional[str] = None, brand_id: Optional[int] = None,
                db: Session = Depends(get_db)):
    return crud.get_stores(db, search=search, brand_id=brand_id)


@router.post("/", response_model=schemas.StoreOut, status_code=201,
             dependencies=[Depends(auth.require_admin)])
def create_store(store: schemas.StoreCreate, db: Session = Depends(get_db)):
    return crud.create_store(db, store)


@router.put("/{store_id}", response_model=schemas.StoreOut,
            dependencies=[Depends(auth.require_admin)])
def update_store(store_id: int, data: schemas.StoreUpdate, db: Session = Depends(get_db)):
    obj = crud.update_store(db, store_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return obj


@router.delete("/{store_id}", dependencies=[Depends(auth.require_admin)])
def delete_store(store_id: int, db: Session = Depends(get_db)):
    obj = crud.delete_store(db, store_id)
    if not obj:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return {"ok": True}
