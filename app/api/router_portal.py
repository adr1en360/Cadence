from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.services.billing_service import BillingService
from app.core.nomba_client import nomba_client
from app.core.config import settings

router = APIRouter(tags=["Subscriber Portal"])
templates = Jinja2Templates(directory="templates")

def validate_portal_token(sub: Subscription, token: str) -> None:
    """Helper to validate subscription portal token and expiration."""
    if not sub.portal_token or sub.portal_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic Link is invalid or has expired."
        )
    if not sub.portal_token_expires_at or datetime.utcnow() > sub.portal_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic Link has expired. Please request a new link from your merchant."
        )

@router.get("/portal/{sub_id}")
def portal_page(sub_id: str, request: Request, token: str = None, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        return templates.TemplateResponse(request=request, name="base.html", context={
            "content_override": "<h3>Subscription Not Found</h3>"
        })
        
    try:
        validate_portal_token(sub, token)
    except HTTPException as e:
        return templates.TemplateResponse(request=request, name="base.html", context={
            "content_override": f"<h3>Access Denied</h3><p>{e.detail}</p>"
        })
        
    subscription_data = {
        "id": sub.id,
        "customer_name": sub.customer_name,
        "customer_email": sub.customer_email,
        "merchant_name": sub.project.name, # Use Project name as provider name
        "plan_id": sub.plan_id,
        "plan_name": sub.plan.name,
        "plan_amount": float(sub.plan.amount),
        "plan_interval": int(sub.plan.interval_days),
        "status": sub.status,
        "token_key": sub.token_key,
        "created_at": sub.created_at.strftime('%Y-%m-%d'),
        "period_end": sub.current_period_end.strftime('%Y-%m-%d %H:%M'),
        "cancel_at_period_end": sub.cancel_at_period_end,
        "pending_plan_id": sub.pending_plan_id,
        "pending_plan_name": sub.pending_plan.name if sub.pending_plan_id and sub.pending_plan else None
    }
    
    from app.models.plan import Plan
    available_plans = db.query(Plan).filter(
        Plan.project_id == sub.project_id,
        Plan.is_active == True
    ).all()
    
    plans_data = [{
        "id": p.id,
        "name": p.name,
        "amount": float(p.amount),
        "interval_days": int(p.interval_days)
    } for p in available_plans]
    
    return templates.TemplateResponse(request=request, name="portal.html", context={
        "subscription": subscription_data,
        "available_plans": plans_data
    })

@router.post("/api/portal/{sub_id}/update-card")
async def update_card(sub_id: str, token: str = None, db: Session = Depends(get_db)):
    """Initialize a small tokenization auth transaction to capture the customer's card token."""
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    validate_portal_token(sub, token)
        
    order_ref = f"cadence_token_{sub.id[:8]}_{int(datetime.utcnow().timestamp())}"
    charge_amount = 100.00
    
    try:
        # Create pending Payment record for tracking
        payment = Payment(
            subscription_id=sub.id,
            project_id=sub.project_id,
            amount=charge_amount,
            currency="NGN",
            nomba_order_ref=order_ref,
            status="pending",
            idempotency_key=f"idemp_{sub.id}_{order_ref}"
        )
        db.add(payment)
        db.commit()

        # Build callback redirect URL back to portal page with token preserved
        callback_url = f"{settings.BASE_URL}/portal/{sub.id}?token={token}"
        
        checkout_resp = await nomba_client.create_checkout_order(
            db=db,
            project=sub.project,
            order_ref=order_ref,
            amount=charge_amount,
            customer_email=sub.customer_email,
            callback_url=callback_url,
            currency="NGN"
        )
        
        checkout_link = checkout_resp.get("data", {}).get("checkoutLink") or checkout_resp.get("checkoutLink")
        if not checkout_link:
            raise RuntimeError("Nomba failed to generate card authorization checkoutLink")
            
        return {"checkout_link": checkout_link}
        
    except Exception as e:
        print(f"[PORTAL] Failed to initialize card authorization for sub {sub.id}: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize card authorization"
        )

@router.post("/api/portal/{sub_id}/cancel")
def cancel_portal_subscription(sub_id: str, token: str = None, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    validate_portal_token(sub, token)
    
    if sub.status == "cancelled":
        raise HTTPException(status_code=400, detail="Subscription is already cancelled")
        
    sub.cancel_at_period_end = True
    db.add(sub)
    db.commit()
    return {"status": "cancel_at_period_end_set"}

@router.post("/api/portal/{sub_id}/resume")
def resume_portal_subscription(sub_id: str, token: str = None, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    validate_portal_token(sub, token)
    
    if sub.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot resume a permanently cancelled subscription")
        
    sub.cancel_at_period_end = False
    db.add(sub)
    db.commit()
    return {"status": "resumed"}

@router.post("/api/portal/{sub_id}/change-plan")
def portal_change_plan(sub_id: str, token: str = None, plan_id: str = None, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    validate_portal_token(sub, token)
    
    from app.models.plan import Plan
    if not plan_id:
        # If no plan_id is provided, treat it as clearing any pending changes
        sub.pending_plan_id = None
        db.add(sub)
        db.commit()
        return {"status": "cleared", "message": "Pending plan switch cancelled"}
        
    new_plan = db.query(Plan).filter(Plan.id == plan_id, Plan.project_id == sub.project_id, Plan.is_active == True).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Selected plan not found or inactive")
        
    if plan_id == sub.plan_id:
        sub.pending_plan_id = None
        db.add(sub)
        db.commit()
        return {"status": "cleared", "message": "Pending plan switch cancelled"}
        
    sub.pending_plan_id = plan_id
    db.add(sub)
    db.commit()
    return {
        "status": "scheduled",
        "pending_plan_name": new_plan.name,
        "message": f"Your plan will switch to {new_plan.name} at the end of the current billing cycle."
    }
