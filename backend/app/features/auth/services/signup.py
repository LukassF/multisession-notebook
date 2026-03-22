from sqlalchemy.orm import Session
from app.features.auth.utils import hash_password, validate_email
from app.features.users.models.user import User
from app.features.auth.dto.signup_dto import SignUpDto


def signup_service(db: Session, data: SignUpDto):
    if not validate_email(data.email):
        raise ValueError("Invalid email format")

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise ValueError("User with this email already exists")

    hashed_pwd = hash_password(data.password)
    new_user = User(
        firstname=data.firstname,
        lastname=data.lastname,
        email=data.email,
        password=hashed_pwd,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise e
