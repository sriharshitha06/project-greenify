import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, ImageVerification
from ..schemas import VerificationOut
from ..auth import get_current_user
from ..cv.image_verifier import verifier

router = APIRouter(prefix="/api/verify", tags=["Activity Verification"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Point rewards for image verifications
CV_VERIFICATION_POINTS = 50

@router.post("/upload", response_model=VerificationOut)
def upload_activity_image(
    file: UploadFile = File(...),
    activity_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an activity verification photo (cycling, reusable cup, public transit, tree planting)
    and verify it using OpenCV.
    """
    valid_types = ["cycling", "reusable_product", "public_transport", "tree_planting"]
    if activity_type.lower() not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity type. Must be one of: {', '.join(valid_types)}"
        )

    # Save uploaded file
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file: {e}"
        )

    # Run OpenCV verification
    is_verified, confidence, message = verifier.verify_image(file_path, activity_type)
    
    status_str = "Verified" if is_verified else "Rejected"
    points_earned = CV_VERIFICATION_POINTS if is_verified else 0
    
    # Save verification record in DB
    # We store a relative or absolute path, storing the filename or path.
    # We will serve this file via FastAPI StaticFiles so the user can see it annotated in the dashboard!
    relative_image_path = f"/uploads/{unique_filename}"
    
    log_entry = ImageVerification(
        user_id=current_user.id,
        activity_type=activity_type.lower(),
        image_path=relative_image_path,
        confidence=confidence,
        status=status_str,
        points_earned=points_earned
    )
    
    db.add(log_entry)
    
    if is_verified:
        current_user.points += points_earned
        
    db.commit()
    
    # Auto check for badges
    from .gamification import check_and_award_badges
    check_and_award_badges(current_user, db)
    
    db.refresh(log_entry)
    db.refresh(current_user)
    
    return log_entry

@router.get("/history", response_model=List[VerificationOut])
def get_verification_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ImageVerification).filter(ImageVerification.user_id == current_user.id).order_by(ImageVerification.created_at.desc()).all()
