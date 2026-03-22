from pydantic import BaseModel, EmailStr


class SignUpDto(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str
