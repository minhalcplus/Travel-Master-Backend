from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from markdown_it.rules_block import reference
from sqlalchemy import or_

from . import schemas, models, utils
from core.app.database import get_db
from sqlalchemy.orm import Session
from core.config.mails import send_welcome_mail, send_forgot_password_mail, send_signup_otp_mail
import secrets
from datetime import datetime, timezone, timedelta
from core.app.env import settings
from .schemas import LoginVerifyOTP
from fastapi import FastAPI
import os
app = FastAPI()
router = APIRouter()

@router.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "env": os.getenv("ENV", "unknown")
    }
async def registerotp(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Check if user already exists
    db_user = (
        db.query(models.User)
        .filter(
            or_(
                models.User.email == user.email,
                models.User.phone == user.phone_number
            )
        )
        .first()
    )
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")

    otp_code = utils.generate_otp_v2()
    expire_time = datetime.now(timezone.utc) + timedelta(seconds=40)

    # Check if OTP already exists for this phone number
    otp_record = (
        db.query(models.OTPRequest)
        .filter(models.OTPRequest.data["phone_number"].as_string() == user.phone_number)
        .first()
    )

    if otp_record:
        # Resend OTP → update only OTP-related fields
        otp_record.code = otp_code
        otp_record.expires_at = expire_time
    else:
        # Create new OTP request
        otp_record = models.OTPRequest(
            code=otp_code,
            expires_at=expire_time,
            data={
                "email": user.email,
                "password": user.password,
                "fullname": user.fullname,
                "phone_number": user.phone_number,
                "guardian_email": user.guardian_email,
                "country": user.country,
            },
        )
        db.add(otp_record)

    db.commit()
    db.refresh(otp_record)

    # Send OTP email in background
    background_tasks.add_task(
        send_signup_otp_mail,
        email_to=user.email,
        otp_code=otp_code,
        expiry_minutes=1,
    )

    return {
        "status": "success",
        "otp": schemas.OTPResponse.model_validate(otp_record),
    }

@router.post("/resend-otp/{id}")
async def resend_otp(
    id: int,    
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
  db_otp = db.query(models.OTPRequest).filter(models.OTPRequest.id == id).first()
  if not db_otp:
    raise HTTPException(status_code=400, detail="NO RECORD FOR THIS USER")
  
  otp_code = utils.generate_otp_v2()
  expire_time = datetime.now(timezone.utc) + timedelta(seconds=40)
  
  db_otp.code = otp_code
  db_otp.expires_at = expire_time
  db.commit()

  background_tasks.add_task(
    send_signup_otp_mail,
    email_to=db_otp.data["email"],
    otp_code=otp_code,
    expiry_minutes=1,
  )
  return {
        "status": "success",
        "otp": schemas.OTPResponse.model_validate(db_otp)
    
  }
@router.post("/register/verify-otp")
async def register_user(data: schemas.RegisterVerifyOTP, db: Session = Depends(get_db)):
  # Find OTP
  otp_record = db.query(models.OTPRequest).filter(models.OTPRequest.code == data.code, models.OTPRequest.id == data.id, models.OTPRequest.data["phone_number"].as_string() == data.phone_number).first()
  if not otp_record:
    raise HTTPException(status_code=400, detail="Invalid OTP")

  # Check expiry
  PKT = timezone(timedelta(hours=5))  # Pakistan timezone

  # Handle naive vs aware datetime
  expires_at = otp_record.expires_at
  # If naive, treat as PKT
  if expires_at.tzinfo is None:
    expires_at = expires_at.replace(tzinfo=PKT)

  # Convert to UTC for comparison
  expires_at_utc = expires_at.astimezone(timezone.utc)

  # Get current UTC time
  now_utc = datetime.now(timezone.utc)


  if expires_at_utc < now_utc:
    raise HTTPException(status_code=400, detail="OTP expired")

  user_data = otp_record.data
  email = otp_record.data["email"] or None
  phone_number = user_data.get("phone_number")

  # Check if user already exists
  if db.query(models.User).filter(models.User.phone == phone_number).first():
    raise HTTPException(status_code=400, detail="User already registered")

  
  fullname = user_data.get("fullname", "")
  first_name, last_name = (fullname.split(" ", 1) + [""])[:2]

  new_user = models.User(
    username=email,
    email=email,
    phone=phone_number,
    is_email_verified=True,
    is_phone_verified=True,
    status="active",
    role=models.Role.passenger
  )
  if user_data["password"]:
    password_hash = utils.get_password_hash(user_data["password"])
    new_user.password_hash = password_hash
  db.add(new_user)
  db.commit()
  db.refresh(new_user)

  profile = models.PassengerProfile(
    user_id=new_user.id,
    first_name=first_name,
    last_name=last_name,
    guardian_email=user_data.get("guardian_email"),
    country=user_data.get("country")
  )
  db.add(profile)
  db.commit()

  db.delete(otp_record)  # remove OTP after verification
  db.commit()

  access_token = utils.create_access_token({"user_id": new_user.id})

  return {
    "access_token": access_token,
    "user": new_user
  }

@router.post("/login", status_code=status.HTTP_200_OK)
async def login_request_otp(
    user: schemas.UserLogin,
    background_task: BackgroundTasks,
    db: Session = Depends(get_db)
):
    print("serere",user.phone_number)
    db_user = db.query(models.User).filter(models.User.phone == user.phone_number).first()
    print(db_user)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Credentials"
        )

    # Generate OTP
    otp_code = utils.generate_otp_v2()
    expire_time = datetime.now(timezone.utc) + timedelta(seconds=40)

    new_otp = models.OTPRequest(
        code=otp_code,
        expires_at=expire_time,
        data={"phone_number": user.phone_number,"email":db_user.email}  # store phone for later validation
    )

    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)

    # Send OTP via email/SMS (background task)
    background_task.add_task(
        send_signup_otp_mail,  # Or your SMS function
        email_to=db_user.email, 
        otp_code=otp_code,
        expiry_minutes=1
    )

    return {"status": "OTP sent successfully",
            "otp": schemas.OTPResponse.model_validate(new_otp),  # <-- added here
            }

