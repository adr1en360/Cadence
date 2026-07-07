from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base, generate_uuid

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=generate_uuid)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)
    nomba_order_ref = Column(String, unique=True, index=True, nullable=False)
    nomba_transaction_id = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, succeeded, failed, refunded
    idempotency_key = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
