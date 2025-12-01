"""
Tests for /me endpoints (current user operations).

Tests protected endpoints where user can view/update/delete their own account.
"""

import pytest

from app.core.config import settings


class TestGetMe:
    """Test getting current user info (GET /me)"""

    def test_get_me_authenticated(self, client, auth_headers, test_user):
        """Test authenticated user can get their own info"""
        response = client.get(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["is_active"] is True
        assert "password" not in data
        assert "hashed_password" not in data

    def test_get_me_unauthenticated(self, client):
        """Test unauthenticated request fails"""
        response = client.get(f"{settings.API_V1_PREFIX}/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client):
        """Test request with invalid token fails"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(
            f"{settings.API_V1_PREFIX}/me",
            headers=headers,
        )
        assert response.status_code == 401


class TestUpdateMe:
    """Test updating current user (PUT /me)"""

    def test_update_me_email(self, client, auth_headers, test_user):
        """Test user can update their own email"""
        new_email = "newemail@example.com"
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
            json={"email": new_email},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == new_email
        assert data["id"] == test_user.id

    def test_update_me_username(self, client, auth_headers, test_user):
        """Test user can update their own username"""
        new_username = "newusername"
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
            json={"username": new_username},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == new_username
        assert data["id"] == test_user.id

    def test_update_me_password(self, client, auth_headers, test_user):
        """Test user can update their own password"""
        new_password = "NewPassword123!"
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
            json={"password": new_password},
        )
        assert response.status_code == 200

        # Verify can login with new password
        login_response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": new_password,
            },
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_update_me_multiple_fields(self, client, auth_headers, test_user):
        """Test user can update multiple fields at once"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
            json={
                "email": "multi@example.com",
                "username": "multiupdate",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "multi@example.com"
        assert data["username"] == "multiupdate"

    def test_update_me_duplicate_email(self, client, auth_headers, test_db):
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

        # Try to update to other user's email
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
            json={"email": other_user.email},
        )
        assert response.status_code == 400

    def test_update_me_unauthenticated(self, client):
        """Test unauthenticated update fails"""
        response = client.put(
            f"{settings.API_V1_PREFIX}/me",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 403


class TestDeleteMe:
    """Test deleting current user (DELETE /me)"""

    def test_delete_me_authenticated(self, client, auth_headers, test_user):
        """Test user can delete their own account"""
        response = client.delete(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify user is deleted
        get_response = client.get(f"{settings.API_V1_PREFIX}/users/{test_user.id}")
        assert get_response.status_code == 404

    def test_delete_me_then_cannot_login(self, client, test_user):
        """Test deleted user cannot login"""
        # First login to get token
        login_response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )
        auth_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

        # Delete account
        delete_response = client.delete(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Try to login again
        retry_login = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )
        assert retry_login.status_code == 401

    def test_delete_me_unauthenticated(self, client):
        """Test unauthenticated delete fails"""
        response = client.delete(f"{settings.API_V1_PREFIX}/me")
        assert response.status_code == 403

    def test_delete_me_invalid_token(self, client):
        """Test delete with invalid token fails"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.delete(
            f"{settings.API_V1_PREFIX}/me",
            headers=headers,
        )
        assert response.status_code == 401


class TestMeEndpointsSecurity:
    """Test security aspects of /me endpoints"""

    def test_user_cannot_access_other_user_data(self, client, test_db):
        """Test user can only access their own data through /me"""
        # Create two users
        from app.schemas.user import UserCreate
        from app.services.user import UserService

        user1 = UserService.create(
            db=test_db,
            user_in=UserCreate(
                email="user1@example.com",
                username="user1",
                password="Password123!",
            ),
        )
        user2 = UserService.create(
            db=test_db,
            user_in=UserCreate(
                email="user2@example.com",
                username="user2",
                password="Password123!",
            ),
        )

        # Login as user1
        login_response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": user1.email,
                "password": "Password123!",
            },
        )
        user1_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

        # Get /me should return user1's data
        me_response = client.get(
            f"{settings.API_V1_PREFIX}/me",
            headers=user1_headers,
        )
        assert me_response.status_code == 200
        assert me_response.json()["id"] == user1.id
        assert me_response.json()["email"] == user1.email

        # Not user2's data
        assert me_response.json()["id"] != user2.id

    def test_superuser_me_returns_own_data(self, client, superuser_headers, test_superuser):
        """Test superuser /me returns their own data, not all users"""
        response = client.get(
            f"{settings.API_V1_PREFIX}/me",
            headers=superuser_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_superuser.id
        assert data["email"] == test_superuser.email
        assert data["is_superuser"] is True

        # Should return single user object, not a list
        assert isinstance(data, dict)
