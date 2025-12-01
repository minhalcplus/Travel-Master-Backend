from core.app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, Text, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime


class Role(enum.Enum):
    admin = "admin"
    passenger = "passenger"
    drive = "driver"


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    fullname: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(20))  # active, inactive, banned
    role: Mapped[str] = mapped_column(Enum(Role), default=Role.passenger, nullable=False)  # passenger, driver, admin

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    DriverProfile: Mapped["DriverProfile"] = relationship("DriverProfile", back_populates="user", uselist=False)
    PassengerProfile: Mapped["PassengerProfile"] = relationship("PassengerProfile", back_populates="user", uselist=False)
    # driver: Mapped["Driver"] = relationship("Driver", back_populates="user", uselist=False)
    oauth_providers: Mapped[list["OAuthProvider"]] = relationship("OAuthProvider", back_populates="user")
    # bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="user")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    email = Column(String(255), primary_key=True, index=True)
    reset_token = Column(String(255), nullable=True)
    token_expires: datetime = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), nullable=True)

class DriverProfile(Base):
    __tablename__ = "DriverProfiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[Date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="DriverProfile")


class PassengerProfile(Base):
  __tablename__ = "PassengerProfiles"

  id: Mapped[int] = mapped_column(primary_key=True)

  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

  first_name: Mapped[str] = mapped_column(String(100))
  last_name: Mapped[str] = mapped_column(String(100))

  avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
  date_of_birth: Mapped[Date | None] = mapped_column(Date)
  gender: Mapped[str | None] = mapped_column(String(20))
  timezone: Mapped[str | None] = mapped_column(String(100))
  guardian_email: Mapped[str | None] = mapped_column(String(100))
  country: Mapped[str | None] = mapped_column(String(100))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

  user: Mapped["User"] = relationship("User", back_populates="PassengerProfile")
  
  
class OTPRequest(Base):
  __tablename__ = "otp_requests"

  id: Mapped[int] = mapped_column(primary_key=True)

  code: Mapped[str] = mapped_column(String(10))
  data: Mapped[dict] = mapped_column(JSON, nullable=False)

  expires_at: Mapped[datetime] = mapped_column(DateTime)

  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    provider: Mapped[str] = mapped_column(String(50))
    provider_user_id: Mapped[str] = mapped_column(String(255))

    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="oauth_providers")