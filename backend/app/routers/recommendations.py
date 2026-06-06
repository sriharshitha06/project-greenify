from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import User, ActivityLog
from ..schemas import RecommendationResponse
from ..auth import get_current_user
from ..rag.sustainability_rag import rag_advisor

router = APIRouter(prefix="/api/recommendations", tags=["Sustainability Advisor (RAG)"])

@router.get("/get", response_model=RecommendationResponse)
def get_recommendations(
    query: Optional[str] = Query(None, description="Custom search query for advisor"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves personalized recommendations using RAG. If query is omitted, it automatically
    analyzes the user's latest log to search for matches.
    """
    # Fetch user's latest activity log
    latest_log = db.query(ActivityLog).filter(
        ActivityLog.user_id == current_user.id
    ).order_by(ActivityLog.date.desc()).first()
    
    # If user hasn't logged anything, use a default skeleton dict representing average profile
    if not latest_log:
        latest_log_dict = {
            "electricity_kwh": 10.0,
            "lpg_cylinders": 0.05,
            "petrol_liters": 3.0,
            "diesel_liters": 1.0,
            "cng_liters": 0.0,
            "diet_type": "vegetarian",
            "waste_recycled_pct": 20.0,
            "public_transport_km": 5.0,
            "cycling_walking_km": 1.0
        }
    else:
        # Convert SQLAlchemy object to dictionary
        latest_log_dict = {
            "electricity_kwh": latest_log.electricity_kwh,
            "lpg_cylinders": latest_log.lpg_cylinders,
            "petrol_liters": latest_log.petrol_liters,
            "diesel_liters": latest_log.diesel_liters,
            "cng_liters": latest_log.cng_liters,
            "diet_type": latest_log.diet_type,
            "waste_recycled_pct": latest_log.waste_recycled_pct,
            "public_transport_km": latest_log.public_transport_km,
            "cycling_walking_km": latest_log.cycling_walking_km
        }
        
    result = rag_advisor.generate_recommendations(
        user_name=current_user.username,
        activity_log=latest_log_dict,
        query_text=query
    )
    
    return result
