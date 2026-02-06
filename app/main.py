"""
Point d'entrée principal de l'application FastAPI
Configuration des routes et middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from app.database import connect_to_mongo, close_mongo_connection
from app.routes import (
    auth, users, events, groups, discussions, 
    albums, polls, tickets, shopping, 
    # carpool
)

# Charger les variables d'environnement
load_dotenv()

# Créer l'application FastAPI
app = FastAPI(
    title="My Social Network API",
    description="API REST pour un réseau social avec gestion d'événements et groupes",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Événements de démarrage/arrêt
@app.on_event("startup")
async def startup_db_client():
    """Connexion à MongoDB au démarrage de l'application"""
    await connect_to_mongo()
    print("Connecté à MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Fermeture de la connexion MongoDB à l'arrêt"""
    await close_mongo_connection()
    print("Déconnecté de MongoDB")

# Inclure les routeurs
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentification"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Utilisateurs"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Événements"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groupes"])
app.include_router(discussions.router, prefix="/api/v1/discussions", tags=["Discussions"])
app.include_router(albums.router, prefix="/api/v1/albums", tags=["Albums photos"])
app.include_router(polls.router, prefix="/api/v1/polls", tags=["Sondages"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["Billetterie"])
app.include_router(shopping.router, prefix="/api/v1/shopping", tags=["Liste de courses (Bonus)"])
# app.include_router(carpool.router, prefix="/api/v1/carpool", tags=["Covoiturage (Bonus)"])

# Route racine
@app.get("/")
async def root():
    """Route racine de l'API"""
    return {
        "message": "Bienvenue sur My Social Network API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de santé de l'API"""
    from app.database import get_database
    db = get_database()
    return {
        "status": "healthy" if db else "unhealthy",
        "database": "connected" if db else "disconnected"
    }
    return {"status": "healthy", "database": "connected"}