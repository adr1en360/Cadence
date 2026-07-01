from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nomba_client_id = Column(String, nullable=True)
    nomba_client_secret_encrypted = Column(String, nullable=True)
    nomba_account_id = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship("APIKey", back_populates="merchant", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="merchant", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String(16), nullable=False)
    label = Column(String, nullable=False)
    nomba_sub_account_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    merchant = relationship("Merchant", back_populates="api_keys")
    plans = relationship("Plan", back_populates="api_key", cascade="all, delete-orphan")
