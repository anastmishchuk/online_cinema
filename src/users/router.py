from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from config.database import get_db
from src.users.auth.schema import UserCreateSchema, ActivationRequestSchema
from src.users.auth.service import get_user_by_email, create_user, activate_user, regenerate_activation_token
from src.users.models import User
from src.users.permissions import is_admin
from src.users.schemas import RoleChangeSchema, UserReadSchema
from src.users.service import send_activation_email

router = APIRouter()


@router.post("/register", response_model=UserReadSchema)
def register(user_create: UserCreateSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_create.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = create_user(db, user_create)
    send_activation_email(new_user.email, new_user.activation_token.token)
    return new_user


@router.get("/activate")
def activate(token: str = Query(...), db: Session = Depends(get_db)):
    user = activate_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired activation token")
    return {"message": "User activated successfully"}


@router.post("/resend-activation", status_code=200)
def resend_activation(request: ActivationRequestSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already activated")

    new_token = regenerate_activation_token(db, user)
    send_activation_email(user.email, new_token.token)
    return {"message": "Activation email resent successfully"}


@router.post("/change-role/{user_id}")
def change_user_role(
    user_id: int,
    role_data: RoleChangeSchema,
    db: Session = Depends(get_db),
    user=Depends(is_admin)
):
    target_user = db.query(User).filter_by(id=user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    target_user.group = role_data.new_role
    db.commit()
    return {"message": f"User role changed to {role_data.new_role}"}


@router.post("/activate/{user_id}")
def activate_user_account(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(is_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"message": "User account is already active"}

    user.is_active = True
    db.commit()
    return {"message": f"User {user.email} activated successfully"}
