# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

# User Auth schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    points: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Carbon Footprint schemas
class ActivityLogCreate(BaseModel):
    date: Optional[date] = None
    electricity_kwh: float = Field(0.0, ge=0.0)
    lpg_cylinders: float = Field(0.0, ge=0.0)
    petrol_liters: float = Field(0.0, ge=0.0)
    diesel_liters: float = Field(0.0, ge=0.0)
    cng_liters: float = Field(0.0, ge=0.0)
    diet_type: str = Field("vegetarian", pattern="^(vegan|vegetarian|meat_heavy)$")
    waste_recycled_pct: float = Field(0.0, ge=0.0, le=100.0)
    public_transport_km: float = Field(0.0, ge=0.0)
    cycling_walking_km: float = Field(0.0, ge=0.0)

class ActivityLogOut(BaseModel):
    id: int
    user_id: int
    date: date
    electricity_kwh: float
    lpg_cylinders: float
    petrol_liters: float
    diesel_liters: float
    cng_liters: float
    diet_type: str
    waste_recycled_pct: float
    public_transport_km: float
    cycling_walking_km: float
    carbon_footprint: float
    classification: str
    is_anomaly: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Verification schemas
class VerificationOut(BaseModel):
    id: int
    user_id: int
    activity_type: str
    image_path: str
    confidence: float
    status: str
    points_earned: int
    created_at: datetime

    class Config:
        from_attributes = True

# Gamification schemas
class BadgeOut(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    requirement_type: str
    requirement_value: float

    class Config:
        from_attributes = True

class UserBadgeOut(BaseModel):
    id: int
    badge: BadgeOut
    earned_at: datetime

    class Config:
        from_attributes = True

class LeaderboardUserOut(BaseModel):
    username: str
    points: int
    rank: int

# Recommendation schemas
class RecommendationItem(BaseModel):
    category: str
    title: str
    description: str
    impact: str

class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]
    advice: str
