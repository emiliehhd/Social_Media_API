"""
Routeur pour la gestion des sondages
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import get_collection
from app.models.poll import Poll, PollCreate, VoteCreate, VoteResponse
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/events/{event_id}", response_model=List[Poll])
async def get_event_polls(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer tous les sondages d'un événement
    """
    polls_collection = get_collection("polls")
    if not polls_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    polls = await polls_collection.find({"event_id": event_id, "is_active": True}).to_list(length=100)
    return [Poll(**poll) for poll in polls]

@router.post("/", response_model=Poll, status_code=status.HTTP_201_CREATED)
async def create_poll(
    poll_data: PollCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un nouveau sondage pour un événement
    """
    # Vérifier que l'événement existe
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": poll_data.event_id, "is_active": True})
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        # Vérifier que l'utilisateur est organisateur de l'événement
        if current_user.id not in event.get("organizers", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only event organizers can create polls"
            )
    
    # Créer le sondage
    poll_dict = poll_data.model_dump()
    
    # Préparer les questions avec les compteurs de réponses
    questions_with_counts = []
    for q in poll_dict["questions"]:
        q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
        q_dict["response_counts"] = {answer: 0 for answer in q_dict["answers"]}
        questions_with_counts.append(q_dict)
    
    poll_dict.update({
        "_id": f"poll_{datetime.utcnow().timestamp()}",
        "creator_id": current_user.id,
        "questions": questions_with_counts,
        "total_responses": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    polls_collection = get_collection("polls")
    if polls_collection:
        await polls_collection.insert_one(poll_dict)
    
    return Poll(**poll_dict)

@router.post("/vote", response_model=VoteResponse)
async def vote_poll(
    vote_data: VoteCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Voter à un sondage
    """
    polls_collection = get_collection("polls")
    if not polls_collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    
    # Vérifier que le sondage existe
    poll = await polls_collection.find_one({"_id": vote_data.poll_id, "is_active": True})
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Vérifier que l'utilisateur participe à l'événement
    events_collection = get_collection("events")
    if events_collection:
        event = await events_collection.find_one({"_id": poll["event_id"], "is_active": True})
        if event:
            if (current_user.id not in event.get("members", []) and 
                current_user.id not in event.get("organizers", [])):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to vote in this poll"
                )
    
    # Vérifier si l'utilisateur a déjà voté (si le sondage n'autorise pas plusieurs votes)
    if not poll.get("allow_multiple_votes", False):
        votes_collection = get_collection("votes")
        if votes_collection:
            existing_vote = await votes_collection.find_one({
                "poll_id": vote_data.poll_id,
                "user_id": current_user.id
            })
            if existing_vote:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already voted in this poll"
                )
    
    # Trouver la question et vérifier que la réponse est valide
    question_found = False
    for question in poll["questions"]:
        if question["_id"] == vote_data.question_id:
            question_found = True
            if vote_data.answer not in question["answers"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid answer for this question"
                )
            break
    
    if not question_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in this poll"
        )
    
    # Enregistrer le vote
    votes_collection = get_collection("votes")
    if votes_collection:
        vote_dict = {
            "_id": f"vote_{datetime.utcnow().timestamp()}",
            "poll_id": vote_data.poll_id,
            "question_id": vote_data.question_id,
            "user_id": current_user.id,
            "answer": vote_data.answer,
            "created_at": datetime.utcnow()
        }
        await votes_collection.insert_one(vote_dict)
    
    # Mettre à jour les compteurs de votes dans le sondage
    await polls_collection.update_one(
        {
            "_id": vote_data.poll_id,
            "questions._id": vote_data.question_id
        },
        {
            "$inc": {
                "total_responses": 1,
                "questions.$.response_counts." + vote_data.answer: 1
            }
        }
    )
    
    # Récupérer le sondage mis à jour pour obtenir le nombre total de votes
    updated_poll = await polls_collection.find_one({"_id": vote_data.poll_id})
    total_votes = updated_poll.get("total_responses", 0) if updated_poll else 0
    
    return VoteResponse(
        success=True,
        message="Vote recorded successfully",
        poll_id=vote_data.poll_id,
        question_id=vote_data.question_id,
        chosen_answer=vote_data.answer,
        total_votes=total_votes
    )