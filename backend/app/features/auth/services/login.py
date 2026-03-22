from sqlalchemy.orm import Session
from app.features.auth.utils import validate_email, verify_password, generate_auth_token
from app.features.users.models.user import User
from app.features.auth.models.refresh_token import RefreshToken
from app.features.auth.dto.login_dto import LoginDto
from app.core.errors.error_with_code import ErrorWithCode
from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
REFRESH_SECRET = os.getenv("REFRESH_SECRET")


def login_service(db: Session, data: LoginDto, device_id: str):
    if not validate_email(data.email):
        raise ErrorWithCode("Invalid email format", 400)

    existing_user = db.query(User).filter(User.email == data.email).first()
    if not existing_user:
        raise ErrorWithCode("User with this email doesn't exist", 404)
    if not verify_password(data.password, existing_user.password):
        raise ErrorWithCode("Invalid password", 400)

    access_token = generate_auth_token(
        existing_user.id, secret_key=ACCESS_SECRET, expiration_minutes=10
    )
    refresh_token = generate_auth_token(
        existing_user.id, secret_key=REFRESH_SECRET, expiration_minutes=60 * 24 * 365
    )

    try:
        insert_refresh_token(refresh_token, existing_user.id, device_id, db)
        db.commit()
        return access_token, refresh_token, existing_user.id

    except Exception as e:
        db.rollback()
        raise e


def insert_refresh_token(
    refresh_token: str, user_id: int, device_id: str, executor: Session
):
    if not refresh_token or not user_id:
        raise ErrorWithCode("Refresh token and user ID must be provided", 400)

    existing_token_entry = (
        executor.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.device_id == device_id)
        .first()
    )

    if existing_token_entry:
        existing_token_entry.token = refresh_token
    else:
        new_refresh_token = RefreshToken(
            token=refresh_token, user_id=user_id, device_id=device_id
        )
        executor.add(new_refresh_token)
