"""
Routeur pour la gestion de la liste de courses 
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_collection
from app.models.shopping_list import ShoppingItem, ShoppingItemCreate, ShoppingListResponse
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/events/{event_id}", response_model=ShoppingListResponse)
async def get_event_shopping_list(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste de courses d'un événement
    """
    # Vérifier que l'événement existe et que l'utilisateur y participe
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": event_id, "is_active": True})
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        if (current_user.id not in event.get("members", []) and 
            current_user.id not in event.get("organizers", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view shopping list for this event"
            )
    
    # Récupérer les items de la liste de courses
    shopping_collection = get_collection("shopping_items")
    if not shopping_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    items = await shopping_collection.find({"event_id": event_id}).to_list(length=100)
    
    # stats
    total_items = len(items)
    brought_items = sum(1 for item in items if item.get("is_brought", False))
    pending_items = total_items - brought_items
    
    return ShoppingListResponse(
        event_id=event_id,
        total_items=total_items,
        brought_items=brought_items,
        pending_items=pending_items,
        items=[ShoppingItem(**item) for item in items]
    )

@router.post("/", response_model=ShoppingItem, status_code=status.HTTP_201_CREATED)
async def create_shopping_item(
    item_data: ShoppingItemCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Ajouter un item à la liste de courses d'un événement
    """
    # Vérifie que l'événement existe et que l'utilisateur y participe
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": item_data.event_id, "is_active": True})
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        if (current_user.id not in event.get("members", []) and 
            current_user.id not in event.get("organizers", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add items to this event's shopping list"
            )
    
    # Vérifie quz l'item n'existe pas pour cet événement
    shopping_collection = get_collection("shopping_items")
    if shopping_collection:
        existing_item = await shopping_collection.find_one({
            "event_id": item_data.event_id,
            "name": item_data.name,
            "is_active": True
        })
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An item with this name already exists for this event"
            )
    
    # Créer l'item
    item_dict = item_data.model_dump()
    item_dict.update({
        "_id": f"shopping_{datetime.utcnow().timestamp()}",
        "user_id": current_user.id,
        "is_brought": False,
        "is_unique": True,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    if shopping_collection:
        await shopping_collection.insert_one(item_dict)
    
    return ShoppingItem(**item_dict)