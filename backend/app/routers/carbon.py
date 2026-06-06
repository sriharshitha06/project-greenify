from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import datetime
import io
import csv
from ..database import get_db
from ..models import User, ActivityLog
from ..schemas import ActivityLogCreate, ActivityLogOut
from ..auth import get_current_user
from ..ml.predictor import predictor

router = APIRouter(prefix="/api/carbon", tags=["Carbon Footprint"])

# Set a reference baseline average per-capita daily emissions (e.g., ~15.0 kg CO2e / day)
BASELINE_DAILY_CO2 = 15.0

@router.post("/predict")
def predict_carbon(activity: ActivityLogCreate):
    """
    Predict carbon footprint (ML Regressor + Classifier) without saving
    """
    data_dict = activity.dict()
    co2, category = predictor.predict(data_dict)
    is_anomaly = predictor.detect_anomaly(data_dict)
    return {
        "carbon_footprint": round(co2, 2),
        "classification": category,
        "is_anomaly": is_anomaly
    }

@router.post("/log", response_model=ActivityLogOut)
def log_activity(activity: ActivityLogCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Log daily activity, run ML prediction & anomaly detection, save to DB, and award points if eco-friendly
    """
    data_dict = activity.dict()
    co2, category = predictor.predict(data_dict)
    is_anomaly = predictor.detect_anomaly(data_dict)
    
    # Create the log entry
    log_date = activity.date if activity.date else datetime.date.today()
    
    # Check if a log already exists for this user on this date, update it if it does
    existing_log = db.query(ActivityLog).filter(
        ActivityLog.user_id == current_user.id,
        ActivityLog.date == log_date
    ).first()
    
    if existing_log:
        # Update existing
        for key, value in data_dict.items():
            if key != 'date':
                setattr(existing_log, key, value)
        existing_log.carbon_footprint = co2
        existing_log.classification = category
        existing_log.is_anomaly = is_anomaly
        log_entry = existing_log
    else:
        # Create new
        log_entry = ActivityLog(
            user_id=current_user.id,
            date=log_date,
            electricity_kwh=activity.electricity_kwh,
            lpg_cylinders=activity.lpg_cylinders,
            petrol_liters=activity.petrol_liters,
            diesel_liters=activity.diesel_liters,
            cng_liters=activity.cng_liters,
            diet_type=activity.diet_type,
            waste_recycled_pct=activity.waste_recycled_pct,
            public_transport_km=activity.public_transport_km,
            cycling_walking_km=activity.cycling_walking_km,
            carbon_footprint=co2,
            classification=category,
            is_anomaly=is_anomaly
        )
        db.add(log_entry)

    # Award point rewards for logging and eco-friendly stats
    # 10 base points for logging
    reward_points = 10
    
    # Bonus for low emission day (< 6 kg CO2e)
    if co2 < 6.0:
        reward_points += 15
    elif co2 < 16.0:
        reward_points += 5
        
    # Bonus for recycling
    if activity.waste_recycled_pct > 50.0:
        reward_points += 10
        
    # Bonus for cycling/walking
    if activity.cycling_walking_km > 2.0:
        reward_points += int(activity.cycling_walking_km * 2) # 2 pts per km
        
    # Deduct points if user is trying to cheat (marked as anomaly)
    if is_anomaly:
        reward_points = 0
        
    current_user.points += reward_points
    
    db.commit()
    
    # Auto check for badges
    from .gamification import check_and_award_badges
    check_and_award_badges(current_user, db)
    
    db.refresh(log_entry)
    db.refresh(current_user)
    return log_entry

@router.get("/history", response_model=List[ActivityLogOut])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.date.desc()).all()

@router.get("/analytics")
def get_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.date.asc()).all()
    
    if not logs:
        return {
            "total_entries": 0,
            "average_footprint": 0.0,
            "total_carbon_saved": 0.0,
            "category_breakdown": {"energy": 0, "transport": 0, "diet": 0, "waste": 0},
            "history_chart_data": []
        }
        
    total_co2 = 0.0
    total_saved = 0.0
    
    # Cumulative breakdown sums
    energy_sum = 0.0
    transport_sum = 0.0
    diet_sum = 0.0
    waste_sum = 0.0
    
    history_chart = []
    
    for log in logs:
        # Breakdown calculations
        energy_co2 = (log.electricity_kwh * 0.62) + (log.lpg_cylinders * 24.4)
        transport_co2 = (log.petrol_liters * 2.35) + (log.diesel_liters * 2.68) + (log.cng_liters * 2.50) + (log.public_transport_km * 0.08)
        
        diet_map = {'vegan': 2.0, 'vegetarian': 3.5, 'meat_heavy': 7.0}
        diet_co2 = diet_map.get(log.diet_type.lower(), 3.5)
        waste_co2 = 1.5 * (1.0 - log.waste_recycled_pct / 100.0)
        
        energy_sum += energy_co2
        transport_sum += transport_co2
        diet_sum += diet_co2
        waste_sum += waste_co2
        
        total_co2 += log.carbon_footprint
        
        # Calculate daily savings: if they emit less than baseline, that is positive savings
        # If they emit more, it counts as negative savings or excess
        daily_saved = BASELINE_DAILY_CO2 - log.carbon_footprint
        total_saved += daily_saved
        
        history_chart.append({
            "date": log.date.strftime("%Y-%m-%d"),
            "footprint": round(log.carbon_footprint, 2),
            "energy": round(energy_co2, 2),
            "transport": round(transport_co2, 2),
            "diet": round(diet_co2, 2),
            "waste": round(waste_co2, 2),
            "classification": log.classification,
            "is_anomaly": log.is_anomaly
        })
        
    num_logs = len(logs)
    avg_footprint = total_co2 / num_logs
    
    return {
        "total_entries": num_logs,
        "average_footprint": round(avg_footprint, 2),
        "total_carbon_saved": round(total_saved, 2),
        "category_breakdown": {
            "energy": round(energy_sum / num_logs, 2),
            "transport": round(transport_sum / num_logs, 2),
            "diet": round(diet_sum / num_logs, 2),
            "waste": round(waste_sum / num_logs, 2)
        },
        "history_chart_data": history_chart
    }

@router.get("/download-report")
def download_report(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Date", "Electricity (kWh)", "LPG Cylinders", "Petrol (liters)", 
        "Diesel (liters)", "CNG (liters)", "Diet Type", "Waste Recycled (%)", 
        "Public Transport (km)", "Cycling/Walking (km)", "Carbon Footprint (kg CO2e)", 
        "Classification", "Is Anomaly"
    ])
    
    for log in logs:
        writer.writerow([
            log.date.strftime("%Y-%m-%d"),
            log.electricity_kwh,
            log.lpg_cylinders,
            log.petrol_liters,
            log.diesel_liters,
            log.cng_liters,
            log.diet_type,
            log.waste_recycled_pct,
            log.public_transport_km,
            log.cycling_walking_km,
            round(log.carbon_footprint, 2),
            log.classification,
            "Yes" if log.is_anomaly else "No"
        ])
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="greenify_report_{current_user.username}.csv"'
    }
    
    return StreamingResponse(output, media_type="text/csv", headers=headers)
