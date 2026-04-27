from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
import secrets
from src import state

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login")
async def auth_login(password: str = Body(..., embed=True)):
    if not state.password_enabled:
        token = secrets.token_hex(32)
        state.auth_tokens.add(token)
        resp = JSONResponse({"success": True})
        resp.set_cookie(key="auth_token", value=token, httponly=True)
        return resp
    if password == state.user_password:
        token = secrets.token_hex(32)
        state.auth_tokens.add(token)
        resp = JSONResponse({"success": True})
        resp.set_cookie(key="auth_token", value=token, httponly=True)
        return resp
    raise HTTPException(status_code=401, detail="Invalid password")


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
    token = request.cookies.get("auth_token")
    return {
        "authenticated": token in state.auth_tokens if state.password_enabled else True,
        "password_enabled": state.password_enabled
    }
