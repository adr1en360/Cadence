from sqlalchemy import Column, String, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)
    interval_days = Column(Numeric(5, 0), nullable=False)  # Interval in days e.g., 30 for monthly
    trial_days = Column(Numeric(5, 0), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="plans")
    api_key = relationship("APIKey", back_populates="plans")
    subscriptions = relationship("Subscription", foreign_keys="[Subscription.plan_id]", back_populates="plan", cascade="all, delete-orphan")
