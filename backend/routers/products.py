from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import crud, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", response_model=List[schemas.ProductOut])
def list_products(
    brand_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_products(db, brand_id=brand_id, search=search)


@router.post("/", response_model=schemas.ProductOut, status_code=201,
             dependencies=[Depends(auth.require_admin)])
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)


@router.put("/{product_id}", response_model=schemas.ProductOut,
            dependencies=[Depends(auth.require_admin)])
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    obj = crud.update_product(db, product_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="商品不存在")
    return obj


@router.delete("/{product_id}", dependencies=[Depends(auth.require_admin)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    obj = crud.delete_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"ok": True}
