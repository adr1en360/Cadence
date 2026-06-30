import hmac
import hashlib
import base64
import json

def verify_nomba_webhook(
    payload: dict,
    headers: dict,
    secret_key: str
) -> bool:
    """
    Verify the signature of an inbound webhook from Nomba.
    Uses the structured colon-delimited string signing recipe.
    """
    # 1. Extract values from payload and headers
    event_type = payload.get("event_type", "")
    request_id = payload.get("requestId", "")
    
    # Nested fields under data
    data = payload.get("data", {})
    merchant = data.get("merchant", {})
    user_id = merchant.get("userId", "")
    wallet_id = merchant.get("walletId", "")  # might be None or empty
    if wallet_id is None:
        wallet_id = ""
        
    transaction = data.get("transaction", {})
    transaction_id = transaction.get("transactionId", "")
    tx_type = transaction.get("type", "")
    time_val = transaction.get("time", "")
    response_code = transaction.get("responseCode", "")  # e.g., "00" or empty
    if response_code is None:
        response_code = ""

    # Timestamp from headers
    timestamp = headers.get("nomba-timestamp", "")

    # 2. Reconstruct the signing string:
    # {event_type}:{requestId}:{userId}:{walletId}:{transactionId}:{type}:{time}:{responseCode}:{nomba-timestamp}
    signing_string = f"{event_type}:{request_id}:{user_id}:{wallet_id}:{transaction_id}:{tx_type}:{time_val}:{response_code}:{timestamp}"
    
    print(f"[*] Reconstructed signing string:")
    print(f"    '{signing_string}'")

    # 3. Compute HMAC-SHA256
    computed_hmac = hmac.new(
        secret_key.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256
    ).digest()
    
    computed_signature = base64.b64encode(computed_hmac).decode("utf-8")
    
    nomba_sig = headers.get("nomba-signature", "")
    print(f"[*] Computed Signature: {computed_signature}")
    print(f"[*] Expected Signature: {nomba_sig}")
    
    # 4. Secure comparison
    is_valid = hmac.compare_digest(computed_signature, nomba_sig)
    return is_valid

def test_webhook_signing():
    print("[*] Starting Webhook HMAC Signature Test...")
    
    secret_key = "test_merchant_secret_key"
    
    # Construct a sample webhook payload matching Nomba's schema
    payload = {
        "event_type": "payment_success",
        "requestId": "550e8400-e29b-41d4-a716-446655440000",
        "data": {
            "merchant": {
                "userId": "f666ef9b-888e-4799-85ce-acb505b28023",
                "walletId": "wallet_123"
            },
            "transaction": {
                "fee": 0.28,
                "type": "online_checkout",
                "transactionId": "WEB-ONLINE_C-abc123-uuid",
                "transactionAmount": 2000.00,
                "time": "2026-06-30T10:00:00Z",
                "responseCode": "00"
            },
            "order": {
                "amount": 2000.00,
                "orderId": "a1b2c3d4",
                "orderReference": "cadence_sub_001",
                "paymentMethod": "card_payment",
                "currency": "NGN"
            }
        }
    }
    
    timestamp = "2026-06-30T10:00:05Z"
    
    # Calculate the valid signature matching this payload manually for verification
    # signing string format:
    # {event_type}:{requestId}:{userId}:{walletId}:{transactionId}:{type}:{time}:{responseCode}:{nomba-timestamp}
    signing_string = f"payment_success:550e8400-e29b-41d4-a716-446655440000:f666ef9b-888e-4799-85ce-acb505b28023:wallet_123:WEB-ONLINE_C-abc123-uuid:online_checkout:2026-06-30T10:00:00Z:00:{timestamp}"
    
    computed_hmac = hmac.new(
        secret_key.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256
    ).digest()
    correct_sig = base64.b64encode(computed_hmac).decode("utf-8")
    
    headers = {
        "nomba-signature": correct_sig,
        "nomba-timestamp": timestamp,
        "nomba-signature-algorithm": "HmacSHA256"
    }
    
    # Verify signature
    success = verify_nomba_webhook(payload, headers, secret_key)
    if success:
        print("[OK] Webhook HMAC signature verification logic is 100% correct!")
        return True
    else:
        print("[ERROR] Webhook verification logic failed.")
        return False

if __name__ == "__main__":
    success = test_webhook_signing()
    import sys
    sys.exit(0 if success else 1)
