"""
Modèles pour les événements
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class EventPrivacy(str, Enum):
    """Types de confidentialité pour un événement"""
    PUBLIC = "public"
    PRIVATE = "private"

class EventConfig(BaseModel):
    """
    Première étape : Configuration de l'événement
    Conforme aux spécifications Facebook
    """
    name: str = Field(..., min_length=1, max_length=200, description="Nom de l'événement")
    description: Optional[str] = Field(None, max_length=2000, description="Description de l'événement")
    start_date: datetime = Field(..., description="Date et heure de début")
    end_date: datetime = Field(..., description="Date et heure de fin")
    location: str = Field(..., min_length=1, max_length=500, description="Lieu de l'événement")
    cover_photo: Optional[str] = Field(None, description="URL de la photo de couverture")
    privacy: EventPrivacy = Field(default=EventPrivacy.PUBLIC, description="Visibilité de l'événement")
    organizers: List[str] = Field(default_factory=list, description="Liste des IDs des organisateurs")
    members: List[str] = Field(default_factory=list, description="Liste des IDs des membres invités")

class EventCreate(EventConfig):
    """Schéma pour la création complète d'un événement"""
    group_id: Optional[str] = Field(None, description="ID du groupe associé (optionnel)")
    auto_invite: bool = Field(default=False, description="Inviter automatiquement les membres du groupe")

class EventUpdate(BaseModel):
    """Schéma pour la mise à jour d'un événement"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    cover_photo: Optional[str] = None
    privacy: Optional[EventPrivacy] = None
    organizers: Optional[List[str]] = None
    members: Optional[List[str]] = None

class Event(EventConfig):
    """Schéma de sortie pour un événement"""
    id: str = Field(..., alias="_id")
    group_id: Optional[str] = None
    creator_id: str = Field(..., description="ID de l'utilisateur qui a créé l'événement")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class EventResponse(Event):
    """Réponse étendue avec détails supplémentaires"""
    organizer_details: Optional[List[dict]] = None
    member_details: Optional[List[dict]] = None
    participant_count: int = Field(default=0, description="Nombre total de participants")