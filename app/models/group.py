"""
Modèles pour les groupes
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class GroupType(str, Enum):
    """Types de groupe """
    PUBLIC = "public"
    PRIVATE = "private"
    SECRET = "secret"

class GroupBase(BaseModel):
    """Schéma de base pour un groupe"""
    name: str = Field(..., min_length=1, max_length=200, description="Nom du groupe")
    description: Optional[str] = Field(None, max_length=2000, description="Description du groupe")
    icon: Optional[str] = Field(None, description="URL de l'icône du groupe")
    cover_photo: Optional[str] = Field(None, description="URL de la photo de couverture")

class GroupCreate(GroupBase):
    """Schéma pour la création d'un groupe"""
    type: GroupType = Field(default=GroupType.PUBLIC, description="Type de groupe (public, privé, secret)")
    allow_member_posts: bool = Field(default=True, description="Autoriser les membres à publier")
    allow_member_events: bool = Field(default=True, description="Autoriser les membres à créer des événements")
    admin_ids: List[str] = Field(default_factory=list, description="Liste des IDs des administrateurs")

class GroupUpdate(BaseModel):
    """Schéma pour la mise à jour d'un groupe"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = None
    cover_photo: Optional[str] = None
    type: Optional[GroupType] = None
    allow_member_posts: Optional[bool] = None
    allow_member_events: Optional[bool] = None

class Group(GroupBase):
    """Schéma de sortie pour un groupe"""
    id: str = Field(..., alias="_id")
    type: GroupType
    allow_member_posts: bool
    allow_member_events: bool
    admin_ids: List[str]
    member_ids: List[str] = Field(default_factory=list, description="Liste des IDs des membres")
    creator_id: str = Field(..., description="ID du créateur du groupe")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class GroupResponse(Group):
    """Réponse étendue avec détails supplémentaires"""
    admin_details: Optional[List[dict]] = None
    member_details: Optional[List[dict]] = None
    member_count: int = Field(default=0, description="Nombre total de membres")
    event_count: int = Field(default=0, description="Nombre d'événements dans le groupe")