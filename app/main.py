from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

app = FastAPI(
    title="Cadence Subscription Engine",
    description="Managed subscription billing engine built on Nomba's payment APIs",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {
        "name": "Cadence Subscription Engine API",
        "status": "operational"
    }

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
