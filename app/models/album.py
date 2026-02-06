"""
Modèles Pydantic pour les albums photos et photos
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class AlbumBase(BaseModel):
    """Schéma de base pour un album photo"""
    name: str = Field(..., min_length=1, max_length=200, description="Nom de l'album")
    description: Optional[str] = Field(None, max_length=1000, description="Description de l'album")

class AlbumCreate(AlbumBase):
    """Schéma pour la création d'un album """
    event_id: str = Field(..., description="ID de l'événement associé")

class AlbumUpdate(BaseModel):
    """Schéma pour la mise à jour d'un album"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class Album(AlbumBase):
    """Schéma de sortie pour un album photo"""
    id: str = Field(..., alias="_id")
    event_id: str
    creator_id: str = Field(..., description="ID du créateur de l'album")
    photo_count: int = Field(default=0, description="Nombre total de photos")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class PhotoBase(BaseModel):
    """Schéma de base pour une photo"""
    caption: Optional[str] = Field(None, max_length=500, description="Légende de la photo")
    image_url: str = Field(..., description="URL de l'image")

class PhotoCreate(PhotoBase):
    """Schéma pour la création d'une photo"""
    album_id: str = Field(..., description="ID de l'album parent")

class PhotoUpdate(BaseModel):
    """Schéma pour la mise à jour d'une photo"""
    caption: Optional[str] = Field(None, max_length=500)

class Photo(PhotoBase):
    """Schéma de sortie pour une photo"""
    id: str = Field(..., alias="_id")
    album_id: str
    event_id: str
    author_id: str = Field(..., description="ID de l'auteur de la photo")
    like_count: int = Field(default=0, description="Nombre de likes")
    comment_count: int = Field(default=0, description="Nombre de commentaires")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class CommentBase(BaseModel):
    """Schéma de base pour un commentaire"""
    content: str = Field(..., min_length=1, max_length=1000, description="Contenu du commentaire")

class CommentCreate(CommentBase):
    """Schéma pour la création d'un commentaire"""
    photo_id: str = Field(..., description="ID de la photo commentée")

class Comment(CommentBase):
    """Schéma de sortie pour un commentaire"""
    id: str = Field(..., alias="_id")
    photo_id: str
    author_id: str = Field(..., description="ID de l'auteur du commentaire")
    is_edited: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class AlbumResponse(Album):
    """Réponse étendue avec les dernières photos"""
    last_photos: Optional[List[Photo]] = None
    event_details: Optional[dict] = None