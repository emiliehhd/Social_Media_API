"""
Routeur pour la gestion de la billetterie
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_collection
from app.models.ticket import TicketType, TicketTypeCreate, Ticket, TicketPurchase
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/types/events/{event_id}", response_model=List[TicketType])
async def get_event_ticket_types(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer tous les types de billets d'un événement
    """
    ticket_types_collection = get_collection("ticket_types")
    if not ticket_types_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    ticket_types = await ticket_types_collection.find({"event_id": event_id, "is_active": True}).to_list(length=100)
    return [TicketType(**tt) for tt in ticket_types]

@router.post("/types", response_model=TicketType, status_code=status.HTTP_201_CREATED)
async def create_ticket_type(
    ticket_type_data: TicketTypeCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouveau type de billet pour un événement
    """
    # Vérifier que l'événement existe
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": ticket_type_data.event_id, "is_active": True})
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        # Vérifier que l'utilisateur est organisateur de l'événement
        if current_user.id not in event.get("organizers", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only event organizers can create ticket types"
            )
    
    # Créer le type de billet
    ticket_type_dict = ticket_type_data.model_dump()
    ticket_type_dict.update({
        "_id": f"ticket_type_{datetime.utcnow().timestamp()}",
        "sold_count": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    ticket_types_collection = get_collection("ticket_types")
    if ticket_types_collection:
        await ticket_types_collection.insert_one(ticket_type_dict)
    
    return TicketType(**ticket_type_dict)

@router.post("/purchase", response_model=Ticket)
async def purchase_ticket(
    purchase_data: TicketPurchase,
    current_user: User = Depends(get_current_user)
):
    """
    Acheter un billet pour un événement
    Vérifie la disponibilité et les limites par personne
    """
    ticket_types_collection = get_collection("ticket_types")
    if not ticket_types_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le type de billet existe et est disponible
    ticket_type = await ticket_types_collection.find_one({
        "_id": purchase_data.ticket_type_id,
        "is_active": True
    })
    
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found"
        )
    
    # Vérifier la disponibilité
    available = ticket_type.get("quantity", 0) - ticket_type.get("sold_count", 0)
    if available <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tickets available for this type"
        )
    
    # Vérifier la limite par personne
    max_per_person = ticket_type.get("max_per_person", 1)
    tickets_collection = get_collection("tickets")
    if tickets_collection:
        user_tickets_count = await tickets_collection.count_documents({
            "ticket_type_id": purchase_data.ticket_type_id,
            "buyer_id": current_user.id,
            "is_valid": True
        })
        
        if user_tickets_count >= max_per_person:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_per_person} ticket(s) per person reached"
            )
    
    # Créer le billet
    ticket_dict = {
        "_id": f"ticket_{datetime.utcnow().timestamp()}_{current_user.id}",
        "ticket_type_id": purchase_data.ticket_type_id,
        "event_id": ticket_type["event_id"],
        "buyer_id": current_user.id,
        "buyer_info": purchase_data.buyer_info,
        "ticket_number": f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{current_user.id[-6:]}",
        "purchase_date": datetime.utcnow(),
        "is_valid": True,
        "checked_in": False,
        "checked_in_at": None
    }
    
    if tickets_collection:
        await tickets_collection.insert_one(ticket_dict)
    
    # Incrémenter le compteur de billets vendus
    await ticket_types_collection.update_one(
        {"_id": purchase_data.ticket_type_id},
        {"$inc": {"sold_count": 1}}
    )
    
    return Ticket(**ticket_dict)

@router.get("/user/{user_id}", response_model=List[Ticket])
async def get_user_tickets(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer tous les billets d'un utilisateur
    """
    tickets_collection = get_collection("tickets")
    if not tickets_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifie que l'utilisateur correspond a ses  billets ou  admin
    if current_user.id != user_id:
        # Ici, on pourrait vérifier les permissions d'administrateur
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view other users' tickets"
        )
    
    tickets = await tickets_collection.find({"buyer_id": user_id, "is_valid": True}).to_list(length=100)
    return [Ticket(**ticket) for ticket in tickets]