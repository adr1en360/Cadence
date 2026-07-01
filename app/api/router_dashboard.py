from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.core.database import get_db
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant, APIKey
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
def get_stats(
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    active_query = db.query(Subscription).filter(
        Subscription.merchant_id == merchant.id,
        Subscription.status == "active"
    )
    if api_key_id:
        active_query = active_query.join(Plan).filter(Plan.api_key_id == api_key_id)
    active_count = active_query.count()
    
    # Calculate MRR (sum of amounts of active subscription plans)
    mrr_query = db.query(func.sum(Plan.amount)).join(Subscription).filter(
        Subscription.merchant_id == merchant.id,
        Subscription.status == "active"
    )
    if api_key_id:
        mrr_query = mrr_query.filter(Plan.api_key_id == api_key_id)
    mrr_result = mrr_query.scalar()
    mrr = float(mrr_result) if mrr_result else 0.0
    
    # Calculate total processed successful payments
    total_query = db.query(func.sum(Payment.amount)).filter(
        Payment.merchant_id == merchant.id,
        Payment.status == "succeeded"
    )
    if api_key_id:
        total_query = total_query.join(Subscription).join(Plan).filter(Plan.api_key_id == api_key_id)
    total_result = total_query.scalar()
    total_payments = float(total_result) if total_result else 0.0
    
    return {
        "active_subscribers": active_count,
        "mrr": mrr,
        "total_payments": total_payments
    }

@router.get("/api/dashboard/plans")
def list_dashboard_plans(
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = db.query(Plan).filter(Plan.merchant_id == merchant.id, Plan.is_active == True)
    if api_key_id:
        query = query.filter(Plan.api_key_id == api_key_id)
    plans = query.all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "amount": float(p.amount),
            "interval_days": int(p.interval_days),
            "trial_days": int(p.trial_days),
            "api_key_label": p.api_key.label if p.api_key else "Direct / No Key"
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
        trial_days=payload.get("trial_days", 0),
        api_key_id=payload.get("api_key_id")
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
def list_dashboard_subscriptions(
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = db.query(Subscription).filter(Subscription.merchant_id == merchant.id)
    if api_key_id:
        query = query.join(Plan).filter(Plan.api_key_id == api_key_id)
    subs = query.all()
    return [
        {
            "id": s.id,
            "customer_name": s.customer_name,
            "customer_email": s.customer_email,
            "status": s.status,
            "plan_name": s.plan.name,
            "plan_amount": float(s.plan.amount),
            "plan_currency": s.plan.currency,
            "api_key_label": s.plan.api_key.label if s.plan.api_key else "Direct / No Key",
            "period_start": s.current_period_start.isoformat(),
            "period_end": s.current_period_end.isoformat()
        } for s in subs
    ]

@router.get("/api/dashboard/wallet-balance")
async def get_wallet_balance_route(
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    sub_account_id = None
    if api_key_id:
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id, APIKey.merchant_id == merchant.id).first()
        if api_key:
            sub_account_id = api_key.nomba_sub_account_id
            
    from app.core.nomba_client import nomba_client
    try:
        balance_data = await nomba_client.get_wallet_balance(sub_account_id=sub_account_id)
        return {
            "amount": float(balance_data["amount"]),
            "currency": balance_data["currency"]
        }
    except Exception as e:
        return {
            "amount": 0.0,
            "currency": "NGN",
            "error": str(e)
        }
