"""
Routeur pour la gestion des albums photos
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
import shutil
import os

from app.database import get_collection
from app.models.album import Album, AlbumCreate, Photo, PhotoCreate, Comment, CommentCreate
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()

# Configuration pour le stockage des photos
UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/events/{event_id}", response_model=List[Album])
async def get_event_albums(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer tous les albums d'un événement
    """
    albums_collection = get_collection("albums")
    if not albums_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    albums = await albums_collection.find({"event_id": event_id, "is_active": True}).to_list(length=100)
    return [Album(**album) for album in albums]

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
async def create_album(
    album_data: AlbumCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouvel album photo pour un événement
    """
    # Vérifier que l'événement existe
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": album_data.event_id, "is_active": True})
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        # Vérifier que l'utilisateur participe à l'événement
        if (current_user.id not in event.get("members", []) and 
            current_user.id not in event.get("organizers", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create album for this event"
            )
    
    # Vérifier qu'il n'y a pas déjà un album avec le même nom pour cet événement
    albums_collection = get_collection("albums")
    if albums_collection:
        existing_album = await albums_collection.find_one({
            "event_id": album_data.event_id,
            "name": album_data.name,
            "is_active": True
        })
        if existing_album:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An album with this name already exists for this event"
            )
    
    # Créer l'album
    album_dict = album_data.model_dump()
    album_dict.update({
        "_id": f"album_{datetime.utcnow().timestamp()}",
        "creator_id": current_user.id,
        "photo_count": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    if albums_collection:
        await albums_collection.insert_one(album_dict)
    
    return Album(**album_dict)

@router.post("/photos/", response_model=Photo, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str = Query(...),
    caption: str = Query(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploader une photo dans un album
    """
    # Vérifier que l'album existe
    albums_collection = get_collection("albums")
    if not albums_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    album = await albums_collection.find_one({"_id": album_id, "is_active": True})
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Vérifier que l'utilisateur a accès à l'événement
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": album["event_id"], "is_active": True})
        if event:
            if (current_user.id not in event.get("members", []) and 
                current_user.id not in event.get("organizers", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to upload photos to this event"
                )
    
    # Sauvegarder le fichier
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"photo_{datetime.utcnow().timestamp()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Créer l'entrée photo dans la base de données
    photo_dict = {
        "_id": f"photo_{datetime.utcnow().timestamp()}",
        "album_id": album_id,
        "event_id": album["event_id"],
        "author_id": current_user.id,
        "caption": caption,
        "image_url": f"/uploads/photos/{filename}",
        "like_count": 0,
        "comment_count": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    photos_collection = get_collection("photos")
    if photos_collection:
        await photos_collection.insert_one(photo_dict)
        
        # Incrémenter le compteur de photos dans l'album
        await albums_collection.update_one(
            {"_id": album_id},
            {
                "$inc": {"photo_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
    
    return Photo(**photo_dict)

@router.post("/photos/{photo_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment(
    photo_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Ajouter un commentaire à une photo
    """
    # Vérifier que la photo existe
    photos_collection = get_collection("photos")
    if not photos_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    photo = await photos_collection.find_one({"_id": photo_id, "is_active": True})
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Vérifier que l'utilisateur a accès à l'événement
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": photo["event_id"], "is_active": True})
        if event:
            if (current_user.id not in event.get("members", []) and 
                current_user.id not in event.get("organizers", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to comment on this photo"
                )
    
    # Créer le commentaire
    comment_dict = comment_data.model_dump()
    comment_dict.update({
        "_id": f"comment_{datetime.utcnow().timestamp()}",
        "author_id": current_user.id,
        "is_edited": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    comments_collection = get_collection("comments")
    if comments_collection:
        await comments_collection.insert_one(comment_dict)
        
        # Incrémenter le compteur de commentaires sur la photo
        await photos_collection.update_one(
            {"_id": photo_id},
            {"$inc": {"comment_count": 1}}
        )
    
    return Comment(**comment_dict)