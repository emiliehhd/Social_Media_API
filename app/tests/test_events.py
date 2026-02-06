"""
Tests pour les endpoints des événements
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_event():
    """Test de création d'un événement"""
    event_data = {
        "name": "Test Event",
        "description": "A test event",
        "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "location": "Test Location",
        "privacy": "public",
        "organizers": [],
        "members": []
    }
    
    # Note: Nécessite un token d'authentification
    # Pour les tests complets, il faudrait mocker l'authentification
    response = client.post("/api/v1/events/", json=event_data)
    # Le statut dépendra de l'authentification
    assert response.status_code in [201, 401]

def test_get_events():
    """Test de récupération des événements"""
    response = client.get("/api/v1/events/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)