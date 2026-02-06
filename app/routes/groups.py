"""
Routeur pour la gestion des groupes
Conforme aux spécifications Facebook (public, privé, secret)
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from bson import ObjectId

from app.database import get_collection
from app.models.group import Group, GroupCreate, GroupUpdate, GroupResponse, GroupType
from app.models.user import User
from app.routes.auth import get_current_user
from app.utils.validators import validate_user_exists

router = APIRouter()

@router.get("/", response_model=List[Group])
async def get_groups(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments à retourner"),
    group_type: Optional[GroupType] = Query(None, description="Filtrer par type de groupe"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste des groupes
    Les groupes secrets ne sont pas visibles publiquement
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Construire la requête selon le type de groupe
    query = {"is_active": True}
    
    if group_type:
        query["type"] = group_type
    else:
        # Par défaut, ne pas montrer les groupes secrets aux non-membres
        query["type"] = {"$in": ["public", "private"]}
    
    cursor = groups_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    groups = await cursor.to_list(length=limit)
    
    return [Group(**group) for group in groups]

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer un groupe spécifique par son ID
    Vérifie les permissions d'accès selon le type de groupe
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    group_type = group.get("type", "public")
    
    # Vérifier les permissions d'accès
    if group_type == "secret":
        # Seuls les membres peuvent voir les groupes secrets
        if (current_user.id not in group.get("member_ids", []) and 
            current_user.id not in group.get("admin_ids", []) and
            current_user.id != group.get("creator_id")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this secret group"
            )
    elif group_type == "private":
        # Les groupes privés sont visibles mais le contenu est restreint
        # Pour l'API, on autorise la vue mais on pourrait filtrer le contenu
        pass
    
    # Récupérer les détails des administrateurs et membres
    users_collection = get_collection("users")
    admin_details = []
    member_details = []
    
    if users_collection:
        # Détails des administrateurs
        admin_ids = group.get("admin_ids", [])
        if admin_ids:
            admins = await users_collection.find(
                {"_id": {"$in": admin_ids}, "is_active": True}
            ).to_list(length=len(admin_ids))
            admin_details = [{"id": a["_id"], "username": a.get("username"), "email": a.get("email")} for a in admins]
        
        # Détails des membres
        member_ids = group.get("member_ids", [])
        if member_ids:
            members = await users_collection.find(
                {"_id": {"$in": member_ids}, "is_active": True}
            ).to_list(length=len(member_ids))
            member_details = [{"id": m["_id"], "username": m.get("username"), "email": m.get("email")} for m in members]
    
    # Compter les membres
    member_count = len(member_ids)
    
    # Compter les événements du groupe
    events_collection = get_collection("events")
    event_count = 0
    if events_collection:
        event_count = await events_collection.count_documents({
            "group_id": group_id,
            "is_active": True
        })
    
    # Créer la réponse
    response = Group(**group)
    response_dict = response.model_dump()
    response_dict.update({
        "admin_details": admin_details,
        "member_details": member_details,
        "member_count": member_count,
        "event_count": event_count
    })
    
    return GroupResponse(**response_dict)

@router.post("/", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouveau groupe
    Le créateur devient automatiquement administrateur
    """
    # Valider que les administrateurs existent
    for admin_id in group_data.admin_ids:
        await validate_user_exists(admin_id)
    
    # Préparer le groupe pour la base de données
    group_dict = group_data.model_dump()
    
    # Ajouter les métadonnées
    group_dict.update({
        "_id": f"group_{datetime.utcnow().timestamp()}",
        "creator_id": current_user.id,
        "member_ids": [],  # Initialiser la liste des membres
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # S'assurer que le créateur est dans la liste des administrateurs
    if current_user.id not in group_dict["admin_ids"]:
        group_dict["admin_ids"].append(current_user.id)
    
    # Insérer dans MongoDB
    groups_collection = get_collection("groups")
    if groups_collection:
        await groups_collection.insert_one(group_dict)
    
    return Group(**group_dict)

@router.put("/{group_id}", response_model=Group)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour un groupe existant
    Seuls les administrateurs peuvent modifier le groupe
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le groupe existe et que l'utilisateur est administrateur
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if current_user.id not in group.get("admin_ids", []) and current_user.id != group.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this group"
        )
    
    # Mettre à jour le groupe
    update_data = group_data.model_dump(exclude_unset=True, exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await groups_collection.update_one(
        {"_id": group_id},
        {"$set": update_data}
    )
    
    # Récupérer le groupe mis à jour
    updated_group = await groups_collection.find_one({"_id": group_id})
    
    return Group(**updated_group)

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer (désactiver) un groupe
    Seuls les administrateurs peuvent supprimer le groupe
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le groupe existe et que l'utilisateur est administrateur
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if current_user.id not in group.get("admin_ids", []) and current_user.id != group.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this group"
        )
    
    # Désactiver le groupe plutôt que de le supprimer
    await groups_collection.update_one(
        {"_id": group_id},
        {"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return None

@router.post("/{group_id}/join", response_model=Group)
async def join_group(
    group_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Rejoindre un groupe
    Les règles pour rejoindre dépendent du type de groupe
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le groupe existe
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    group_type = group.get("type", "public")
    
    # Vérifier les règles d'adhésion selon le type de groupe
    if group_type == "secret":
        # Les groupes secrets nécessitent une invitation
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot join a secret group without invitation"
        )
    elif group_type == "private":
        # Les groupes privés peuvent nécessiter une approbation
        # Pour l'instant, on autorise l'adhésion directe
        pass
    
    # Vérifier si l'utilisateur est déjà membre
    if current_user.id in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this group"
        )
    
    # Vérifier si l'utilisateur est déjà administrateur
    if current_user.id in group.get("admin_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already an administrator of this group"
        )
    
    # Ajouter l'utilisateur aux membres
    await groups_collection.update_one(
        {"_id": group_id},
        {
            "$addToSet": {"member_ids": current_user.id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Récupérer le groupe mis à jour
    updated_group = await groups_collection.find_one({"_id": group_id})
    
    return Group(**updated_group)

@router.post("/{group_id}/leave", response_model=Group)
async def leave_group(
    group_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Quitter un groupe
    Un administrateur ne peut pas quitter s'il est le seul administrateur
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le groupe existe
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Vérifier si l'utilisateur est membre
    if current_user.id not in group.get("member_ids", []) and current_user.id not in group.get("admin_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a member of this group"
        )
    
    # Vérifier si l'utilisateur est administrateur
    is_admin = current_user.id in group.get("admin_ids", [])
    
    if is_admin:
        # Vérifier s'il est le seul administrateur
        admin_ids = group.get("admin_ids", [])
        if len(admin_ids) == 1 and admin_ids[0] == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave group as the only administrator"
            )
    
    # Retirer l'utilisateur des membres et/ou administrateurs
    update_operations = {
        "$pull": {},
        "$set": {"updated_at": datetime.utcnow()}
    }
    
    if current_user.id in group.get("member_ids", []):
        update_operations["$pull"]["member_ids"] = current_user.id
    
    if is_admin:
        update_operations["$pull"]["admin_ids"] = current_user.id
    
    await groups_collection.update_one(
        {"_id": group_id},
        update_operations
    )
    
    # Récupérer le groupe mis à jour
    updated_group = await groups_collection.find_one({"_id": group_id})
    
    return Group(**updated_group)

@router.post("/{group_id}/promote/{user_id}", response_model=Group)
async def promote_to_admin(
    group_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Promouvoir un membre en administrateur
    Seuls les administrateurs existants peuvent promouvoir
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le groupe existe et que l'utilisateur est administrateur
    group = await groups_collection.find_one({"_id": group_id, "is_active": True})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if current_user.id not in group.get("admin_ids", []) and current_user.id != group.get("creator_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to promote members"
        )
    
    # Vérifier que l'utilisateur à promouvoir existe et est membre
    if user_id not in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this group"
        )
    
    # Vérifier que l'utilisateur n'est pas déjà administrateur
    if user_id in group.get("admin_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an administrator"
        )
    
    # Promouvoir l'utilisateur
    await groups_collection.update_one(
        {"_id": group_id},
        {
            "$addToSet": {"admin_ids": user_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Récupérer le groupe mis à jour
    updated_group = await groups_collection.find_one({"_id": group_id})
    
    return Group(**updated_group)

@router.get("/user/{user_id}", response_model=List[Group])
async def get_user_groups(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les groupes d'un utilisateur spécifique
    """
    groups_collection = get_collection("groups")
    if not groups_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Construire la requête pour trouver les groupes où l'utilisateur est impliqué
    query = {
        "is_active": True,
        "$or": [
            {"creator_id": user_id},
            {"admin_ids": user_id},
            {"member_ids": user_id}
        ]
    }
    
    cursor = groups_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    groups = await cursor.to_list(length=limit)
    
    return [Group(**group) for group in groups]