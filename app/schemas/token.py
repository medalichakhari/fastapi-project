from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Schema for access token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for JWT token payload"""

    sub: Optional[str] = None  # Subject (user ID)
    exp: Optional[int] = None  # Expiration time


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""

    refresh_token: str
