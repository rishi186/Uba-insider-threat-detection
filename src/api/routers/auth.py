"""
Authentication Router for UBA ITD.

Provides JWT-based employee authentication for the dashboard and endpoint agents.
Uses HMAC-SHA256 tokens with hardcoded demo credentials.

Endpoints:
  POST /auth/login      — Authenticate employee, return JWT
  GET  /auth/verify     — Verify JWT token validity
  GET  /auth/me         — Get current user profile from token
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import base64
import logging

logger = logging.getLogger("uba.auth")
router = APIRouter()

# =============================================================================
# CONFIG
# =============================================================================
JWT_SECRET = "uba-itd-secret-key-2026-do-not-use-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# =============================================================================
# EMPLOYEE CREDENTIALS (Demo — production would use LDAP/AD)
# =============================================================================
EMPLOYEE_CREDENTIALS = {
    "rishi": {
        "password_hash": hashlib.sha256("rishi123".encode()).hexdigest(),
        "user_id": "EMP001",
        "name": "Rishi Mishra",
        "role": "Security Analyst",
        "department": "Cybersecurity",
        "pc_id": "WS-SEC-001",
        "avatar_color": "#00d4ff",
        "is_admin": True,
    },
    "priya": {
        "password_hash": hashlib.sha256("priya123".encode()).hexdigest(),
        "user_id": "EMP002",
        "name": "Priya Sharma",
        "role": "Software Engineer",
        "department": "Engineering",
        "pc_id": "WS-ENG-012",
        "avatar_color": "#00ff88",
        "is_admin": False,
    },
    "alex": {
        "password_hash": hashlib.sha256("alex123".encode()).hexdigest(),
        "user_id": "EMP003",
        "name": "Alex Chen",
        "role": "Database Admin",
        "department": "IT Operations",
        "pc_id": "WS-DBA-003",
        "avatar_color": "#ff6b35",
        "is_admin": False,
    },
    "marcus": {
        "password_hash": hashlib.sha256("marcus123".encode()).hexdigest(),
        "user_id": "EMP004",
        "name": "Marcus Johnson",
        "role": "Contractor",
        "department": "Finance",
        "pc_id": "WS-FIN-007",
        "avatar_color": "#ff3366",
        "is_admin": False,
    },
    "sarah": {
        "password_hash": hashlib.sha256("sarah123".encode()).hexdigest(),
        "user_id": "EMP005",
        "name": "Sarah Williams",
        "role": "HR Manager",
        "department": "Human Resources",
        "pc_id": "WS-HR-002",
        "avatar_color": "#b366ff",
        "is_admin": False,
    },
}


# =============================================================================
# JWT HELPERS (minimal, no pyjwt dependency)
# =============================================================================
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict) -> str:
    """Create a minimal JWT token (HS256)."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_jwt(token: str) -> Optional[dict]:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        # Check expiry
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None


# =============================================================================
# AUTH DEPENDENCY
# =============================================================================
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and validate user from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    # Support "Bearer <token>" format
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================
class LoginRequest(BaseModel):
    username: str = Field(..., description="Employee username")
    password: str = Field(..., description="Employee password")


class LoginResponse(BaseModel):
    status: str
    token: str
    user: dict
    expires_at: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/login")
async def login(req: LoginRequest):
    """
    Authenticate an employee and return a JWT token.
    
    Demo credentials:
      - rishi / rishi123 (Admin)
      - priya / priya123
      - alex / alex123
      - marcus / marcus123
      - sarah / sarah123
    """
    emp = EMPLOYEE_CREDENTIALS.get(req.username.lower())
    if not emp:
        logger.warning("Login failed: unknown user '%s'", req.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()
    if not hmac.compare_digest(password_hash, emp["password_hash"]):
        logger.warning("Login failed: wrong password for '%s'", req.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    
    payload = {
        "sub": emp["user_id"],
        "username": req.username.lower(),
        "name": emp["name"],
        "role": emp["role"],
        "department": emp["department"],
        "pc_id": emp["pc_id"],
        "avatar_color": emp["avatar_color"],
        "is_admin": emp["is_admin"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    
    token = create_jwt(payload)
    
    logger.info("Login success: %s (%s)", emp["name"], emp["user_id"])
    
    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": emp["user_id"],
            "username": req.username.lower(),
            "name": emp["name"],
            "role": emp["role"],
            "department": emp["department"],
            "pc_id": emp["pc_id"],
            "avatar_color": emp["avatar_color"],
            "is_admin": emp["is_admin"],
        },
        "expires_at": expires_at.isoformat(),
    }


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify that a JWT token is valid."""
    return {
        "status": "valid",
        "user_id": user["sub"],
        "name": user["name"],
        "expires_at": datetime.fromtimestamp(
            user["exp"], tz=timezone.utc
        ).isoformat(),
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return {
        "user_id": user["sub"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "department": user["department"],
        "pc_id": user["pc_id"],
        "avatar_color": user["avatar_color"],
        "is_admin": user.get("is_admin", False),
    }
