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
from src.logger import init_logger, get_runtime_logger
from src.mdns import start_mdns

from src.routes.pages import router as pages_router
from src.routes.system import router as system_router
from src.routes.config import router as config_router
from src.routes.auth import router as auth_router
from src.routes.cards import router as cards_router
from src.routes.script import router as script_router
from src.routes.joystick import router as joystick_router
from src.routes.llm import router as llm_router
from src.routes.t2i import router as t2i_router
from src.routes.chat import router as chat_router

PORT = state.PORT
app = FastAPI(title="TavLite", version="1.1.0")

static_dirs = ["css", "js", "img", "json", "docs"]
for dir_name in static_dirs:
    app.mount(f"/{dir_name}", StaticFiles(directory=os.path.join(state.public_dir, dir_name)), name=dir_name)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    return await call_next(request)


app.include_router(pages_router)
app.include_router(system_router)
app.include_router(config_router)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(script_router)
app.include_router(joystick_router)
app.include_router(llm_router)
app.include_router(t2i_router)
app.include_router(chat_router)


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
    _protocol = "http"

    def open_chat(icon, item):
        webbrowser.open(f"{_protocol}://127.0.0.1:{PORT}/")

    def open_settings(icon, item):
        webbrowser.open(f"{_protocol}://127.0.0.1:{PORT}/settings")

    def open_prompts(icon, item):
        os.startfile(os.path.join(state.BASE_DIR, "public", "json", "prompts"))

    def open_cards(icon, item):
        os.startfile(os.path.join(state.BASE_DIR, "public", "json", "cards"))

    def open_install_dir(icon, item):
        os.startfile(state.BASE_DIR)

    def open_logs(icon, item):
        os.startfile(os.path.join(state.BASE_DIR, "logs"))

    def open_github(icon, item):
        webbrowser.open("https://github.com/Karasukaigan/TavLite")

    def open_buy_pro(icon, item):
        webbrowser.open("https://beyondblackwall.com/product/2")

    translations = {
        "Homepage": "主页面",
        "Settings": "设置页面",
        "Prompts Folder": "提示词目录",
        "Character Cards Folder": "角色卡目录",
        "Installation Folder": "安装目录",
        "Log Directory": "日志目录",
        "GitHub": "GitHub",
        "Buy TavLite Pro": "购买TavLite Pro",
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
            MenuItem(tr("Homepage"), open_chat),
            MenuItem(tr("Settings"), open_settings),
            MenuItem(tr("Prompts Folder"), open_prompts),
            MenuItem(tr("Character Cards Folder"), open_cards),
            MenuItem(tr("Installation Folder"), open_install_dir),
            MenuItem(tr("Log Directory"), open_logs),
            MenuItem(tr("GitHub"), open_github),
            MenuItem(tr("Buy TavLite Pro"), open_buy_pro),
            Menu.SEPARATOR,
            MenuItem(tr("Exit"), on_exit)
        )
    )
    icon.run()


if __name__ == "__main__":
    init_logger()
    state.load_token_usage()
    get_runtime_logger("server").info("TavLite server starting on port %d", PORT)
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()

    _protocol = "http"

    def open_browser():
        if state.startup_page == "disabled":
            return
        page_map = {"home": "/", "llm": "/settings#llm", "qr": "/settings#qr"}
        path = page_map.get(state.startup_page, "/settings#llm")
        webbrowser.open(f"{_protocol}://127.0.0.1:{PORT}{path}")
    threading.Timer(1.0, open_browser).start()

    start_mdns()

    uvicorn.run(app, host="0.0.0.0", port=PORT, use_colors=False)
