from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_superuser, get_current_user
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.schemas.user import UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/me", tags=["current-user"])


@router.get("/", response_model=UserSchema)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user information.

    Requires authentication.
    """
    return current_user


@router.put("/", response_model=UserSchema)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's own information.

    Users can only update their own profile.
    Requires authentication.
    """
    updated_user = UserService.update(db, current_user.id, user_update)
    return updated_user


@router.delete("/", status_code=204)
def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete current user's own account.

    Requires authentication.
    """
    UserService.delete(db, current_user.id)
    return None
