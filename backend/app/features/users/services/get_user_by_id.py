from sqlalchemy.orm import Session
from app.features.users.models.user import User


def get_user_by_id_service(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    return user
