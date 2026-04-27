import os
import threading
import webbrowser
import locale
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import uvicorn

from src import state
from src.routes.pages import router as pages_router
from src.routes.system import router as system_router
from src.routes.config import router as config_router
from src.routes.auth import router as auth_router
from src.routes.cards import router as cards_router
from src.routes.script import router as script_router
from src.routes.joystick import router as joystick_router
from src.routes.llm import router as llm_router
from src.routes.t2i import router as t2i_router

PORT = state.PORT
app = FastAPI(title="TavLite", version="1.0.0")

static_dirs = ["html", "css", "js", "img", "i18n", "json", "docs"]
for dir_name in static_dirs:
    app.mount(f"/{dir_name}", StaticFiles(directory=os.path.join(state.public_dir, dir_name)), name=dir_name)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not state.password_enabled:
        return await call_next(request)
    path = request.url.path
    if path in ["/login", "/favicon.ico"] or any(path.startswith(p) for p in ["/css/", "/js/", "/img/", "/i18n/", "/docs/", "/json/"]) or path.startswith("/api/auth/"):
        return await call_next(request)
    token = request.cookies.get("auth_token")
    if token in state.auth_tokens:
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return RedirectResponse(url="/login")


app.include_router(pages_router)
app.include_router(system_router)
app.include_router(config_router)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(script_router)
app.include_router(joystick_router)
app.include_router(llm_router)
app.include_router(t2i_router)


def create_image():
    logo_path = os.path.join(state.public_dir, "img", "logo.png")
    try:
        image = Image.open(logo_path).convert("RGBA")
        image = image.resize((256, 256), Image.LANCZOS)
        return image
    except Exception:
        width, height = 64, 64
        image = Image.new('RGBA', (width, height))
        dc = ImageDraw.Draw(image)
        dc.ellipse((0, 0, width - 1, height - 1), fill=None, outline="green", width=2)
        mask = Image.new('L', (width, height), 0)
        dc_mask = ImageDraw.Draw(mask)
        dc_mask.ellipse((0, 0, width - 1, height - 1), fill=255)
        image.putalpha(mask)
        return image


def on_exit(icon, item):
    icon.stop()
    os._exit(0)


def get_system_language():
    for v in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        val = os.environ.get(v)
        if val:
            return val.split('.')[0].split('_')[0].lower().strip()
    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            return lang.split('_')[0].lower()
    except:
        pass
    return 'en'


def run_tray_icon():
    def open_chat(icon, item):
        webbrowser.open(f"http://127.0.0.1:{PORT}/")

    def open_settings(icon, item):
        webbrowser.open(f"http://127.0.0.1:{PORT}/settings")

    def open_prompts(icon, item):
        os.startfile(os.path.join(state.BASE_DIR, "public", "json", "prompts"))

    def open_github(icon, item):
        webbrowser.open("https://github.com/Karasukaigan/TavLite")

    translations = {
        "Chat": "聊天",
        "Settings": "设置",
        "Prompts": "提示词",
        "Exit": "退出"
    }

    def tr(text):
        if get_system_language() == "zh":
            return translations.get(text, text)
        return text

    icon = Icon(
        name="TavLite",
        icon=create_image(),
        title="TavLite",
        menu=Menu(
            MenuItem(tr("Chat"), open_chat),
            MenuItem(tr("Settings"), open_settings),
            MenuItem(tr("Prompts"), open_prompts),
            MenuItem("GitHub", open_github),
            Menu.SEPARATOR,
            MenuItem(tr("Exit"), on_exit)
        )
    )
    icon.run()


if __name__ == "__main__":
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()

    def open_browser():
        webbrowser.open(f"http://127.0.0.1:{PORT}/settings")
    threading.Timer(1.0, open_browser).start()

    uvicorn.run(app, host="0.0.0.0", port=PORT, use_colors=False)
