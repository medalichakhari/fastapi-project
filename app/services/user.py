from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user CRUD operations"""

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get a user by username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, user_in: UserCreate) -> User:
        """
        Create a new user.

        Args:
            db: Database session
            user_in: User creation schema with plain password

        Returns:
            Created user object
        """
        # Hash the password
        hashed_password = get_password_hash(user_in.password)

        # Create user instance
        db_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_password,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
        )

        # Add to database
        db.add(db_user)
        db.commit()
        db.refresh(db_user)  # Refresh to get id and timestamps

        return db_user

    @staticmethod
    def update(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """
        Update a user.

        Args:
            db: Database session
            user_id: ID of user to update
            user_in: User update schema

        Returns:
            Updated user object or None if not found
        """
        from fastapi import HTTPException, status

        db_user = UserService.get_by_id(db, user_id)
        if not db_user:
            return None

        # Update fields that are provided
        update_data = user_in.model_dump(exclude_unset=True)

        # Check for duplicate email (if email is being updated)
        if "email" in update_data and update_data["email"] != db_user.email:
            existing_user = UserService.get_by_email(db, update_data["email"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Check for duplicate username (if username is being updated)
        if "username" in update_data and update_data["username"] != db_user.username:
            existing_user = UserService.get_by_username(db, update_data["username"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        # Hash password if provided
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        # Apply updates
        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)

        return db_user

    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            db: Database session
            user_id: ID of user to delete

        Returns:
            True if deleted, False if not found
        """
        db_user = UserService.get_by_id(db, user_id)
        if not db_user:
            return False

        db.delete(db_user)
        db.commit()

        return True

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Args:
            db: Database session
            email: User email
            password: Plain password

        Returns:
            User object if authenticated, None otherwise
        """
        user = UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
