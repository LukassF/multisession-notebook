from sqlalchemy.orm import Session
from app.features.auth.utils import validate_email, verify_password, generate_auth_token
from app.features.users.models.user import User
from app.features.auth.models.refresh_token import RefreshToken
from app.features.auth.dto.refresh_dto import RefreshDto
import jwt
from app.features.auth.utils import decode_auth_token

from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
REFRESH_SECRET = os.getenv("REFRESH_SECRET")
ALGORITHM = os.getenv("ALGORITHM")


def refresh_service(db: Session, data: RefreshDto):
    payload = decode_auth_token(
        data.refresh_token, secret_key=REFRESH_SECRET, algorithm=ALGORITHM
    )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise ValueError("Invalid refresh token")

    existing_refresh_token = find_refresh_token(
        db, user_id=int(user_id), refresh_token=data.refresh_token
    )
    if not existing_refresh_token:
        raise ValueError("Refresh token not found or does not match")

    access_token = generate_auth_token(
        int(user_id), secret_key=ACCESS_SECRET, expiration_minutes=10
    )

    db.commit()

    return access_token, int(user_id)


def find_refresh_token(db: Session, user_id: int, refresh_token: str):
    token_entry = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.token == refresh_token)
        .first()
    )
    return token_entry
