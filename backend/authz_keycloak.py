import os
import time
import json
import urllib.request
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=True)

ISSUER = os.getenv("KEYCLOAK_ISSUER", "").rstrip("/")
AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "")
JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", "")

# simple in-process JWKS cache
_JWKS: Optional[dict] = None
_JWKS_TS: float = 0
_JWKS_TTL = 3600  # 1h

def _get_jwks():
    global _JWKS, _JWKS_TS
    now = time.time()
    if _JWKS and now - _JWKS_TS < _JWKS_TTL:
        return _JWKS
    if not JWKS_URL:
        raise RuntimeError("KEYCLOAK_JWKS_URL not configured")
    with urllib.request.urlopen(JWKS_URL, timeout=5) as resp:
        data = json.load(resp)
    _JWKS = data
    _JWKS_TS = now
    return _JWKS

def _expected_auds():
    # allow comma-separated list in env: "transition-spa,account"
    return {a.strip() for a in AUDIENCE.split(",") if a.strip()}

def _raise_unauth(detail="Not authenticated"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

def verify_jwt_token(token: str) -> dict:
    jwks = _get_jwks()
    try:
        # jose can accept jwks dict with key set
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not key:
            _raise_unauth("Signing key not found")

        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg","RS256"), "RS256"],
            # audience=AUDIENCE if AUDIENCE else None,
            issuer=ISSUER if ISSUER else None,
            # options={"verify_aud": bool(AUDIENCE), "verify_iss": bool(ISSUER)},
            options={"verify_aud": False, "verify_iss": bool(ISSUER)},
        )

        # Flexible audience validation: accept if any expected matches aud OR azp
        expected = _expected_auds()
        if expected:
            aud_claim = payload.get("aud")
            if isinstance(aud_claim, str):
                auds = {aud_claim}
            elif isinstance(aud_claim, (list, tuple, set)):
                auds = set(aud_claim)
            else:
                auds = set()

            azp = payload.get("azp")  # authorized party (often clientId)
            if not (expected & auds or (azp and azp in expected)):
                _raise_unauth("Invalid audience")
                
        return payload
    except JWTError as e:
        _raise_unauth(str(e))

async def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Use this as a dependency to protect routes."""
    token = creds.credentials
    return verify_jwt_token(token)

def require_role(role: str):
    """Example role-check dependency (Keycloak realm roles)."""
    async def _dep(payload: dict = Depends(require_user)):
        roles = (
            payload.get("realm_access", {}).get("roles", [])
            if isinstance(payload.get("realm_access"), dict) else []
        )
        if role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return _dep
