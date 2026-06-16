from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import secrets
from src import state
from src.logger import get_runtime_logger
_log = get_runtime_logger("auth")

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login")
async def auth_login(request: Request = None):
    token = secrets.token_hex(32)
    state.auth_tokens.add(token)
    _log.info("Login")
    resp = JSONResponse({"success": True})
    resp.set_cookie(key="auth_token", value=token, httponly=True)
    return resp


@router.post("/api/auth/logout")
async def auth_logout(request: Request):
    token = request.cookies.get("auth_token")
    if token:
        state.auth_tokens.discard(token)
    resp = JSONResponse({"success": True})
    resp.delete_cookie("auth_token")
    return resp


@router.get("/api/auth/check")
async def auth_check(request: Request):
    return {
        "authenticated": True,
        "password_enabled": False
    }
