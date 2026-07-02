from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    customer_email = Column(String, index=True, nullable=False)
    customer_name = Column(String, nullable=True)
    status = Column(String, default="active", nullable=False)  # trialing, active, past_due, suspended, cancelled, expired
    token_key = Column(String, nullable=True)  # tokenized card key from Nomba
    portal_token = Column(String, nullable=True)
    portal_token_expires_at = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, default=datetime.utcnow, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    trial_end = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="subscription", cascade="all, delete-orphan")
