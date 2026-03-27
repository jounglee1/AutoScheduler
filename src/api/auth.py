import base64
import hashlib
import secrets
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from src.modules.gcal import SCOPES, TOKEN_PATH, is_authenticated
from google_auth_oauthlib.flow import Flow

router = APIRouter(prefix="/auth")

CLIENT_SECRET_PATH = Path(__file__).parent.parent.parent / "config" / "client_secret.json"
REDIRECT_URI = "http://localhost:8001/auth/callback"
FRONTEND_URL = "http://localhost:3000"

_code_verifier: str | None = None


@router.get("/status")
def auth_status():
    return {"authenticated": is_authenticated()}


@router.get("/login")
def auth_login():
    global _code_verifier
    _code_verifier = secrets.token_urlsafe(96)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(_code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH), scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return RedirectResponse(auth_url)


@router.post("/logout")
def auth_logout():
    TOKEN_PATH.unlink(missing_ok=True)
    return {"ok": True}


@router.get("/callback")
def auth_callback(code: str, state: str):
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH), scopes=SCOPES, redirect_uri=REDIRECT_URI, state=state
    )
    flow.fetch_token(code=code, code_verifier=_code_verifier)
    TOKEN_PATH.write_text(flow.credentials.to_json())
    return RedirectResponse(FRONTEND_URL)
