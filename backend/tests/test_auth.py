"""
Тесты аутентификации
"""
import pytest


def test_register(client):
    """Тест регистрации пользователя"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data


def test_register_duplicate_email(client, test_user):
    """Тест регистрации с существующим email"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "anotherpassword",
            "full_name": "Another User"
        }
    )
    assert response.status_code == 400


def test_login(client, test_user):
    """Тест входа"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Тест входа с неверным паролем"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    """Тест получения текущего пользователя"""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_get_me_unauthorized(client):
    """Тест без авторизации"""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
