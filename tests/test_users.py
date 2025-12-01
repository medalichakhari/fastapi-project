"""
Tests for user management endpoints.

Tests CRUD operations, admin-only protection, and validation.
"""

import pytest

from app.core.config import settings


class TestCreateUser:
    """Test user creation endpoint (POST /users/)"""

    def test_create_user_minimal(self, client):
        """Test creating user with minimal required fields"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": "minimal@example.com",
                "username": "minimaluser",
                "password": "Minimal123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "minimal@example.com"
        assert data["username"] == "minimaluser"
        assert data["is_active"] is True
        assert data["is_superuser"] is False

    def test_create_user_missing_required_fields(self, client):
        """Test creating user without required fields fails"""
        # Missing password
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": "test@example.com",
                "username": "testuser",
            },
        )
        assert response.status_code == 422

        # Missing email
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "username": "testuser",
                "password": "Password123!",
            },
        )
        assert response.status_code == 422


class TestListUsers:
    """Test listing users endpoint (GET /users/)"""

    def test_list_users_as_admin(self, client, superuser_headers, test_user, test_superuser):
        """Test listing users as superuser"""
        response = client.get(
            f"{settings.API_V1_PREFIX}/users/",
            headers=superuser_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least test_user and test_superuser

        # Check structure
        assert all("email" in user for user in data)
        assert all("username" in user for user in data)
        assert all("password" not in user for user in data)

    def test_list_users_as_regular_user(self, client, auth_headers):
        """Test listing users as regular user fails (admin only)"""
        response = client.get(
            f"{settings.API_V1_PREFIX}/users/",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_list_users_without_auth(self, client):
        """Test listing users without authentication fails"""
        response = client.get(f"{settings.API_V1_PREFIX}/users/")
        assert response.status_code == 403

    def test_list_users_pagination(self, client, superuser_headers, test_db):
        """Test pagination parameters work"""
        # Create multiple users for pagination test
        from app.schemas.user import UserCreate
        from app.services.user import UserService

        for i in range(5):
            UserService.create(
                db=test_db,
                user_in=UserCreate(
                    email=f"user{i}@example.com",
                    username=f"user{i}",
                    password="Password123!",
                ),
            )

        # Test with limit
        response = client.get(
            f"{settings.API_V1_PREFIX}/users/?limit=3",
            headers=superuser_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

        # Test with skip
        response = client.get(
            f"{settings.API_V1_PREFIX}/users/?skip=2&limit=3",
            headers=superuser_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 3


class TestGetUser:
    """Test getting single user endpoint (GET /users/{id})"""

    def test_get_existing_user(self, client, test_user):
        """Test getting an existing user by ID"""
        response = client.get(f"{settings.API_V1_PREFIX}/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_get_nonexistent_user(self, client):
        """Test getting non-existent user returns 404"""
        response = client.get(f"{settings.API_V1_PREFIX}/users/99999")
        assert response.status_code == 404

    def test_get_user_invalid_id(self, client):
        """Test getting user with invalid ID format"""
        response = client.get(f"{settings.API_V1_PREFIX}/users/invalid")
        assert response.status_code == 422


class TestUpdateUser:
    """Test updating user endpoint (PUT /users/{id})"""

    def test_update_user_email(self, client, test_user):
        """Test updating user email"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            json={"email": "newemail@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"
        assert data["username"] == test_user.username  # Unchanged

    def test_update_user_username(self, client, test_user):
        """Test updating username"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            json={"username": "newusername"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newusername"

    def test_update_user_password(self, client, test_user):
        """Test updating password"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            json={"password": "NewPassword123!"},
        )
        assert response.status_code == 200

        # Verify can login with new password
        login_response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "NewPassword123!",
            },
        )
        assert login_response.status_code == 200

    def test_update_nonexistent_user(self, client):
        """Test updating non-existent user returns 404"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/users/99999",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 404

    def test_update_user_duplicate_email(self, client, test_user, test_db):
        """Test updating to duplicate email fails"""
        # Create another user
        from app.schemas.user import UserCreate
        from app.services.user import UserService

        other_user = UserService.create(
            db=test_db,
            user_in=UserCreate(
                email="other@example.com",
                username="otheruser",
                password="Password123!",
            ),
        )

        # Try to update test_user with other_user's email
        response = client.put(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            json={"email": other_user.email},
        )
        assert response.status_code == 400


class TestDeleteUser:
    """Test deleting user endpoint (DELETE /users/{id})"""

    def test_delete_user_as_admin(self, client, superuser_headers, test_user):
        """Test deleting user as superuser"""
        response = client.delete(
            f"{settings.API_V1_PREFIX}/users/{test_user.id}",
            headers=superuser_headers,
        )
        assert response.status_code == 204

        # Verify user is deleted
        get_response = client.get(f"{settings.API_V1_PREFIX}/users/{test_user.id}")
        assert get_response.status_code == 404

    def test_delete_user_as_regular_user(self, client, auth_headers, test_db):
        """Test deleting user as regular user fails (admin only)"""
        # Create another user to delete
        from app.schemas.user import UserCreate
        from app.services.user import UserService

        other_user = UserService.create(
            db=test_db,
            user_in=UserCreate(
                email="other@example.com",
                username="otheruser",
                password="Password123!",
            ),
        )

        response = client.delete(
            f"{settings.API_V1_PREFIX}/users/{other_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_delete_user_without_auth(self, client, test_user):
        """Test deleting user without authentication fails"""
        response = client.delete(f"{settings.API_V1_PREFIX}/users/{test_user.id}")
        assert response.status_code == 403

    def test_delete_nonexistent_user(self, client, superuser_headers):
        """Test deleting non-existent user returns 404"""
        response = client.delete(
            f"{settings.API_V1_PREFIX}/users/99999",
            headers=superuser_headers,
        )
        assert response.status_code == 404
