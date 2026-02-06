"""
Fonctions de validation des données
"""

from fastapi import HTTPException, status
from app.database import get_collection

async def validate_email_unique(email: str, exclude_user_id: str = None):
    """
    Valider qu'un email est unique dans la base de données
    """
    users_collection = get_collection("users")
    if users_collection is not None:
        query = {"email": email, "is_active": True}
        if exclude_user_id:
            query["_id"] = {"$ne": exclude_user_id}
        
        existing_user = await users_collection.find_one(query)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

async def validate_user_exists(user_id: str):
    """
    Valider qu'un utilisateur existe dans la base de données
    """
    users_collection = get_collection("users")
    if users_collection is not None:
        user = await users_collection.find_one({"_id": user_id, "is_active": True})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

async def validate_discussion_access(discussion: dict, user_id: str):
    """
    Valider qu'un utilisateur a accès à une discussion
    """
    discussion_type = discussion.get("discussion_type")
    linked_id = discussion.get("linked_id")
    
    if discussion_type == "group":
        groups_collection = get_collection("groups")
        if groups_collection:
            group = await groups_collection.find_one({"_id": linked_id, "is_active": True})
            if group:
                group_type = group.get("type", "public")
                if group_type == "secret":
                    if (user_id not in group.get("member_ids", []) and 
                        user_id not in group.get("admin_ids", [])):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access this discussion"
                        )
    elif discussion_type == "event":
        events_collection = get_collection("events")
        if events_collection:
            event = await events_collection.find_one({"_id": linked_id, "is_active": True})
            if event:
                if event.get("privacy") == "private":
                    if (user_id not in event.get("members", []) and 
                        user_id not in event.get("organizers", [])):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access this discussion"
                        )

def validate_event_dates(start_date, end_date):
    """
    Valider que les dates d'un événement sont valides
    """
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )