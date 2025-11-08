from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema for login response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict  # We'll include user info in response
