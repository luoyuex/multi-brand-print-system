from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import get_db

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("/", response_model=List[schemas.BrandOut])
def list_brands(db: Session = Depends(get_db)):
    return crud.get_brands(db)


@router.post("/", response_model=schemas.BrandOut, status_code=201)
def create_brand(brand: schemas.BrandCreate, db: Session = Depends(get_db)):
    return crud.create_brand(db, brand)
