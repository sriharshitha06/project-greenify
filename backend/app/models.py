import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    activities = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    verifications = relationship("ImageVerification", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=datetime.date.today, nullable=False)
    electricity_kwh = Column(Float, default=0.0)
    lpg_cylinders = Column(Float, default=0.0)
    petrol_liters = Column(Float, default=0.0)
    diesel_liters = Column(Float, default=0.0)
    cng_liters = Column(Float, default=0.0)
    diet_type = Column(String, default="vegetarian")  # vegan, vegetarian, meat_heavy
    waste_recycled_pct = Column(Float, default=0.0)    # 0 to 100
    public_transport_km = Column(Float, default=0.0)
    cycling_walking_km = Column(Float, default=0.0)
    carbon_footprint = Column(Float, nullable=False)   # kg CO2e
    classification = Column(String, nullable=False)    # Low, Medium, High, Extreme
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="activities")

class ImageVerification(Base):
    __tablename__ = "image_verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String, nullable=False)     # cycling, reusable_product, public_transport, tree_planting
    image_path = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    status = Column(String, default="Pending")         # Verified, Rejected, Pending
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="verifications")

class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=False)
    icon = Column(String, nullable=False)              # FontAwesome or CSS icon name
    requirement_type = Column(String, nullable=False)  # total_activities, verifications, points, carbon_saved
    requirement_value = Column(Float, nullable=False)

    users = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="users")
