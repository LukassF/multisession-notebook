from sqlalchemy.orm import Session
from app.features.users.models.user import User
from app.core.errors.error_with_code import ErrorWithCode


def get_user_by_id_service(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ErrorWithCode("User not found", 404)
    return user
