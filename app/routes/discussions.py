"""
Routeur pour la gestion des discussions
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId

from app.database import get_collection
from app.models.discussion import Discussion, DiscussionCreate, DiscussionUpdate, Message, MessageCreate, DiscussionResponse
from app.models.user import User
from app.routes.auth import get_current_user
from app.utils.validators import validate_user_exists, validate_discussion_access

router = APIRouter()

@router.get("/", response_model=List[Discussion])
async def get_discussions(
    linked_type: Optional[str] = Query(None, description="Type de lien (group ou event)"),
    linked_id: Optional[str] = Query(None, description="ID du groupe ou événement"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste des discussions
    Peut être filtrée par type et ID de lien
    """
    discussions_collection = get_collection("discussions")
    if not discussions_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Construire la requête
    query = {"is_active": True}
    
    if linked_type and linked_id:
        query["discussion_type"] = linked_type
        query["linked_id"] = linked_id
    
    cursor = discussions_collection.find(query).sort("is_pinned", -1).sort("updated_at", -1).skip(skip).limit(limit)
    discussions = await cursor.to_list(length=limit)
    
    return [Discussion(**discussion) for discussion in discussions]

@router.get("/{discussion_id}", response_model=DiscussionResponse)
async def get_discussion(
    discussion_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer une discussion spécifique par son ID
    Vérifie les permissions d'accès
    """
    discussions_collection = get_collection("discussions")
    if not discussions_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    discussion = await discussions_collection.find_one({"_id": discussion_id, "is_active": True})
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Vérifier l'accès à la discussion
    await validate_discussion_access(discussion, current_user.id)
    
    # Récupérer les derniers messages
    messages_collection = get_collection("messages")
    last_messages = []
    if messages_collection:
        messages = await messages_collection.find(
            {"discussion_id": discussion_id, "is_active": True}
        ).sort("created_at", -1).limit(10).to_list(length=10)
        last_messages = [Message(**msg) for msg in messages]
    
    # Récupérer les détails de l'auteur
    users_collection = get_collection("users")
    author_details = None
    if users_collection:
        author = await users_collection.find_one(
            {"_id": discussion.get("creator_id"), "is_active": True}
        )
        if author:
            author_details = {"id": author["_id"], "username": author.get("username")}
    
    # Créer la réponse
    response = Discussion(**discussion)
    response_dict = response.model_dump()
    response_dict.update({
        "last_messages": last_messages,
        "author_details": author_details
    })
    
    return DiscussionResponse(**response_dict)

@router.post("/", response_model=Discussion, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    discussion_data: DiscussionCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouveau fil de discussion
    Vérifie que l'utilisateur a accès au groupe/événement lié
    """
    # Valider l'accès au groupe/événement lié
    if discussion_data.discussion_type == "group":
        groups_collection = get_collection("groups")
        if groups_collection:
            group = await groups_collection.find_one({"_id": discussion_data.linked_id, "is_active": True})
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Linked group not found"
                )
            # Vérifier que l'utilisateur est membre du groupe
            if (current_user.id not in group.get("member_ids", []) and 
                current_user.id not in group.get("admin_ids", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create discussion in this group"
                )
    elif discussion_data.discussion_type == "event":
        events_collection = get_collection("events")
        if events_collection:
            event = await events_collection.find_one({"_id": discussion_data.linked_id, "is_active": True})
            if not event:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Linked event not found"
                )
            # Vérifier que l'utilisateur participe à l'événement
            if (current_user.id not in event.get("members", []) and 
                current_user.id not in event.get("organizers", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create discussion for this event"
                )
    
    # Créer la discussion
    discussion_dict = discussion_data.model_dump()
    discussion_dict.update({
        "_id": f"disc_{datetime.utcnow().timestamp()}",
        "creator_id": current_user.id,
        "message_count": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    discussions_collection = get_collection("discussions")
    if discussions_collection:
        await discussions_collection.insert_one(discussion_dict)
    
    return Discussion(**discussion_dict)

@router.post("/{discussion_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(
    discussion_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un message dans une discussion
    """
    # Vérifier que la discussion existe
    discussions_collection = get_collection("discussions")
    if not discussions_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    discussion = await discussions_collection.find_one({"_id": discussion_id, "is_active": True})
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Vérifier l'accès à la discussion
    await validate_discussion_access(discussion, current_user.id)
    
    # Si c'est une réponse, vérifier que le message parent existe
    if message_data.parent_message_id:
        messages_collection = get_collection("messages")
        if messages_collection:
            parent_message = await messages_collection.find_one({
                "_id": message_data.parent_message_id,
                "discussion_id": discussion_id,
                "is_active": True
            })
            if not parent_message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent message not found"
                )
    
    # Créer le message
    message_dict = message_data.model_dump()
    message_dict.update({
        "_id": f"msg_{datetime.utcnow().timestamp()}",
        "author_id": current_user.id,
        "reply_count": 0,
        "is_edited": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    messages_collection = get_collection("messages")
    if messages_collection:
        await messages_collection.insert_one(message_dict)
        
        # Incrémenter le compteur de messages dans la discussion
        await discussions_collection.update_one(
            {"_id": discussion_id},
            {
                "$inc": {"message_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Si c'est une réponse, incrémenter le compteur de réponses du message parent
        if message_data.parent_message_id:
            await messages_collection.update_one(
                {"_id": message_data.parent_message_id},
                {"$inc": {"reply_count": 1}}
            )
    
    return Message(**message_dict)