from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment

router = APIRouter(tags=["Merchant Dashboard"])
templates = Jinja2Templates(directory="templates")

# Helper to retrieve JWT token from cookies
def get_merchant_from_cookie(request: Request, db: Session = Depends(get_db)) -> Merchant:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=302, detail="Not authenticated")
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=302, detail="Session expired")
    merchant_email = payload.get("sub")
    merchant = db.query(Merchant).filter(Merchant.email == merchant_email).first()
    if not merchant:
        raise HTTPException(status_code=302, detail="Merchant not found")
    return merchant

# UI Page Routers
@router.get("/")
def landing_page(request: Request):
    # If already logged in, redirect to dashboard
    if request.cookies.get("access_token"):
        return Response(headers={"Location": "/dashboard"}, status_code=302)
    return templates.TemplateResponse(request=request, name="landing.html")

@router.get("/login")
def login_page(request: Request):
    # If already logged in, redirect to dashboard
    if request.cookies.get("access_token"):
        return Response(headers={"Location": "/dashboard"}, status_code=302)
    return templates.TemplateResponse(request=request, name="login.html")

@router.get("/register")
def register_page(request: Request):
    if request.cookies.get("access_token"):
        return Response(headers={"Location": "/dashboard"}, status_code=302)
    return templates.TemplateResponse(request=request, name="register.html")

@router.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    try:
        merchant = get_merchant_from_cookie(request, db)
    except HTTPException:
        return Response(headers={"Location": "/login"}, status_code=302)
        
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"merchant": merchant})

# JSON Data API Routers for UI Dashboard
@router.get("/api/dashboard/stats")
def get_stats(merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)):
    active_count = db.query(Subscription).filter(
        Subscription.merchant_id == merchant.id,
        Subscription.status == "active"
    ).count()
    
    # Calculate MRR (sum of amounts of active subscription plans)
    mrr_result = db.query(func.sum(Plan.amount)).join(Subscription).filter(
        Subscription.merchant_id == merchant.id,
        Subscription.status == "active"
    ).scalar()
    mrr = float(mrr_result) if mrr_result else 0.0
    
    # Calculate total processed successful payments
    total_result = db.query(func.sum(Payment.amount)).filter(
        Payment.merchant_id == merchant.id,
        Payment.status == "succeeded"
    ).scalar()
    total_payments = float(total_result) if total_result else 0.0
    
    return {
        "active_subscribers": active_count,
        "mrr": mrr,
        "total_payments": total_payments
    }

@router.get("/api/dashboard/plans")
def list_dashboard_plans(merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.merchant_id == merchant.id, Plan.is_active == True).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "amount": float(p.amount),
            "interval_days": int(p.interval_days),
            "trial_days": int(p.trial_days)
        } for p in plans
    ]

@router.post("/api/dashboard/plans")
def create_dashboard_plan(
    payload: dict,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    plan = Plan(
        merchant_id=merchant.id,
        name=payload["name"],
        amount=payload["amount"],
        interval_days=payload["interval_days"],
        trial_days=payload.get("trial_days", 0)
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/api/dashboard/plans/{plan_id}")
def delete_dashboard_plan(
    plan_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.merchant_id == merchant.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    db.add(plan)
    db.commit()
    return {"status": "archived"}

@router.get("/api/dashboard/subscriptions")
def list_dashboard_subscriptions(merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)):
    subs = db.query(Subscription).filter(Subscription.merchant_id == merchant.id).all()
    return [
        {
            "id": s.id,
            "customer_name": s.customer_name,
            "customer_email": s.customer_email,
            "status": s.status,
            "plan_name": s.plan.name,
            "period_start": s.current_period_start.isoformat(),
            "period_end": s.current_period_end.isoformat()
        } for s in subs
    ]
