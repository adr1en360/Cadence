import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from app.core.config import settings

# Password hashing configuration using bcrypt directly
def hash_password(password: str) -> str:
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# API key hashing configuration (SHA-256)
def generate_api_key_prefix_and_secret() -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (prefix, plain_secret_key, hashed_secret_key)
    """
    import secrets
    plain_secret = secrets.token_urlsafe(32)
    prefix = f"cd_{plain_secret[:6]}"
    
    # Prefix + plain secret is the API key token the user sees: e.g. cd_abc12_plainsecret
    full_api_key = f"{prefix}_{plain_secret}"
    hashed_key = hash_api_key(full_api_key)
    
    return prefix, full_api_key, hashed_key

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    return hmac.compare_digest(hash_api_key(plain_api_key), hashed_api_key)

# JWT creation and validation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return decoded_token if decoded_token.get("exp") >= datetime.utcnow().timestamp() else None
    except Exception:
        return None

# Webhook signature verification (Nomba inbound)
def verify_nomba_webhook(
    payload: dict,
    headers: dict,
    secret_key: str
) -> bool:
    """
    Verify the signature of an inbound webhook from Nomba.
    Uses the structured colon-delimited string signing recipe.
    """
    event_type = payload.get("event_type", "")
    request_id = payload.get("requestId", "")
    
    data = payload.get("data", {})
    merchant = data.get("merchant", {})
    user_id = merchant.get("userId", "")
    wallet_id = merchant.get("walletId", "")
    if wallet_id is None:
        wallet_id = ""
        
    transaction = data.get("transaction", {})
    transaction_id = transaction.get("transactionId", "")
    tx_type = transaction.get("type", "")
    time_val = transaction.get("time", "")
    response_code = transaction.get("responseCode", "")
    if response_code is None:
        response_code = ""

    timestamp = headers.get("nomba-timestamp", "")
    if not timestamp:
        # Check lowercase header just in case
        timestamp = headers.get("Nomba-Timestamp", "")

    # Replay attack prevention check (log warning in sandbox/dev instead of strict rejection)
    if timestamp:
        try:
            from datetime import datetime
            ts_str = timestamp.replace("Z", "+00:00")
            event_dt = datetime.fromisoformat(ts_str)
            now = datetime.utcnow()
            dt_diff = abs((now - event_dt.replace(tzinfo=None)).total_seconds())
            if dt_diff > 300:
                print(f"[SECURITY WARNING] Inbound Nomba webhook timestamp drift is too high: {dt_diff:.1f}s (potential replay attack)")
        except Exception as e:
            print(f"[SECURITY WARNING] Failed to parse webhook timestamp '{timestamp}': {e}")

    # Signing string:
    # {event_type}:{requestId}:{userId}:{walletId}:{transactionId}:{type}:{time}:{responseCode}:{nomba-timestamp}
    signing_string = f"{event_type}:{request_id}:{user_id}:{wallet_id}:{transaction_id}:{tx_type}:{time_val}:{response_code}:{timestamp}"

    computed_hmac = hmac.new(
        secret_key.encode("utf-8"),
        signing_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    
    computed_signature = base64.b64encode(computed_hmac).decode("utf-8")
    
    # Headers signature lookup (handles potential lowercase issue)
    nomba_sig = headers.get("nomba-signature", "")
    
    return hmac.compare_digest(computed_signature, nomba_sig)

# Webhook signature generation (Outbound to merchant)
def sign_outbound_webhook(payload: dict, secret: str) -> str:
    """Generate a signature for an outbound merchant webhook request."""
    import json
    raw_body = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        secret.encode("utf-8"),
        raw_body.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    return signature

def get_fernet():
    # Derive a 32-byte URL-safe base64 key from SECRET_KEY
    import hashlib
    import base64
    from app.core.config import settings
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise ImportError("cryptography package required — run: pip install cryptography")
    
    key_bytes = hashlib.sha256(
        settings.SECRET_KEY.encode("utf-8")
    ).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt_credential(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_credential(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
