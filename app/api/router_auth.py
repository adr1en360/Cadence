from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, generate_api_key_prefix_and_secret
from app.api.deps import get_current_merchant
from app.models.merchant import Merchant, APIKey
from app.models.project import Project

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class APIKeyCreateRequest(BaseModel):
    project_id: str
    label: str
    nomba_sub_account_id: Optional[str] = None

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
        password_hash=hash_password(payload.password)
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    
    # Automatically create a default project for the newly registered merchant
    default_proj = Project(
        merchant_id=merchant.id,
        name="My First Project"
    )
    db.add(default_proj)
    db.commit()
    
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
    project = db.query(Project).filter(Project.id == payload.project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
        
    prefix, plain_key, hashed_key = generate_api_key_prefix_and_secret()
    
    api_key = APIKey(
        project_id=project.id,
        key_hash=hashed_key,
        key_prefix=prefix,
        label=payload.label,
        nomba_sub_account_id=payload.nomba_sub_account_id
    )
    db.add(api_key)
    db.commit()
    
    return {
        "api_key": plain_key,
        "label": payload.label,
        "prefix": prefix,
        "nomba_sub_account_id": payload.nomba_sub_account_id,
        "message": "Copy this key now. You will not be able to see it again."
    }

@router.get("/api-keys")
def list_keys(
    project_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id, Project.merchant_id == merchant.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
        
    keys = db.query(APIKey).filter(APIKey.project_id == project.id).all()
    return [
        {
            "id": k.id,
            "prefix": k.key_prefix,
            "label": k.label,
            "created_at": k.created_at,
            "is_active": k.is_active,
            "nomba_sub_account_id": k.nomba_sub_account_id
        } for k in keys
    ]

@router.delete("/api-keys/{key_id}")
def revoke_key(
    key_id: str,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    api_key = db.query(APIKey).join(Project).filter(APIKey.id == key_id, Project.merchant_id == merchant.id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
        
    api_key.is_active = False
    db.commit()
    return {"message": "API key revoked"}
