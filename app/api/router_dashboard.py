from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
from typing import List, Optional
from app.core.database import get_db
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant, APIKey
from app.models.project import Project
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.event import Event
from app.core.config import settings

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
    if request.cookies.get("access_token"):
        return Response(headers={"Location": "/dashboard"}, status_code=302)
    return templates.TemplateResponse(request=request, name="landing.html")

@router.get("/login")
def login_page(request: Request):
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

# JSON Data API Routers for Projects
@router.get("/api/dashboard/projects")
def list_projects(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    projects = db.query(Project).filter(Project.merchant_id == merchant.id).all()
    has_updates = False
    for p in projects:
        if not p.webhook_secret:
            import secrets
            p.webhook_secret = f"whsec_{secrets.token_hex(16)}"
            db.add(p)
            has_updates = True
    if has_updates:
        db.commit()
    return [
        {
            "id": p.id,
            "name": p.name,
            "nomba_client_id": p.nomba_client_id,
            "nomba_account_id": p.nomba_account_id,
            "nomba_client_secret_configured": p.nomba_client_secret_encrypted is not None,
            "webhook_url": p.webhook_url,
            "webhook_secret": p.webhook_secret,
            "created_at": p.created_at.isoformat()
        } for p in projects
    ]

@router.post("/api/dashboard/projects")
def create_project(
    payload: dict,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    name = payload.get("name")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Project name is required")
        
    import secrets
    project = Project(
        merchant_id=merchant.id,
        name=name.strip(),
        webhook_secret=f"whsec_{secrets.token_hex(16)}"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at.isoformat()
    }

@router.post("/api/dashboard/projects/{project_id}/settings")
def update_project_settings(
    project_id: str,
    payload: dict,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Update Nomba credentials (only if provided and non-empty)
    nomba_client_id = (payload.get("nomba_client_id") or "").strip()
    nomba_client_secret = (payload.get("nomba_client_secret") or "").strip()
    nomba_account_id = (payload.get("nomba_account_id") or "").strip()
    
    if nomba_client_id:
        project.nomba_client_id = nomba_client_id
    if nomba_client_secret and nomba_client_secret != "********":
        from app.core.security import encrypt_credential
        project.nomba_client_secret_encrypted = encrypt_credential(nomba_client_secret)
    if nomba_account_id:
        project.nomba_account_id = nomba_account_id
    
    # Always update webhook_url (can be set or cleared)
    webhook_url = (payload.get("webhook_url") or "").strip()
    project.webhook_url = webhook_url if webhook_url else None
        
    db.add(project)
    db.commit()
    return {"message": "Project settings updated successfully"}

# JSON Data API Routers for UI Dashboard (scoped to Project)
@router.get("/api/dashboard/stats")
def get_stats(
    project_id: str,
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    active_query = db.query(Subscription).filter(
        Subscription.project_id == project.id,
        Subscription.status == "active"
    )
    if api_key_id:
        active_query = active_query.join(Plan, Subscription.plan_id == Plan.id).filter(Plan.api_key_id == api_key_id)
    active_count = active_query.count()
    
    # Calculate MRR
    mrr_query = db.query(func.sum(Plan.amount)).join(Subscription, Subscription.plan_id == Plan.id).filter(
        Subscription.project_id == project.id,
        Subscription.status == "active"
    )
    if api_key_id:
        mrr_query = mrr_query.filter(Plan.api_key_id == api_key_id)
    mrr_result = mrr_query.scalar()
    mrr = float(mrr_result) if mrr_result else 0.0
    
    # Calculate total processed payments
    total_query = db.query(func.sum(Payment.amount)).filter(
        Payment.project_id == project.id,
        Payment.status == "succeeded"
    )
    if api_key_id:
        total_query = total_query.join(Subscription).join(Plan, Subscription.plan_id == Plan.id).filter(Plan.api_key_id == api_key_id)
    total_result = total_query.scalar()
    total_payments = float(total_result) if total_result else 0.0
    
    return {
        "active_subscribers": active_count,
        "mrr": mrr,
        "total_payments": total_payments
    }

@router.get("/api/dashboard/plans")
def list_dashboard_plans(
    project_id: str,
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    query = db.query(Plan).filter(Plan.project_id == project.id, Plan.is_active == True)
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
    project_id = payload.get("project_id")
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    plan = Plan(
        project_id=project.id,
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
    # Verify project belongs to merchant
    plan = db.query(Plan).join(Project).filter(Plan.id == plan_id, Project.merchant_id == merchant.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    db.add(plan)
    db.commit()
    return {"status": "archived"}

@router.get("/api/dashboard/subscriptions")
def list_dashboard_subscriptions(
    project_id: str,
    api_key_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    query = db.query(Subscription).filter(Subscription.project_id == project.id)
    if api_key_id:
        query = query.join(Plan, Subscription.plan_id == Plan.id).filter(Plan.api_key_id == api_key_id)
        
    if status:
        query = query.filter(Subscription.status == status)
        
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Subscription.customer_name.ilike(search_filter)) | 
            (Subscription.customer_email.ilike(search_filter))
        )
        
    if start_date:
        try:
            if len(start_date) == 10:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                parsed_start = datetime.fromisoformat(start_date)
            query = query.filter(Subscription.created_at >= parsed_start)
        except Exception:
            pass
            
    if end_date:
        try:
            if len(end_date) == 10:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            else:
                parsed_end = datetime.fromisoformat(end_date)
            query = query.filter(Subscription.created_at <= parsed_end)
        except Exception:
            pass
            
    subs = query.order_by(Subscription.created_at.desc()).all()
    
    data = []
    for s in subs:
        # Load all payments and events associated with this subscription
        payments = db.query(Payment).filter(Payment.subscription_id == s.id).order_by(Payment.created_at.desc()).all()
        events = db.query(Event).filter(Event.subscription_id == s.id).order_by(Event.created_at.desc()).all()
        
        data.append({
            "id": s.id,
            "customer_name": s.customer_name,
            "customer_email": s.customer_email,
            "status": s.status,
            "plan_name": s.plan.name,
            "plan_amount": float(s.plan.amount),
            "plan_currency": s.plan.currency,
            "api_key_label": s.plan.api_key.label if s.plan.api_key else "Direct / No Key",
            "period_start": s.current_period_start.isoformat(),
            "period_end": s.current_period_end.isoformat(),
            "pending_plan_id": s.pending_plan_id,
            "pending_plan_name": s.pending_plan.name if s.pending_plan_id and s.pending_plan else None,
            "payments": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "status": p.status,
                    "nomba_order_ref": p.nomba_order_ref,
                    "nomba_transaction_id": p.nomba_transaction_id or "",
                    "created_at": p.created_at.isoformat()
                } for p in payments
            ],
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "created_at": e.created_at.isoformat(),
                    "data": json.loads(e.data_json) if e.data_json else {}
                } for e in events
            ]
        })
    return data

@router.get("/api/dashboard/wallet-balance")
async def get_wallet_balance_route(
    project_id: str,
    api_key_id: Optional[str] = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    sub_account_id = None
    if api_key_id:
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id, APIKey.project_id == project.id).first()
        if api_key:
            sub_account_id = api_key.nomba_sub_account_id
            
    from app.core.nomba_client import nomba_client
    try:
        balance_data = await nomba_client.get_wallet_balance(db=db, project=project, sub_account_id=sub_account_id)
        return {
            "amount": float(balance_data["amount"]),
            "currency": balance_data["currency"]
        }
    except Exception as e:
        print(f"[DASHBOARD] Wallet balance check failed for project {project_id}: {type(e).__name__} - {str(e)}")
        return {
            "amount": 0.0,
            "currency": "NGN",
            "error": "Failed to retrieve wallet balance"
        }

@router.post("/api/dashboard/subscriptions/{sub_id}/portal-link")
def dashboard_generate_portal_link(
    sub_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).join(Project).filter(Subscription.id == sub_id, Project.merchant_id == merchant.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    import secrets
    from datetime import datetime, timedelta
    token = secrets.token_urlsafe(32)
    sub.portal_token = token
    sub.portal_token_expires_at = datetime.utcnow() + timedelta(hours=2)
    db.add(sub)
    db.commit()
    
    portal_url = f"{settings.BASE_URL}/portal/{sub.id}?token={token}"
    return {
        "portal_url": portal_url,
        "expires_at": sub.portal_token_expires_at.isoformat()
    }

class DashboardChangePlanRequest(BaseModel):
    plan_id: Optional[str] = None

@router.post("/api/dashboard/subscriptions/{sub_id}/change-plan")
def dashboard_change_plan(
    sub_id: str,
    payload: DashboardChangePlanRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).join(Project).filter(Subscription.id == sub_id, Project.merchant_id == merchant.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    if not payload.plan_id:
        sub.pending_plan_id = None
        db.add(sub)
        db.commit()
        return {"status": "cleared", "message": "Pending plan switch cancelled"}
        
    new_plan = db.query(Plan).filter(Plan.id == payload.plan_id, Plan.project_id == sub.project_id, Plan.is_active == True).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Selected plan not found or inactive")
        
    if payload.plan_id == sub.plan_id:
        sub.pending_plan_id = None
        db.add(sub)
        db.commit()
        return {"status": "cleared", "message": "Pending plan switch cancelled"}
        
    sub.pending_plan_id = payload.plan_id
    db.add(sub)
    db.commit()
    return {
        "status": "scheduled",
        "pending_plan_name": new_plan.name,
        "message": f"Subscription plan switch to {new_plan.name} scheduled for end of period."
    }

@router.post("/api/dashboard/payments/{payment_id}/refund")
async def dashboard_refund_payment(
    payment_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).join(Project).filter(Payment.id == payment_id, Project.merchant_id == merchant.id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
        
    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail="Only succeeded payments can be refunded")
        
    if not payment.nomba_transaction_id:
        raise HTTPException(status_code=400, detail="Payment lacks a transaction ID")
        
    try:
        from app.core.nomba_client import nomba_client
        resp = await nomba_client.refund_transaction(
            db=db,
            project=payment.project,
            transaction_id=payment.nomba_transaction_id,
            amount=float(payment.amount)
        )
        
        code = resp.get("code")
        status_val = resp.get("status")
        
        if code == "00" or status_val == "SUCCESS" or resp.get("data", {}).get("status") == "SUCCESS":
            payment.status = "refunded"
            db.add(payment)
            
            # Log refund event
            event = Event(
                project_id=payment.project_id,
                subscription_id=payment.subscription_id,
                event_type="payment.refunded",
                data_json=json.dumps({
                    "payment_id": payment.id,
                    "nomba_transaction_id": payment.nomba_transaction_id,
                    "amount": float(payment.amount),
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            db.add(event)
            
            # Dispatch webhook to merchant
            from app.services.webhook_dispatcher import dispatch_webhook
            dispatch_webhook(
                project=payment.project,
                event_type="payment.refunded",
                data={
                    "payment_id": payment.id,
                    "nomba_transaction_id": payment.nomba_transaction_id,
                    "amount": float(payment.amount),
                    "customer_email": payment.subscription.customer_email if payment.subscription else None
                }
            )
            
            db.commit()
            return {"status": "refunded"}
        else:
            raise RuntimeError(f"Nomba refund rejected: {resp}")
    except Exception as e:
        print(f"[DASHBOARD] Refund failed for payment {payment_id}: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail="Refund processing failed")
