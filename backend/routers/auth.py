from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import crud, schemas, models, auth
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── 登录 / 当前用户 ──────────────────────────────────────
@router.post("/login", response_model=schemas.LoginOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, data.username)
    if not user or not auth.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return {"token": auth.create_token(user), "user": user}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(auth.get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    data: schemas.ChangePasswordIn,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if not data.new_password.strip():
        raise HTTPException(status_code=400, detail="新密码不能为空")
    crud.change_password(db, user, data.new_password)
    return {"ok": True}


# ── 账号管理（仅管理员）─────────────────────────────────
@router.get("/users", response_model=List[schemas.UserOut])
def list_users(admin: models.User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    return crud.get_users(db)


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(
    data: schemas.UserCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if data.role not in ("admin", "staff"):
        raise HTTPException(status_code=400, detail="角色只能是 admin 或 staff")
    if crud.get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    return crud.create_user(db, data)


@router.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if data.role is not None and data.role not in ("admin", "staff"):
        raise HTTPException(status_code=400, detail="角色只能是 admin 或 staff")
    # 防止把最后一个启用的管理员降级/停用，导致无人能管理
    target = crud.get_user(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")
    demoting = (data.role is not None and data.role != "admin") or data.is_active is False
    if target.role == "admin" and demoting:
        active_admins = [u for u in crud.get_users(db) if u.role == "admin" and u.is_active]
        if len(active_admins) <= 1:
            raise HTTPException(status_code=400, detail="至少需保留一个启用的管理员")
    obj = crud.update_user(db, user_id, data)
    return obj


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的账号")
    target = crud.get_user(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")
    if target.role == "admin":
        active_admins = [u for u in crud.get_users(db) if u.role == "admin" and u.is_active]
        if len(active_admins) <= 1:
            raise HTTPException(status_code=400, detail="至少需保留一个启用的管理员")
    crud.delete_user(db, user_id)
    return {"ok": True}
