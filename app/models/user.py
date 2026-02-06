"""
Modèles pour les utilisateurs
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserBase(BaseModel):
    """Schéma de base pour un utilisateur"""
    username: str = Field(..., min_length=3, max_length=50, description="Nom d'utilisateur unique")
    email: EmailStr = Field(..., description="Adresse email")
    first_name: Optional[str] = Field(None, max_length=100, description="Prénom")
    last_name: Optional[str] = Field(None, max_length=100, description="Nom de famille")
    profile_picture: Optional[str] = Field(None, description="URL de la photo de profil")

class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur"""
    password: str = Field(..., min_length=8, max_length=72, description="Mot de passe (min 8 caractères, max 72)")

class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    profile_picture: Optional[str] = Field(None)
    password: Optional[str] = Field(None, min_length=8)

class UserInDB(UserBase):
    """Schéma pour un utilisateur stocké en base de données"""
    id: str = Field(..., alias="_id")
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    """Schéma de sortie pour un utilisateur (sans mot de passe)"""
    id: str = Field(..., alias="_id")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    """Schéma pour la connexion d'un utilisateur"""
    email: EmailStr
    password: str