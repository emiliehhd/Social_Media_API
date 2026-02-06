"""
Routeur pour la gestion des utilisateurs
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId

from app.database import get_collection
from app.models.user import User, UserCreate, UserUpdate
from app.routes.auth import get_current_user
from app.utils.validators import validate_email_unique

router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments à retourner"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste des utilisateurs avec pagination.
    Accessible seulement aux utilisateurs authentifiés
    """
    users_collection = get_collection("users")
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    cursor = users_collection.find({"is_active": True}).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return [User(**user) for user in users]

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer un utilisateur par son ID
    """
    users_collection = get_collection("users")
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    user = await users_collection.find_one({"_id": user_id, "is_active": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return User(**user)

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouvel utilisateur (pour les admin) et valide l'email unique
    """
    
    # Vérifie l'email unique
    await validate_email_unique(user_data.email)
    
    # Importe les fonctions de sécurité d' auth.py
    from app.routes.auth import get_password_hash
    from datetime import datetime
    
    # Hasher le mot de passe
    hashed_password = get_password_hash(user_data.password)
    
    # Préparer l'utilisateur pour la base de données
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict.update({
        "_id": f"user_{datetime.utcnow().timestamp()}_{user_data.email}",
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # Insérer dans MongoDB
    users_collection = get_collection("users")
    if users_collection is not None:
        await users_collection.insert_one(user_dict)
    
    return User(**user_dict)

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour un utilisateur
    l'utilisateur peut se mettre à jour ou un admin
    """
    users_collection = get_collection("users")
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'utilisateur existe
    existing_user = await users_collection.find_one({"_id": user_id, "is_active": True})
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Vérifier les permissions (utilisateur peut se mettre à jour lui-même)
    if current_user.id != user_id:
        # Ici, on pourrait vérifier les rôles d'administrateur
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    # Vérifier l'unicité de l'email si fourni
    if user_data.email:
        await validate_email_unique(user_data.email, exclude_user_id=user_id)
    
    # Préparer les données de mise à jour
    update_data = user_data.model_dump(exclude_unset=True, exclude_none=True)
    
    # Hasher le mot de passe si fourni
    if "password" in update_data:
        from app.routes.auth import get_password_hash
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Ajouter la date de mise à jour
    from datetime import datetime
    update_data["updated_at"] = datetime.utcnow()
    
    # Mettre à jour dans MongoDB
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": update_data}
    )
    
    # Récupérer l'utilisateur mis à jour
    updated_user = await users_collection.find_one({"_id": user_id})
    
    return User(**updated_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer un utilisateur (désactivation)
    Seul l'utilisateur peut se supprimer ou un admin
    """
    users_collection = get_collection("users")
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que l'utilisateur existe
    existing_user = await users_collection.find_one({"_id": user_id, "is_active": True})
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Vérifier les permissions
    if current_user.id != user_id:
        # Ici, on pourrait vérifier les rôles d'administrateur
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )
    
    # Désactiver l'utilisateur plutôt que de le supprimer
    from datetime import datetime
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return None

@router.get("/search/", response_model=List[User])
async def search_users(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Rechercher des utilisateurs par nom, prénom ou email
    """
    users_collection = get_collection("users")
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Créer une requête de recherche
    query = {
        "is_active": True,
        "$or": [
            {"username": {"$regex": q, "$options": "i"}},
            {"first_name": {"$regex": q, "$options": "i"}},
            {"last_name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]
    }
    
    cursor = users_collection.find(query).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return [User(**user) for user in users]