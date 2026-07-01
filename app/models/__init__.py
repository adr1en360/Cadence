from app.core.database import Base
from app.models.project import Project
from app.models.merchant import Merchant, APIKey
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.event import Event

# Expose Base.metadata for Alembic discovery
metadata = Base.metadata
