from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import datetime
from ..database import get_db
from ..models import User, Badge, UserBadge, ActivityLog, ImageVerification
from ..schemas import BadgeOut, UserBadgeOut, LeaderboardUserOut
from ..auth import get_current_user

router = APIRouter(prefix="/api/gamification", tags=["Gamification & Badges"])

# Seeding badges helper
def seed_badges(db: Session):
    default_badges = [
        {
            "name": "Eco Novice",
            "description": "Log your first daily activity to start tracking your footprint.",
            "icon": "leaf",
            "requirement_type": "total_logs",
            "requirement_value": 1.0
        },
        {
            "name": "Pedal Power",
            "description": "Log a total of 10+ km of cycling or walking.",
            "icon": "bicycle",
            "requirement_type": "cycling_km",
            "requirement_value": 10.0
        },
        {
            "name": "Zero Waste Hero",
            "description": "Reach a recycling rate of 80% or more in a single log.",
            "icon": "recycle",
            "requirement_type": "recycling_pct",
            "requirement_value": 80.0
        },
        {
            "name": "Green Commuter",
            "description": "Log a total of 50+ km of public transport travel.",
            "icon": "bus",
            "requirement_type": "public_transport_km",
            "requirement_value": 50.0
        },
        {
            "name": "Eagle Eye",
            "description": "Successfully verify 3 eco-friendly activities via OpenCV image upload.",
            "icon": "camera",
            "requirement_type": "verifications",
            "requirement_value": 3.0
        },
        {
            "name": "Carbon Champion",
            "description": "Accumulate 300+ total green reward points.",
            "icon": "trophy",
            "requirement_type": "points",
            "requirement_value": 300.0
        }
    ]

    for dbadge in default_badges:
        exists = db.query(Badge).filter(Badge.name == dbadge["name"]).first()
        if not exists:
            badge = Badge(
                name=dbadge["name"],
                description=dbadge["description"],
                icon=dbadge["icon"],
                requirement_type=dbadge["requirement_type"],
                requirement_value=dbadge["requirement_value"]
            )
            db.add(badge)
    db.commit()

def check_and_award_badges(user: User, db: Session) -> List[Badge]:
    """
    Checks user metrics and unlocks any badges they qualify for.
    Returns list of newly earned badges.
    """
    # 1. Gather User Metrics
    total_logs = db.query(func.count(ActivityLog.id)).filter(ActivityLog.user_id == user.id).scalar() or 0
    total_cycling_km = db.query(func.sum(ActivityLog.cycling_walking_km)).filter(ActivityLog.user_id == user.id).scalar() or 0.0
    total_transit_km = db.query(func.sum(ActivityLog.public_transport_km)).filter(ActivityLog.user_id == user.id).scalar() or 0.0
    max_recycling = db.query(func.max(ActivityLog.waste_recycled_pct)).filter(ActivityLog.user_id == user.id).scalar() or 0.0
    
    total_verifications = db.query(func.count(ImageVerification.id)).filter(
        ImageVerification.user_id == user.id,
        ImageVerification.status == "Verified"
    ).scalar() or 0
    
    user_points = user.points

    metrics = {
        "total_logs": float(total_logs),
        "cycling_km": float(total_cycling_km),
        "public_transport_km": float(total_transit_km),
        "recycling_pct": float(max_recycling),
        "verifications": float(total_verifications),
        "points": float(user_points)
    }

    # Fetch badges already earned
    earned_badge_ids = [ub.badge_id for ub in user.badges]
    
    # Query all available badges
    all_badges = db.query(Badge).all()
    newly_earned = []

    for badge in all_badges:
        if badge.id not in earned_badge_ids:
            req_type = badge.requirement_type
            req_val = badge.requirement_value
            
            # Check condition
            if metrics.get(req_type, 0.0) >= req_val:
                # Award Badge
                user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                db.add(user_badge)
                newly_earned.append(badge)
                
                # Bonus points for earning a badge!
                user.points += 100
                
    if newly_earned:
        db.commit()
        
    return newly_earned

@router.get("/leaderboard", response_model=List[LeaderboardUserOut])
def get_leaderboard(db: Session = Depends(get_db)):
    """
    Retrieves global user leaderboard ranked by green points
    """
    users = db.query(User).order_by(User.points.desc()).all()
    
    leaderboard = []
    for rank, u in enumerate(users, 1):
        leaderboard.append({
            "username": u.username,
            "points": u.points,
            "rank": rank
        })
    return leaderboard

@router.get("/badges")
def get_user_badges(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns all badges and notes which ones the user has unlocked.
    """
    # Trigger checking in case they qualified recently
    check_and_award_badges(current_user, db)
    
    all_badges = db.query(Badge).all()
    earned_badge_ids = {ub.badge_id: ub.earned_at for ub in current_user.badges}
    
    result = []
    for badge in all_badges:
        is_unlocked = badge.id in earned_badge_ids
        result.append({
            "id": badge.id,
            "name": badge.name,
            "description": badge.description,
            "icon": badge.icon,
            "requirement_type": badge.requirement_type,
            "requirement_value": badge.requirement_value,
            "unlocked": is_unlocked,
            "earned_at": earned_badge_ids.get(badge.id).strftime("%Y-%m-%d %H:%M:%S") if is_unlocked else None
        })
    return result

@router.post("/check-badges")
def trigger_badge_check(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    newly_earned = check_and_award_badges(current_user, db)
    return {
        "status": "success",
        "newly_earned_count": len(newly_earned),
        "new_badges": [b.name for b in newly_earned]
    }
