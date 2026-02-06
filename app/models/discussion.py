"""
Modèles Pydantic pour les fils de discussion et messages
Conforme aux spécifications (lié à 1 groupe OU 1 événement)
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class DiscussionType(str, Enum):
    """Types de discussion"""
    GROUP = "group"
    EVENT = "event"

class DiscussionBase(BaseModel):
    """Schéma de base pour un fil de discussion"""
    title: str = Field(..., min_length=1, max_length=200, description="Titre de la discussion")
    description: Optional[str] = Field(None, max_length=1000, description="Description de la discussion")

class DiscussionCreate(DiscussionBase):
    """Schéma pour la création d'une discussion"""
    discussion_type: DiscussionType = Field(..., description="Type de discussion (group ou event)")
    linked_id: str = Field(..., description="ID du groupe ou événement lié")
    is_pinned: bool = Field(default=False, description="Épingler la discussion en haut")

class DiscussionUpdate(BaseModel):
    """Schéma pour la mise à jour d'une discussion"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_pinned: Optional[bool] = None

class Discussion(DiscussionBase):
    """Schéma de sortie pour d'unr discussion"""
    id: str = Field(..., alias="_id")
    discussion_type: DiscussionType
    linked_id: str
    creator_id: str = Field(..., description="ID du créateur de la discussion")
    is_pinned: bool
    is_active: bool = Field(default=True)
    message_count: int = Field(default=0, description="Nombre total de messages")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class MessageBase(BaseModel):
    """Schéma de base pour un message"""
    content: str = Field(..., min_length=1, max_length=5000, description="Contenu du message")

class MessageCreate(MessageBase):
    """Schéma pour la création d'un message"""
    discussion_id: str = Field(..., description="ID de la discussion parente")
    parent_message_id: Optional[str] = Field(None, description="ID du message parent (pour les réponses)")

class Message(MessageBase):
    """Schéma de sortie pour un message"""
    id: str = Field(..., alias="_id")
    discussion_id: str
    parent_message_id: Optional[str] = None
    author_id: str = Field(..., description="ID de l'auteur du message")
    is_edited: bool = Field(default=False, description="Le message a été modifié")
    reply_count: int = Field(default=0, description="Nombre de réponses à ce message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

#ICI
class DiscussionResponse(Discussion):
    """Réponse étendue avec les derniers messages"""
    last_messages: Optional[List[Message]] = None
    author_details: Optional[dict] = None