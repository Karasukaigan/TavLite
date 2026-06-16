from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os
from src import state

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=os.path.join(state.public_dir, "templates"))


@router.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "title": "TavLite", "css": "home.css", "js": "index.js", "marked": True
    })


@router.get("/chat")
async def read_chat(request: Request):
    return templates.TemplateResponse(request, "chat.html", {
        "title": "Chat", "css": "chat.css",
        "extra_css": "chat-theme.css", "js": "chat.js", "marked": True
    })


@router.get("/settings")
async def read_settings(request: Request):
    return templates.TemplateResponse(request, "settings.html", {
        "title": "Settings", "css": "settings.css",
        "js": "settings.js", "marked": True, "qrcode": True
    })



