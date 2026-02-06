"""
Modèles  pour les sondages et questions
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

class QuestionBase(BaseModel):
    """Schéma de base pour une question de sondage"""
    text: str = Field(..., min_length=1, max_length=500, description="Texte de la question")
    
class QuestionCreate(QuestionBase):
    """Schéma pour la création d'une question"""
    answers: List[str] = Field(..., min_items=2, description="Liste des réponses possibles")

class Question(QuestionBase):
    """Schéma de sortie pour une question"""
    id: str = Field(..., alias="_id")
    answers: List[str]
    poll_id: str = Field(..., description="ID du sondage parent")
    response_counts: Dict[str, int] = Field(default_factory=dict, description="Compteur des réponses par option")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class PollBase(BaseModel):
    """Schéma de base pour un sondage"""
    title: str = Field(..., min_length=1, max_length=200, description="Titre du sondage")
    description: Optional[str] = Field(None, max_length=1000, description="Description du sondage")

class PollCreate(PollBase):
    """Schéma pour la création d'un sondage"""
    event_id: str = Field(..., description="ID de l'événement associé")
    questions: List[QuestionCreate] = Field(..., min_items=1, description="Liste des questions")
    is_anonymous: bool = Field(default=False, description="Les réponses sont-elles anonymes ?")
    allow_multiple_votes: bool = Field(default=False, description="Autoriser plusieurs votes par participant")

class PollUpdate(BaseModel):
    """Schéma pour la mise à jour d'un sondage"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_anonymous: Optional[bool] = None
    allow_multiple_votes: Optional[bool] = None

class Poll(PollBase):
    """Schéma de sortie pour un sondage"""
    id: str = Field(..., alias="_id")
    event_id: str
    creator_id: str = Field(..., description="ID du créateur du sondage")
    questions: List[Question]
    is_anonymous: bool
    allow_multiple_votes: bool
    total_responses: int = Field(default=0, description="Nombre total de réponses")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class VoteCreate(BaseModel):
    """Schéma pour voter à un sondage"""
    poll_id: str = Field(..., description="ID du sondage")
    question_id: str = Field(..., description="ID de la question")
    answer: str = Field(..., description="Réponse choisie")

class VoteResponse(BaseModel):
    """Schéma de réponse après un vote"""
    success: bool
    message: str
    poll_id: str
    question_id: str
    chosen_answer: str
    total_votes: int

class PollResponse(Poll):
    """Réponse étendue avec détails supplémentaires"""
    event_details: Optional[dict] = None
    creator_details: Optional[dict] = None
    has_voted: bool = Field(default=False, description="L'utilisateur a-t-il déjà voté ?")