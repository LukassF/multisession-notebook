from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.features.auth.dto.signup_dto import SignUpDto
from app.features.auth.dto.login_dto import LoginDto
from app.features.auth.dto.refresh_dto import RefreshDto
from app.core.database.index import get_db
from app.features.auth.services.signup import signup_service
from app.features.auth.services.login import login_service
from app.features.auth.services.refresh import refresh_service


auth = APIRouter(prefix="/auth", tags=["Notebook Sessions"])


@auth.post("/signup")
async def signup(
    data: SignUpDto,
    db: Session = Depends(get_db),
):
    try:
        new_user = signup_service(db, data)
        return {"message": "Sign up successful", "data": {"user_id": new_user.id}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth.post("/login")
async def login(
    data: LoginDto,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        # we should probably use a unique device id from the frontend, but for simplicity, we'll use the user-agent header as a proxy for the device
        device_id = request.headers.get("user-agent")
        access_token, refresh_token, user_id = login_service(
            db, data, device_id=device_id
        )
        return {
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_id": user_id,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth.post("/refresh")
async def refresh(
    data: RefreshDto,
    db: Session = Depends(get_db),
):
    try:
        access_token, user_id = refresh_service(db, data)
        return {
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "user_id": user_id,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
