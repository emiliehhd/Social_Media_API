"""
Modèles  pour la liste de courses 
"""

from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ShoppingItemBase(BaseModel):
    """Schéma de base pour un item de la liste de courses"""
    name: str = Field(..., min_length=1, max_length=200, description="Nom de l'item")
    quantity: int = Field(..., gt=0, description="Quantité à apporter")
    unit: Optional[str] = Field(None, max_length=50, description="Unité de mesure (ex: kg, L, pièces)")

class ShoppingItemCreate(ShoppingItemBase):
    """Schéma pour la création d'un item de la liste de courses"""
    event_id: str = Field(..., description="ID de l'événement associé")
    arrival_time: Optional[time] = Field(None, description="Heure d'arrivée à l'événement")
    notes: Optional[str] = Field(None, max_length=500, description="Notes supplémentaires")

class ShoppingItemUpdate(BaseModel):
    """Schéma pour la mise à jour d'un item"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    arrival_time: Optional[time] = None
    notes: Optional[str] = Field(None, max_length=500)
    is_brought: Optional[bool] = Field(None, description="L'item a-t-il été apporté ?")

class ShoppingItem(ShoppingItemBase):
    """Schéma de sortie pour un item de la liste de courses"""
    id: str = Field(..., alias="_id")
    event_id: str
    user_id: str = Field(..., description="ID de l'utilisateur qui apporte l'item")
    arrival_time: Optional[time]
    notes: Optional[str]
    is_brought: bool = Field(default=False, description="L'item a-t-il été apporté ?")
    is_unique: bool = Field(default=True, description="Cet item est-il unique pour l'événement ?")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class ShoppingListResponse(BaseModel):
    """Réponse pour la liste de courses complète d'un événement"""
    event_id: str
    total_items: int = Field(default=0, description="Nombre total d'items")
    brought_items: int = Field(default=0, description="Nombre d'items apportés")
    pending_items: int = Field(default=0, description="Nombre d'items en attente")
    items: list[ShoppingItem] = Field(default_factory=list, description="Liste des items")
    event_details: Optional[dict] = None