from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, generate_api_key_prefix_and_secret
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant, APIKey

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    nomba_client_id: str
    nomba_client_secret: str
    nomba_account_id: str

class LoginRequest(BaseModel):
    email: str
    password: str

class APIKeyCreateRequest(BaseModel):
    label: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_merchant(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Check if merchant exists
    existing = db.query(Merchant).filter(Merchant.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
        
    merchant = Merchant(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        nomba_client_id=payload.nomba_client_id,
        nomba_client_secret_encrypted=payload.nomba_client_secret,
        nomba_account_id=payload.nomba_account_id
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    
    return {"message": "Merchant registered successfully", "merchant_id": merchant.id}

@router.post("/login")
def login_merchant(payload: LoginRequest, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.email == payload.email).first()
    if not merchant or not verify_password(payload.password, merchant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    access_token = create_access_token(data={"sub": merchant.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
def generate_key(
    payload: APIKeyCreateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    prefix, plain_key, hashed_key = generate_api_key_prefix_and_secret()
    
    api_key = APIKey(
        merchant_id=merchant.id,
        key_hash=hashed_key,
        key_prefix=prefix,
        label=payload.label
    )
    db.add(api_key)
    db.commit()
    
    return {
        "api_key": plain_key,
        "label": payload.label,
        "prefix": prefix,
        "message": "Copy this key now. You will not be able to see it again."
    }

@router.get("/api-keys")
def list_keys(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    keys = db.query(APIKey).filter(APIKey.merchant_id == merchant.id, APIKey.is_active == True).all()
    return [
        {
            "id": k.id,
            "prefix": k.key_prefix,
            "label": k.label,
            "created_at": k.created_at
        } for k in keys
    ]
