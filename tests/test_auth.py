"""
Authentication endpoint tests.
Tests signup, login, token refresh, and logout functionality.
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_signup_success(self, client: TestClient):
        """Test successful user signup."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123"
        })
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "message" in data
        assert "user_id" in data
    
    def test_signup_duplicate_email(self, client: TestClient):
        """Test that duplicate email signup fails."""
        # First signup
        client.post("/auth/signup", json={
            "email": "duplicate@example.com",
            "username": "duplicate1",
            "password": "password123"
        })
        
        # Duplicate signup
        response = client.post("/api/v1/auth/signup", json={
            "email": "duplicate@example.com",
            "username": "duplicate2",
            "password": "differentpassword"
        })
        
        assert response.status_code == 409  # Conflict for duplicate
    
    def test_signup_invalid_email(self, client: TestClient):
        """Test signup with invalid email format."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "notanemail",
            "username": "invalid",
            "password": "password123"
        })
        
        # Email validation is handled by Pydantic EmailStr
        assert response.status_code == 422  # Validation error
    
    def test_signup_weak_password(self, client: TestClient):
        """Test signup with weak password."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "user@example.com",
            "username": "weakpass",
            "password": "123"  # Too short (< 6 chars)
        })
        
        # Should reject weak password
        assert response.status_code == 400
    
    def test_login_success(self, client: TestClient):
        """Test successful login."""
        # First create user
        client.post("/auth/signup", json={
            "email": "loginuser@example.com",
            "username": "loginuser",
            "password": "loginpassword123"
        })
        
        # Login
        response = client.post("/api/v1/auth/login", json={
            "email": "loginuser@example.com",
            "password": "loginpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_login_wrong_password(self, client: TestClient):
        """Test login with correct email but wrong password."""
        # Create user
        client.post("/auth/signup", json={
            "email": "wrongpass@example.com",
            "username": "wrongpass",
            "password": "correctpassword"
        })
        
        # Login with wrong password
        response = client.post("/api/v1/auth/login", json={
            "email": "wrongpass@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_refresh_token_success(self, client: TestClient):
        """Test successful token refresh."""
        # Create user and login
        client.post("/auth/signup", json={
            "email": "refreshuser@example.com",
            "username": "refreshuser",
            "password": "refreshpassword123"
        })
        
        login_response = client.post("/auth/login", json={
            "email": "refreshuser@example.com",
            "password": "refreshpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_token_string"
        })
        
        assert response.status_code == 401
    
    def test_me_authenticated(self, client: TestClient, auth_headers: dict):
        """Test getting current user info with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "id" in data
    
    def test_me_unauthenticated(self, client: TestClient):
        """Test getting current user info without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout."""
        response = client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code in [200, 201]
        
        # Token should now be invalid
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 401
    
    def test_rate_limiting_login(self, client: TestClient):
        """Test that login endpoint is rate-limited."""
        # Attempt multiple failed logins
        for i in range(6):  # Exceed the 5 req/min limit
            response = client.post("/api/v1/auth/login", json={
                "email": f"ratelimit{i}@example.com",
                "password": "wrongpassword"
            })
        
        # Should be rate-limited
        assert response.status_code == 429