from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.api import router_auth, router_plans, router_subscriptions, router_payments, router_webhooks, router_dashboard, router_portal, developer_routes

app = FastAPI(
    title="Cadence Subscription Engine",
    description="Managed subscription billing engine built on Nomba's payment APIs",
    version="0.1.0"
)

# API Routers
app.include_router(router_auth.router)
app.include_router(router_plans.router)
app.include_router(router_subscriptions.router)
app.include_router(router_payments.router)
app.include_router(router_webhooks.router)

# UI/Template Routers
app.include_router(router_dashboard.router)
app.include_router(router_portal.router)
app.include_router(developer_routes.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Verify database connection
        db.execute(text("SELECT 1;"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({str(e)})"
        
    return {
        "status": "healthy",
        "database": db_status
    }
