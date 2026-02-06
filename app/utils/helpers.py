"""
Fonctions compleùentaires pour l'application
"""

from datetime import datetime
from typing import Any, Dict

def generate_id(prefix: str) -> str:
    """
    Générer un ID unique avec un préfixe
    """
    timestamp = datetime.utcnow().timestamp()
    return f"{prefix}_{timestamp}"

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nettoyer un dictionnaire en retirant les valeurs None
    """
    return {k: v for k, v in data.items() if v is not None}

def format_datetime(dt: datetime) -> str:
    """
    Formater une date pour l'affichage
    """
    return dt.isoformat() if dt else None