from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base, generate_uuid

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=True)
    event_type = Column(String, nullable=False)  # subscription.activated, payment.failed, etc.
    data_json = Column(Text, nullable=False)  # JSON dump of event context/metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="events")
    subscription = relationship("Subscription", back_populates="events")
