from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_nomba_webhook
from app.models.project import Project
from app.services.billing_service import BillingService
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/nomba")
async def handle_nomba_webhook(request: Request, db: Session = Depends(get_db)):
    # 1. Parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")
        
    # 2. Extract signature headers
    headers = dict(request.headers)
    
    # Extract merchant parent account ID from payload
    data = payload.get("data", {})
    merchant_data = data.get("merchant", {})
    user_id = merchant_data.get("userId")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing merchant userId in payload"
        )
        
    # 3. Find the Project owning this account ID
    project = db.query(Project).filter(Project.nomba_account_id == user_id).first()
    if not project:
        # Fallback: check if we have a project configured with this ID in default settings
        from app.core.config import settings
        if settings.NOMBA_ACCOUNT_ID == user_id:
            project = db.query(Project).first()
            
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project owning this Nomba account not found in Cadence"
        )
        
    # Use the configured webhook signing key as the HMAC key
    from app.core.config import settings
    secret_key = settings.NOMBA_WEBHOOK_SECRET
    
    # 4. Verify signature
    is_valid = verify_nomba_webhook(payload, headers, secret_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signature verification failed"
        )
        
    # 5. Route webhook event to billing service
    event_type = payload.get("event_type")
    order = data.get("order", {})
    order_ref = order.get("orderReference")
    transaction = data.get("transaction", {})
    transaction_id = transaction.get("transactionId")
    
    # Nomba token key resides under data.tokenKey or in webhook payload
    token_key = data.get("tokenKey")
    
    # Event Type Mapping:
    # Nomba's underscore events (e.g. `payment_success`, `payment_failed`)
    # are mapped to Cadence's internal dot-notation events (e.g. `payment.succeeded`, `payment.failed`)
    # inside the BillingService processing methods.
    if event_type == "payment_success" and order_ref:
        BillingService.process_payment_success(
            db=db,
            nomba_order_ref=order_ref,
            transaction_id=transaction_id,
            token_key=token_key
        )
        print(f"[WEBHOOK] Successfully processed payment_success for ref: {order_ref}")
        
    elif event_type == "payment_failed" and order_ref:
        BillingService.process_payment_failure(
            db=db,
            nomba_order_ref=order_ref
        )
        print(f"[WEBHOOK] Successfully processed payment_failed for ref: {order_ref}")
        
    return {"status": "received"}

@router.post("/test-success")
def trigger_test_success_webhook(payload: dict, merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)):
    """Sandbox endpoint to simulate a successful payment webhook for a given order reference."""
    order_ref = payload.get("order_ref")
    transaction_id = payload.get("transaction_id", "test_txn_12345")
    token_key = payload.get("token_key", "test_token_key_abcde")
    
    if not order_ref:
        raise HTTPException(status_code=400, detail="order_ref is required")
        
    try:
        BillingService.process_payment_success(
            db=db,
            nomba_order_ref=order_ref,
            transaction_id=transaction_id,
            token_key=token_key
        )
        return {"status": "success", "message": "Simulation success webhook triggered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/test-failed")
def trigger_test_failed_webhook(payload: dict, merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)):
    """Sandbox endpoint to simulate a failed payment webhook for a given order reference."""
    order_ref = payload.get("order_ref")
    
    if not order_ref:
        raise HTTPException(status_code=400, detail="order_ref is required")
        
    try:
        BillingService.process_payment_failure(
            db=db,
            nomba_order_ref=order_ref
        )
        return {"status": "success", "message": "Simulation failed webhook triggered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