@router.post("/login/verify-otp")
async def login_verify_otp(
    data: schemas.LoginVerifyOTP,
    db: Session = Depends(get_db)
):
    otp_record = db.query(models.OTPRequest).filter(
        models.OTPRequest.code == data.code
    ).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    PKT = timezone(timedelta(hours=5))  # Pakistan timezone
    # Handle naive vs aware datetime
    expires_at = otp_record.expires_at
    # If naive, treat as PKT
    if expires_at.tzinfo is None:
      expires_at = expires_at.replace(tzinfo=PKT)
    # Convert to UTC for comparison
    expires_at_utc = expires_at.astimezone(timezone.utc)
    # Get current UTC time
    now_utc = datetime.now(timezone.utc)
    if expires_at_utc < now_utc:
      raise HTTPException(status_code=400, detail="OTP expired")
    phone = otp_record.data.get("phone_number")  # <- get phone from JSON stored in OTP

    # OTP is valid, proceed to login / generate token
    db_user = db.query(models.User).filter(models.User.phone == phone).first()

    access_token = utils.create_access_token({"user_id": db_user.id})

    # Delete used OTP
    db.delete(otp_record)
    db.commit()

    return {"access_token": access_token, "user": schemas.UserResponse.model_validate(db_user)}


@router.post("/login/super-admin", status_code=status.HTTP_200_OK)
async def login_super_admin(
    user: schemas.SuperUserLogin,
    db: Session = Depends(get_db)
):
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Credentials"
        )

    # Verify password
    if not utils.verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Credentials"
        )

    # Check role
    allowed_roles = [models.Role.admin, models.Role.super_admin, models.Role.operator]
    if db_user.role not in allowed_roles: # Correct way to check enum
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized Access"
        )

    access_token = utils.create_access_token({"user_id": db_user.id})
    return {"access_token": access_token, "user": schemas.UserResponse.model_validate(db_user)}

@router.post('/forgot-password', status_code=status.HTTP_200_OK)
async def forgotPassword(
    user: schemas.User,
    backround_task: BackgroundTasks,
    db: Session = Depends(get_db)
):
    errors = {}
    db_user = db.query(models.User).filter(
        models.User.email == user.email,
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email Not Found",
        )
    reset_token = secrets.token_urlsafe(32)
    token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    existing_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.email == user.email
    ).first()

    if existing_token:
        existing_token.reset_token = reset_token
        existing_token.token_expires = token_expires
        existing_token.updated_at = datetime.now(timezone.utc)
    else:
        new_reset_token = models.PasswordResetToken(
            email=user.email,
            reset_token=reset_token,
            token_expires=token_expires
        )
        db.add(new_reset_token)
    db.commit()
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    backround_task.add_task(
        send_forgot_password_mail,
        email_to=user.email,
        reset_url=reset_url
    )
    return {"message": "Password Reset Link Send Successfully"}


@router.post('/reset-password', status_code=status.HTTP_200_OK)
async def forgotPassword(
    request: schemas.ResetPassword,
    db: Session = Depends(get_db)
):
    errors = {}
    token_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.reset_token == request.token
    ).first()
  
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid Or Expire Token",
        )
    current_time = datetime.now(timezone.utc)
    if token_record.token_expires.replace(tzinfo=timezone.utc) < current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has Expired"
        )
    user = db.query(models.User).filter(
        models.User.email == token_record.email
    ).first()
    
    if not user:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User Not Found"
      )
    hashed_password = utils.get_password_hash(request.password)
    user.password = hashed_password
    db.add(user)
    db.delete(token_record)
    
    db.commit()

    return {"message": "Password has been Updated"}


@router.get('/me', response_model=schemas.UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user(
    current_user: schemas.UserResponse = Depends(utils.loggedin_user)
):
    return current_user
