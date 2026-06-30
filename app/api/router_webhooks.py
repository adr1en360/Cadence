from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_nomba_webhook
from app.models.merchant import Merchant
from app.services.billing_service import BillingService

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
        
    # 3. Find the Merchant owning this account ID
    merchant = db.query(Merchant).filter(Merchant.nomba_account_id == user_id).first()
    if not merchant:
        # Fallback: check if we have a merchant configured with this ID in settings
        from app.core.config import settings
        if settings.NOMBA_ACCOUNT_ID == user_id:
            # Query by default config email or first merchant
            merchant = db.query(Merchant).first()
            
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not registered in Cadence"
        )
        
    # Use the decrypted/stored client secret as the HMAC key
    secret_key = merchant.nomba_client_secret_encrypted or ""
    
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
    
    # Nomba token key usually resides under data.tokenKey or in data.paymentMethod details
    token_key = data.get("tokenKey")
    
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
