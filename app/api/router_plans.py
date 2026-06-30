from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.deps import get_merchant_by_api_key
from app.models.merchant import Merchant
from app.models.plan import Plan

router = APIRouter(prefix="/api/plans", tags=["Plans"])

class PlanCreateRequest(BaseModel):
    name: str
    amount: float = Field(gt=0, description="Amount to charge per interval")
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    interval_days: int = Field(gt=0, description="Plan billing interval in days")
    trial_days: Optional[int] = Field(default=0, ge=0)

class PlanResponse(BaseModel):
    id: str
    name: str
    amount: float
    currency: str
    interval_days: int
    trial_days: int
    is_active: bool

    class Config:
        from_attributes = True

@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreateRequest,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    plan = Plan(
        merchant_id=merchant.id,
        name=payload.name,
        amount=payload.amount,
        currency=payload.currency.upper(),
        interval_days=payload.interval_days,
        trial_days=payload.trial_days
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.get("", response_model=List[PlanResponse])
def list_plans(
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    plans = db.query(Plan).filter(Plan.merchant_id == merchant.id, Plan.is_active == True).all()
    return plans

@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: str,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.merchant_id == merchant.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: str,
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.merchant_id == merchant.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
        
    # Soft delete (deactivate) plan
    plan.is_active = False
    db.add(plan)
    db.commit()
    return
