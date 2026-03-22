from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.features.auth.services.jwt_auth_guard import jwt_auth_guard
from sqlalchemy.orm import Session
from app.core.database.index import get_db
from app.features.users.services.get_user_by_id import get_user_by_id_service
from app.core.errors.error_with_code import ErrorWithCode

users = APIRouter(prefix="/api/users", tags=["Users"])


@users.get("/info/{user_id}")
async def get_user_info(
    user_id: str = None,
    auth_user_id: str = Depends(jwt_auth_guard),
    db: Session = Depends(get_db),
):
    target_id = user_id if user_id else auth_user_id

    try:
        current_user = get_user_by_id_service(db, target_id)

        return JSONResponse(
            status_code=200,
            content={
                "message": "User info retrieved successfully",
                "data": current_user.to_dict(),
            },
        )
    except Exception as e:
        return HTTPException(
            status_code=e.code if isinstance(e, ErrorWithCode) else 500,
            detail={"message": "An error occurred", "error": str(e)},
        )
