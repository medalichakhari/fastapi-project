"""
Tests for authentication endpoints.

Tests login, token refresh, registration, and error handling.
"""


from app.core.config import settings


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_user_success(self, client):
        """Test successful user registration"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewUser123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration fails with duplicate email"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": test_user.email,
                "username": "different_username",
                "password": "Password123!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client, test_user):
        """Test registration fails with duplicate username"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "Password123!",
            },
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration fails with invalid email format"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/users/",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "Password123!",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Test login endpoint"""

    def test_login_success(self, client, test_user):
        """Test successful login returns tokens and user data"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check token structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

        # Check user data
        assert "user" in data
        assert data["user"]["email"] == test_user.email
        assert data["user"]["username"] == test_user.username
        assert "password" not in data["user"]

    def test_login_wrong_password(self, client, test_user):
        """Test login fails with incorrect password"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login fails with non-existent user"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!",
            },
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_inactive_user(self, client, test_user, test_db):
        """Test login fails for inactive user"""
        # Deactivate user
        test_user.is_active = False
        test_db.commit()

        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Test token refresh endpoint"""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # First login to get refresh token
        login_response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new tokens
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """Test refresh fails with invalid token"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={"refresh_token": "invalid_token_12345"},
        )
        assert response.status_code == 401

    def test_refresh_token_missing(self, client):
        """Test refresh fails with missing token"""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={},
        )
        assert response.status_code == 422


class TestProtectedEndpoints:
    """Test authentication is required for protected endpoints"""

    def test_access_protected_without_token(self, client):
        """Test accessing protected endpoint without token fails"""
        response = client.get(f"{settings.API_V1_PREFIX}/me")
        assert response.status_code == 403

    def test_access_protected_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token fails"""
        headers = {"Authorization": "Bearer invalid_token_123"}
        response = client.get(f"{settings.API_V1_PREFIX}/me", headers=headers)
        assert response.status_code == 401

    def test_access_protected_with_valid_token(self, client, auth_headers, test_user):
        """Test accessing protected endpoint with valid token succeeds"""
        response = client.get(
            f"{settings.API_V1_PREFIX}/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
