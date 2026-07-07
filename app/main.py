from fastapi import FastAPI, Depends, Response
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import os

from app.core.database import get_db
from app.api import router_auth, router_plans, router_subscriptions, router_payments, router_webhooks, router_dashboard, router_portal, developer_routes

app = FastAPI(
    title="Cadence Subscription Engine",
    description="Managed subscription billing engine built on Nomba's payment APIs",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

@app.get("/favicon.ico")
def get_favicon_ico():
    return RedirectResponse(url="/favicon.svg")

@app.get("/favicon.svg")
def get_favicon():
    svg_content = """<svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#FF6B00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 17L12 22L22 17M2 12L12 17L22 12" stroke="#FF6B00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""
    return Response(content=svg_content, media_type="image/svg+xml")

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

def get_public_openapi_spec():
    """Build a temporary FastAPI instance and generate public-only schema."""
    public_app = FastAPI(
        title="Cadence Public Developer API",
        description="Public API endpoints for creating billing plans and enrolling subscribers on the Cadence engine.",
        version="0.1.0"
    )
    public_app.include_router(router_plans.router)
    public_app.include_router(router_subscriptions.router)
    public_app.include_router(router_payments.router)
    
    return get_openapi(
        title=public_app.title,
        version=public_app.version,
        openapi_version=public_app.openapi_version,
        description=public_app.description,
        routes=public_app.routes,
    )

@app.on_event("startup")
def verify_secret_key():
    """Verify that SECRET_KEY is not the default value in production environment."""
    from app.core.config import settings
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production" and settings.SECRET_KEY == "cadence-dev-secret-change-in-production":
        raise RuntimeError("Insecure SECRET_KEY fallback is not allowed in production environment.")

@app.on_event("startup")
def save_public_openapi_schema():
    """Cache the public OpenAPI schema to a static JSON file on startup."""
    os.makedirs("static", exist_ok=True)
    schema = get_public_openapi_spec()
    with open("static/openapi.json", "w") as f:
        json.dump(schema, f, indent=2)

@app.get("/openapi.json")
def get_public_openapi():
    """Serves the clean, developer-facing public OpenAPI spec."""
    return get_public_openapi_spec()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Verify database connection
        db.execute(text("SELECT 1;"))
        db_status = "connected"
    except Exception as e:
        print(f"[HEALTH] Database connection failed: {type(e).__name__} - {str(e)}")
        db_status = "disconnected"
        
    return {
        "status": "healthy",
        "database": db_status
    }
