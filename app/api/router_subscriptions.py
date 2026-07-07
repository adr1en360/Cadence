from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
from app.core.database import get_db
from app.api.deps import get_project_by_api_key
from app.models.project import Project
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.services.billing_service import BillingService, VALID_TRANSITIONS
from app.core.config import settings

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

class SubscriptionCreateRequest(BaseModel):
    plan_id: str
    customer_email: EmailStr
    customer_name: Optional[str] = None
    callback_url: str  # Redirect destination after payment checkout completes

class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = False

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
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == payload.plan_id, Plan.project_id == project.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription Plan not found"
        )
        
    existing_sub = db.query(Subscription).filter(
        Subscription.project_id == project.id,
        Subscription.customer_email == payload.customer_email,
        Subscription.status.notin_(["cancelled", "expired", "pending_payment"])
    ).first()
    if existing_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already has an active subscription in this project"
        )
        
    try:
        subscription, checkout_link, order_ref = await BillingService.create_subscription(
            db=db,
            project=project,
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
            "checkout_link": checkout_link,
            "nomba_order_ref": order_ref
        }
    except Exception as e:
        print(f"[SUBSCRIPTIONS] Failed to initialize checkout for {payload.customer_email}: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize subscription checkout"
        )

@router.get("")
def list_subscriptions(
    status_filter: Optional[str] = None,
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    query = db.query(Subscription).filter(Subscription.project_id == project.id)
    if status_filter:
        if status_filter not in VALID_TRANSITIONS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status filter")
        query = query.filter(Subscription.status == status_filter)
    subs = query.all()
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
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.project_id == project.id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
        
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "plan_name": sub.plan.name if sub.plan else "N/A",
        "plan_amount": float(sub.plan.amount) if sub.plan else 0.0,
        "customer_email": sub.customer_email,
        "customer_name": sub.customer_name,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat(),
        "period_end": sub.current_period_end.isoformat(),
        "token_key": sub.token_key,
        "retry_count": sub.retry_count,
        "next_retry_at": sub.next_retry_at.isoformat() if sub.next_retry_at else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat(),
        "cancel_at_period_end": sub.cancel_at_period_end
    }

@router.post("/{sub_id}/cancel")
def cancel_subscription(
    sub_id: str,
    payload: CancelSubscriptionRequest = None,
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    if payload is None:
        payload = CancelSubscriptionRequest()
        
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.project_id == project.id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
        
    try:
        if payload.cancel_at_period_end:
            sub.cancel_at_period_end = True
            db.commit()
            return {"message": "Subscription scheduled to cancel at period end", "status": sub.status, "cancel_at_period_end": True}
        else:
            BillingService.cancel_subscription(db, sub)
            return {"message": "Subscription cancelled successfully", "status": sub.status, "cancel_at_period_end": False}
    except ValueError as e:
        print(f"[SUBSCRIPTIONS] Failed to cancel subscription {sub_id}: ValueError - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription cannot be cancelled from its current state"
        )
@router.post("/{sub_id}/portal-link")
def generate_portal_link(
    sub_id: str,
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.project_id == project.id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
        
    from app.services.billing_service import BillingService
    from app.core.config import settings
    return BillingService.generate_portal_link(db, sub, settings.BASE_URL)
