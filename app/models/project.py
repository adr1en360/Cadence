from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    name = Column(String, nullable=False)
    
    # Connected Nomba Credentials per Project
    nomba_client_id = Column(String, nullable=True)
    nomba_client_secret_encrypted = Column(String, nullable=True)
    nomba_account_id = Column(String, nullable=True)
    
    # DB-backed Token Cache for this project
    nomba_access_token = Column(String, nullable=True)
    nomba_token_expires_at = Column(DateTime, nullable=True)
    
    # Webhook settings
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    merchant = relationship("Merchant", back_populates="projects")
    api_keys = relationship("APIKey", back_populates="project", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="project", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="project", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="project", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="project", cascade="all, delete-orphan")
