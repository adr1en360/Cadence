from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.services.billing_service import BillingService
from app.core.nomba_client import nomba_client

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
        "plan_name": sub.plan.name,
        "plan_amount": float(sub.plan.amount),
        "plan_interval": int(sub.plan.interval_days),
        "status": sub.status,
        "token_key": sub.token_key,
        "created_at": sub.created_at.strftime('%Y-%m-%d'),
        "period_end": sub.current_period_end.strftime('%Y-%m-%d %H:%M')
    }
    
    return templates.TemplateResponse(request=request, name="portal.html", context={
        "subscription": subscription_data
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
            status="pending"
        )
        db.add(payment)
        db.commit()

        # Build callback redirect URL back to portal page with token preserved
        callback_url = f"http://localhost:8000/portal/{sub.id}?token={token}"
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize card authorization: {str(e)}"
        )

@router.post("/api/portal/{sub_id}/cancel")
def cancel_portal_subscription(sub_id: str, token: str = None, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    validate_portal_token(sub, token)
        
    try:
        BillingService.cancel_subscription(db, sub)
        return {"status": "cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
