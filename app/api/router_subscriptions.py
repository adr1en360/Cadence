from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.deps import get_merchant_by_api_key
from app.models.merchant import Merchant
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.services.billing_service import BillingService

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

class SubscriptionCreateRequest(BaseModel):
    plan_id: str
    customer_email: EmailStr
    customer_name: Optional[str] = None
    callback_url: str  # Redirect destination after payment checkout completes

class SubscriptionResponse(BaseModel):
    id: str
    plan_id: str
    customer_email: str
    customer_name: Optional[str]
    status: str
    current_period_start: str
    current_period_end: str
    checkout_link: Optional[str] = None

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreateRequest,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == payload.plan_id, Plan.merchant_id == merchant.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription Plan not found"
        )
        
    try:
        subscription, checkout_link = await BillingService.create_subscription(
            db=db,
            merchant=merchant,
            plan=plan,
            customer_email=payload.customer_email,
            customer_name=payload.customer_name,
            callback_url=payload.callback_url
        )
        
        return {
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "customer_email": subscription.customer_email,
            "customer_name": subscription.customer_name,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "checkout_link": checkout_link
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize subscription checkout: {str(e)}"
        )

@router.get("")
def list_subscriptions(
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    subs = db.query(Subscription).filter(Subscription.merchant_id == merchant.id).all()
    return [
        {
            "id": s.id,
            "plan_id": s.plan_id,
            "customer_email": s.customer_email,
            "customer_name": s.customer_name,
            "status": s.status,
            "current_period_start": s.current_period_start.isoformat(),
            "current_period_end": s.current_period_end.isoformat()
        } for s in subs
    ]

@router.get("/{sub_id}")
def get_subscription(
    sub_id: str,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.merchant_id == merchant.id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
        
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "customer_email": sub.customer_email,
        "customer_name": sub.customer_name,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat(),
        "token_key": sub.token_key,
        "retry_count": sub.retry_count,
        "next_retry_at": sub.next_retry_at.isoformat() if sub.next_retry_at else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat()
    }

@router.post("/{sub_id}/cancel")
def cancel_subscription(
    sub_id: str,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.merchant_id == merchant.id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
        
    try:
        BillingService.cancel_subscription(db, sub)
        return {"message": "Subscription cancelled successfully", "status": sub.status}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
