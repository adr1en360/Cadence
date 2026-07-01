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
        # Request refund from Nomba
        resp = await nomba_client.refund_transaction(
            db=db,
            project=project,
            transaction_id=payment.nomba_transaction_id,
            amount=float(payment.amount)
        )
        
        # Verify response code
        code = resp.get("code")
        status_val = resp.get("status")
        
        # Depending on sandbox/production structure, success is code "00" or status SUCCESS
        if code == "00" or status_val == "SUCCESS" or resp.get("data", {}).get("status") == "SUCCESS":
            payment.status = "refunded"
            db.add(payment)
            
            # Log refund event
            event = Event(
                project_id=project.id,
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
            db.commit()
            
            return {"message": "Payment refunded successfully", "status": "refunded"}
        else:
            raise RuntimeError(f"Nomba refund rejected: {resp}")
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund via Nomba: {str(e)}"
        )
