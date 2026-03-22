from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from dotenv import load_dotenv
import os
from app.features.auth.utils import decode_auth_token
from app.core.errors.error_with_code import ErrorWithCode

# for swagger documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


load_dotenv()
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
ALGORITHM = os.getenv("ALGORITHM")


async def jwt_auth_guard(token: str = Depends(oauth2_scheme)):
    credentials_exception = ErrorWithCode(
        "Could not validate credentials",
        status.HTTP_401_UNAUTHORIZED,
    )
    try:
        payload = decode_auth_token(
            token, secret_key=ACCESS_SECRET, algorithm=ALGORITHM
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        return user_id
    except ValueError or jwt.PyJWTError:
        raise credentials_exception
