import random
import string

from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
from core.app.env import settings
from core.app.database import get_db
from jose import jwt, JWTError
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import HTTPBasicCredentials, HTTPBasic, HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from . import models
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

basic_auth = HTTPBasic(auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)
oauth = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(text_password, hashed_password) -> bool:
    return pwd_context.verify(text_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expire_delta: timedelta = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=settings.JWT_EXPIRES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encode_jwt


def verify_basic_auth(credentials: HTTPBasicCredentials, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
    user = db.query(models.User).filter(
        models.User.email == credentials.username).first()
    if not user:
        raise credentials_exception
    if not verify_password(credentials.password, user.password):
        raise credentials_exception
    return user


def verify_bearer_token(token: str, db: Session):
    token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token=token, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise token_exception
    except JWTError:
        raise token_exception
    user = db.query(models.User).filter(
        models.User.id == user_id).first()
    return user


def loggedin_user(
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_auth),
    token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_auth),
    db: Session = Depends(get_db)

) -> models.User:
    if token is not None:
        return verify_bearer_token(token=token.credentials, db=db)
    if credentials is not None:
        return verify_basic_auth(credentials=credentials, db=db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not Authenticated",
        headers={"WWW-Authenticate": "Bearer,Basic"},
    )

def generate_otp_v2():
  # Generate 6 random digits and shuffle
  digits = random.choices(string.digits, k=6)
  random.shuffle(digits)
  return ''.join(digits)