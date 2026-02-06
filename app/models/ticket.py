"""
Modèles  pour la billetterie
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class TicketTypeBase(BaseModel):
    """Schéma de base pour un type de billet"""
    name: str = Field(..., min_length=1, max_length=100, description="Nom du type de billet")
    description: Optional[str] = Field(None, max_length=500, description="Description du billet")

class TicketTypeCreate(TicketTypeBase):
    """Schéma pour la création d'un type de billet"""
    event_id: str = Field(..., description="ID de l'événement associé")
    price: float = Field(..., ge=0, description="Prix du billet")
    quantity: int = Field(..., gt=0, description="Quantité disponible")
    max_per_person: int = Field(default=1, ge=1, description="Maximum par personne")

class TicketTypeUpdate(BaseModel):
    """Schéma pour la mise à jour d'un type de billet"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, gt=0)
    max_per_person: Optional[int] = Field(None, ge=1)

class TicketType(TicketTypeBase):
    """Schéma de sortie pour un type de billet"""
    id: str = Field(..., alias="_id")
    event_id: str
    price: float
    quantity: int
    max_per_person: int
    sold_count: int = Field(default=0, description="Nombre de billets vendus")
    available_count: int = Field(..., description="Nombre de billets disponibles")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def available_count(self) -> int:
        """Calculer le nombre de billets disponibles"""
        return max(0, self.quantity - self.sold_count)

class TicketPurchase(BaseModel):
    """Schéma pour l'achat d'un billet"""
    ticket_type_id: str = Field(..., description="ID du type de billet")
    buyer_info: dict = Field(..., description="Informations de l'acheteur")
    
    class BuyerInfo(BaseModel):
        """Informations de l'acheteur"""
        first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
        last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
        email: str = Field(..., description="Adresse email")
        address: Optional[str] = Field(None, max_length=500, description="Adresse complète")
        phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")

class TicketBase(BaseModel):
    """Schéma de base pour un billet"""
    ticket_number: str = Field(..., description="Numéro unique du billet")

class TicketCreate(TicketBase):
    """Schéma pour la création d'un billet"""
    ticket_type_id: str = Field(..., description="ID du type de billet")
    event_id: str = Field(..., description="ID de l'événement")
    buyer_id: str = Field(..., description="ID de l'acheteur")
    buyer_info: dict = Field(..., description="Informations de l'acheteur")

class Ticket(TicketBase):
    """Schéma de sortie pour un billet"""
    id: str = Field(..., alias="_id")
    ticket_type_id: str
    event_id: str
    buyer_id: str
    buyer_info: dict
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = Field(default=True)
    checked_in: bool = Field(default=False, description="Le billet a-t-il été utilisé ?")
    checked_in_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class TicketResponse(Ticket):
    """Réponse étendue avec détails supplémentaires"""
    ticket_type_details: Optional[TicketType] = None
    event_details: Optional[dict] = None
    buyer_details: Optional[dict] = None