from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
class User(BaseModel):
    email: EmailStr


class UserCreate(BaseModel):
  fullname: str = Field(..., min_length=3, max_length=100)
  email:  Optional[EmailStr] = None
  phone_number: str = Field(..., pattern=r'^\+?\d{10,15}$')  # <- use pattern instead of regex
  password: Optional[str] = Field(default=None, min_length=8)
  guardian_email: Optional[EmailStr] = None  # optional field
  country: Optional[str] 

  # @field_validator("password")
  # def validate_password(cls, v):
  #   if not any(c.isdigit() for c in v):
  #     raise ValueError("Password must contain at least one digit")
  #   if not any(c.isupper() for c in v):
  #     raise ValueError("Password must contain at least one uppercase letter")
  #   return v
class LoginVerifyOTP(BaseModel):
  id: int
  phone_number: str
  code: str  
  
class UserLogin(BaseModel):
    phone_number: str 

    
class UserResponse(User):
    id: int
    role: str
    username: str
    status: str       # ← change from bool to str
    fullname: str | None = None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    access_token: str
    user: UserResponse


class OTPResponse(BaseModel):
  id: int
  expires_at: datetime


  class Config:
    from_attributes = True

class OTPCreateResponse(BaseModel):
    status: str
    otp: OTPResponse

    class Config:
      from_attributes = True


class RegisterVerifyOTP(BaseModel):
  id: int
  phone_number: str
  code: str


class LoginResponse(RegisterResponse):
    pass


class ResetPassword(BaseModel):
    token: str
    password: str
    password_confirmation: str
