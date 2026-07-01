from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models.merchant import Merchant, APIKey
from app.models.project import Project

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_current_merchant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Merchant:
    """Authenticate merchant using JWT token (dashboard session)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
        
    merchant_email = payload.get("sub")
    if not merchant_email:
        raise credentials_exception
        
    merchant = db.query(Merchant).filter(Merchant.email == merchant_email).first()
    if not merchant:
        raise credentials_exception
        
    return merchant

def get_project_by_api_key(
    api_key: str = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> Project:
    """Authenticate API requests using Bearer API Key and return the associated Project."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )
        
    # Standard format: 'Bearer cd_xxx_yyy' or just 'cd_xxx_yyy'
    token = api_key
    if api_key.startswith("Bearer "):
        token = api_key.replace("Bearer ", "")
        
    # Extract prefix (prefix format: cd_xxxxxx)
    parts = token.split("_")
    if len(parts) < 2 or not parts[0].startswith("cd"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format"
        )
        
    prefix = f"{parts[0]}_{parts[1]}"
    
    # Query API Key prefix
    db_key = db.query(APIKey).filter(APIKey.key_prefix == prefix, APIKey.is_active == True).first()
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key"
        )
        
    # Securely verify key secret hash
    if not verify_api_key(token, db_key.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key credentials"
        )
        
    return db_key.project
