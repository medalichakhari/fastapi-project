from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    is_active: bool = True
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8, max_length=100)


# Properties to receive via API on update
class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)"""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    """Schema with database fields"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows reading data from SQLAlchemy models


# Properties to return via API
class User(UserInDBBase):
    """Schema for returning user data to client"""

    pass


# Properties stored in DB (includes hashed password)
class UserInDB(UserInDBBase):
    """Schema representing user in database"""

    hashed_password: str
