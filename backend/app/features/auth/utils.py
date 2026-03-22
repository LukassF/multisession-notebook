from passlib.context import CryptContext
import jwt
from datetime import timedelta, timezone, datetime
from dotenv import load_dotenv
import os

load_dotenv()
ALGORITHM = os.getenv("ALGORITHM")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def validate_email(email: str) -> bool:
    return "@" in email and "." in email


def generate_auth_token(
    user_id: int,
    secret_key: str,
    algorithm: str = ALGORITHM or "HS256",
    expiration_minutes=10,
) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes),
    }
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token


def decode_auth_token(token: str, secret_key: str, algorithm: str = None):
    algo = algorithm or ALGORITHM or "HS256"
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algo])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
