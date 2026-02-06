"""
Routeur pour la gestion des événements
Conforme aux spécifications Facebook (3 étapes de création)
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from bson import ObjectId

from app.database import get_collection
from app.models.event import Event, EventCreate, EventUpdate, EventConfig, EventResponse
from app.models.user import User
from app.routes.auth import get_current_user
from app.utils.validators import validate_user_exists

router = APIRouter()

@router.get("/", response_model=List[Event])
async def get_events(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments à retourner"),
    public_only: bool = Query(True, description="Afficher uniquement les événements publics"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste des événements
    Par défaut, ne montre que les événements publics
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Construire la requête
    query = {"is_active": True}
    
    if public_only:
        query["privacy"] = "public"
    else:
        # Si l'utilisateur veut voir les événements privés, vérifier s'il y a accès
        query["$or"] = [
            {"privacy": "public"},
            {"members": current_user.id},
            {"organizers": current_user.id},
            {"creator_id": current_user.id}
        ]
    
    cursor = events_collection.find(query).sort("start_date", 1).skip(skip).limit(limit)
    events = await cursor.to_list(length=limit)
    
    return [Event(**event) for event in events]

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer un événement spécifique par son ID
    Vérifie les permissions d'accès pour les événements privés
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    event = await events_collection.find_one({"_id": event_id, "is_active": True})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Vérifier l'accès pour les événements privés
    if event.get("privacy") == "private":
        if (current_user.id not in event.get("members", []) and 
            current_user.id not in event.get("organizers", []) and
            current_user.id != event.get("creator_id")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this private event"
            )
    
    # Récupérer les détails des organisateurs et membres
    users_collection = get_collection("users")
    organizer_details = []
    member_details = []
    
    if users_collection:
        # Détails des organisateurs
        organizer_ids = event.get("organizers", [])
        if organizer_ids:
            organizers = await users_collection.find(
                {"_id": {"$in": organizer_ids}, "is_active": True}
            ).to_list(length=len(organizer_ids))
            organizer_details = [{"id": o["_id"], "username": o.get("username"), "email": o.get("email")} for o in organizers]
        
        # Détails des membres
        member_ids = event.get("members", [])
        if member_ids:
            members = await users_collection.find(
                {"_id": {"$in": member_ids}, "is_active": True}
            ).to_list(length=len(member_ids))
            member_details = [{"id": m["_id"], "username": m.get("username"), "email": m.get("email")} for m in members]
    
    # Compter les participants
    participant_count = len(organizer_ids) + len(member_ids)
    
    # Créer la réponse
    response = Event(**event)
    response_dict = response.model_dump()
    response_dict.update({
        "organizer_details": organizer_details,
        "member_details": member_details,
        "participant_count": participant_count
    })
    
    return EventResponse(**response_dict)

@router.post("/", response_model=Event, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouvel événement en 3 étapes
    Première étape : Configuration de l'événement
    """
    # Valider que les organisateurs existent
    for organizer_id in event_data.organizers:
        await validate_user_exists(organizer_id)
    
    # Valider que les membres existent
    for member_id in event_data.members:
        await validate_user_exists(member_id)
    
    # Si l'événement est lié à un groupe, vérifier le groupe
    group_members_to_add = []
    if event_data.group_id and event_data.auto_invite:
        groups_collection = get_collection("groups")
        if groups_collection:
            group = await groups_collection.find_one({
                "_id": event_data.group_id,
                "is_active": True
            })
            if group:
                # Ajouter les membres du groupe aux invités
                group_members_to_add = group.get("member_ids", [])
    
    # Préparer l'événement pour la base de données
    event_dict = event_data.model_dump()
    
    # Fusionner les membres existants avec les membres du groupe (si auto_invite)
    all_members = list(set(event_dict.get("members", []) + group_members_to_add))
    event_dict["members"] = all_members
    
    # Ajouter les métadonnées
    event_dict.update({
        "_id": f"event_{datetime.utcnow().timestamp()}",
        "creator_id": current_user.id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # S'assurer que le créateur est dans la liste des organisateurs
    if current_user.id not in event_dict["organizers"]:
        event_dict["organizers"].append(current_user.id)
    
    # Insérer dans MongoDB
    events_collection = get_collection("events")
    if events_collection:
        await events_collection.insert_one(event_dict)
    
    return Event(**event_dict)

@router.post("/{event_id}/config", response_model=Event)
async def configure_event(
    event_id: str,
    event_config: EventConfig,
    current_user: User = Depends(get_current_user)
):
    """
    Deuxième étape : Configurer un événement existant
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'événement existe et que l'utilisateur est organisateur
    event = await events_collection.find_one({"_id": event_id, "is_active": True})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user.id not in event.get("organizers", []) and current_user.id != event.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to configure this event"
        )
    
    # Valider que les nouveaux organisateurs existent
    for organizer_id in event_config.organizers:
        await validate_user_exists(organizer_id)
    
    # Valider que les nouveaux membres existent
    for member_id in event_config.members:
        await validate_user_exists(member_id)
    
    # Mettre à jour l'événement
    update_data = event_config.model_dump(exclude_unset=True, exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await events_collection.update_one(
        {"_id": event_id},
        {"$set": update_data}
    )
    
    # Récupérer l'événement mis à jour
    updated_event = await events_collection.find_one({"_id": event_id})
    
    return Event(**updated_event)

@router.put("/{event_id}", response_model=Event)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour un événement existant
    Seuls les organisateurs peuvent modifier l'événement
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'événement existe et que l'utilisateur est organisateur
    event = await events_collection.find_one({"_id": event_id, "is_active": True})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user.id not in event.get("organizers", []) and current_user.id != event.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this event"
        )
    
    # Valider que les nouveaux organisateurs existent
    if event_data.organizers:
        for organizer_id in event_data.organizers:
            await validate_user_exists(organizer_id)
    
    # Valider que les nouveaux membres existent
    if event_data.members:
        for member_id in event_data.members:
            await validate_user_exists(member_id)
    
    # Mettre à jour l'événement
    update_data = event_data.model_dump(exclude_unset=True, exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await events_collection.update_one(
        {"_id": event_id},
        {"$set": update_data}
    )
    
    # Récupérer l'événement mis à jour
    updated_event = await events_collection.find_one({"_id": event_id})
    
    return Event(**updated_event)

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer (désactiver) un événement
    Seuls les organisateurs peuvent supprimer l'événement
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'événement existe et que l'utilisateur est organisateur
    event = await events_collection.find_one({"_id": event_id, "is_active": True})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user.id not in event.get("organizers", []) and current_user.id != event.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this event"
        )
    
    # Désactiver l'événement plutôt que de le supprimer
    await events_collection.update_one(
        {"_id": event_id},
        {"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return None

@router.post("/{event_id}/join", response_model=Event)
async def join_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Rejoindre un événement public
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'événement existe et est public
    event = await events_collection.find_one({"_id": event_id, "is_active": True})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.get("privacy") != "public":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot join a private event without invitation"
        )
    
    # Vérifier si l'utilisateur est déjà membre
    if current_user.id in event.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this event"
        )
    
    # Vérifier si l'utilisateur est déjà organisateur
    if current_user.id in event.get("organizers", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already an organizer of this event"
        )
    
    # Ajouter l'utilisateur aux membres
    await events_collection.update_one(
        {"_id": event_id},
        {
            "$addToSet": {"members": current_user.id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Récupérer l'événement mis à jour
    updated_event = await events_collection.find_one({"_id": event_id})
    
    return Event(**updated_event)

@router.get("/user/{user_id}", response_model=List[Event])
async def get_user_events(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les événements d'un utilisateur spécifique
    """
    events_collection = get_collection("events")
    if not events_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Construire la requête pour trouver les événements où l'utilisateur est impliqué
    query = {
        "is_active": True,
        "$or": [
            {"creator_id": user_id},
            {"organizers": user_id},
            {"members": user_id}
        ]
    }
    
    cursor = events_collection.find(query).sort("start_date", 1).skip(skip).limit(limit)
    events = await cursor.to_list(length=limit)
    
    return [Event(**event) for event in events]