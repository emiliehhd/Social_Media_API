"""
Fonctions de sécurité (hachage, tokens, etc.)
"""

from fastapi import HTTPException, status
from passlib.context import CryptContext
import bcrypt

# Configuration du hachage de mdp
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
s = bcrypt.gensalt()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifier un mot de passe contre son hash
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hasher un mot de passe
    """
    # return pwd_context.hash(password)
    pw = b'password'
    return bcrypt.hashpw(pw, s)