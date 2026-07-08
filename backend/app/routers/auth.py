from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
import pyotp
from fastapi import Request
from ..limiter import limiter
from ..database import get_db
from ..models.core import User, AuditLog
from ..config import settings
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "Officer"

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth_service.jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = auth_service.TokenData(email=email, role=payload.get("role"), user_id=payload.get("user_id"))
    except auth_service.JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth_service.get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Audit log
    audit = AuditLog(actor_id=new_user.id, action="REGISTER", entity_type="USER", entity_id=str(new_user.id))
    db.add(audit)
    db.commit()
    
    return {"message": "User registered successfully"}

@router.post("/login", response_model=auth_service.Token)
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), totp_code: str = Form(None), db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.role == "Admin" and user.totp_enabled:
        if not totp_code:
            raise HTTPException(status_code=401, detail="TOTP code required for Admin")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
            
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}, expires_delta=access_token_expires
    )
    
    # Audit log
    audit = AuditLog(actor_id=user.id, action="LOGIN", entity_type="USER", entity_id=str(user.id))
    db.add(audit)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

class TOTPVerify(BaseModel):
    code: str

@router.post("/2fa/setup")
def setup_2fa(current_user: User = Depends(require_role(["Admin"])), db: Session = Depends(get_db)):
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already setup and enabled")
        
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    db.commit()
    
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="AURA")
    
    return {"secret": secret, "provisioning_uri": uri}

@router.post("/2fa/verify")
def verify_2fa(req: TOTPVerify, current_user: User = Depends(require_role(["Admin"])), db: Session = Depends(get_db)):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not setup")
        
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(req.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
        
    current_user.totp_enabled = 1
    
    audit = AuditLog(actor_id=current_user.id, action="ENABLE_2FA", entity_type="USER", entity_id=str(current_user.id))
    db.add(audit)
    db.commit()
    
    return {"message": "2FA successfully verified and enabled"}
