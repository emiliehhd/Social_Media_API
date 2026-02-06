"""
Tests pour les endpoints des utilisateurs
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    """Test de création d'un utilisateur"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data

def test_duplicate_email():
    """Test d'email dupliqué"""
    user_data = {
        "username": "testuser2",
        "email": "test@example.com",  # Même email
        "password": "testpassword123",
        "first_name": "Test2",
        "last_name": "User2"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 400

def test_get_user():
    """Test de récupération d'un utilisateur"""
    # D'abord créer un utilisateur
    user_data = {
        "username": "gettestuser",
        "email": "gettest@example.com",
        "password": "testpassword123"
    }
    
    create_response = client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # Ensuite le récupérer
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == user_data["username"]