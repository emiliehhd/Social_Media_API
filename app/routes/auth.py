"""
Routeur pour l'authentification des utilisateurs
Gère l'inscription, la connexion et les tokens JWT
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.database import get_collection
from app.models.user import UserCreate, User, UserLogin
from app.utils.security import verify_password, get_password_hash
from app.utils.validators import validate_email_unique

import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Configuration sécurité
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_HHED")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT d'accès"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Obtenir l'utilisateur courant à partir du token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users_collection = get_collection("users")
    if users_collection is None:
        raise credentials_exception
    
    user = await users_collection.find_one({"_id": user_id})
    if user is None:
        raise credentials_exception
    
    return User(**user)

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Inscription d'un nouvel utilisateur
    Verifie quz l'email n'existe pas déjà avant la création
    """
    # Vérifier l'email
    await validate_email_unique(user_data.email)
    
    # Hasher le mot de passe
    hashed_password = get_password_hash(user_data.password)
    
    # Préparer l'utilisateur pour la bdd
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict.update({
        "_id": f"user_{datetime.utcnow().timestamp()}",
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # ajout dans MongoDB
    users_collection = get_collection("users")
    if users_collection is not None:
        await users_collection.insert_one(user_dict)
    
    # Retourner l'utilisateur sans le mot de passe
    return User(**user_dict)

@router.post("/login")
async def login(login_data: LoginRequest):
    """
    Connexion d'un utilisateur
    Retourne un token JWT en cas de succès
    """
    users_collection = get_collection("users")
    if not users_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Chercher l'utilisateur par email
    user = await users_collection.find_one({"email": login_data.username})
    if not user or not verify_password(login_data.password, user.get("hashed_password")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Créer le token d'accès
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["_id"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["_id"],
        "email": user["email"],
        "username": user.get("username", "")
    }

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Récupérer les infos de l'user connecté
    """
    return current_user