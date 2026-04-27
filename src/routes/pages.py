from fastapi import APIRouter
from fastapi.responses import FileResponse
import os
from src import state

router = APIRouter(tags=["pages"])


@router.get("/login")
async def read_login():
    login_path = os.path.join(state.public_dir, "html", "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)


@router.get("/")
async def read_index():
    index_path = os.path.join(state.public_dir, "html", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)


@router.get("/chat")
async def read_chat():
    chat_path = os.path.join(state.public_dir, "html", "chat.html")
    if os.path.exists(chat_path):
        return FileResponse(chat_path)


@router.get("/settings")
async def read_settings():
    index_path = os.path.join(state.public_dir, "html", "settings.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
