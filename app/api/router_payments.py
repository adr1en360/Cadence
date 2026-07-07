from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from datetime import datetime
from app.core.database import get_db
from app.api.deps import get_project_by_api_key
from app.models.project import Project
from app.models.payment import Payment
from app.models.event import Event
from app.core.nomba_client import nomba_client

router = APIRouter(prefix="/api/payments", tags=["Payments"])

@router.post("/{payment_id}/refund", status_code=status.HTTP_200_OK)
async def refund_payment(
    payment_id: str,
    project: Project = Depends(get_project_by_api_key),
    db: Session = Depends(get_db)
):
    """Refund a successful payment transaction."""
    from app.services.billing_service import BillingService
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.project_id == project.id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found"
        )
        
    if payment.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only succeeded payments can be refunded. Current status: {payment.status}"
        )
        
    if not payment.nomba_transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment cannot be refunded because it lacks a Nomba transaction ID."
        )

    try:
        await BillingService.refund_payment(db, payment, project)
        return {"message": "Payment refunded successfully", "status": "refunded"}
    except Exception as e:
        print(f"[PAYMENTS] Refund failed for payment {payment.id}: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund via Nomba"
        )
