import locale
import socket
import secrets
import os
import json
import base64
import asyncio
from io import BytesIO
from dotenv import load_dotenv, set_key

load_dotenv(override=True)

from src.logger import get_runtime_logger
_log = get_runtime_logger("state")

from src.player import Player
from src.joystick import JoystickController
from src.llm_client import LLMClient
from src.comfyui import ComfyUIClient
from src.intiface_client import IntifaceClient
from src.handy_client import HandyClient

version_info = "TavLite v1.1.0"
PORT = 12333
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
public_dir = os.path.join(BASE_DIR, "public")
UPLOADS_DIR = os.path.join(public_dir, "img", "uploads")


def _safe_card_name(name):
    return name.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_').replace('|', '_').replace('<', '_').replace('>', '_').replace('"', '_').replace('?', '_').replace('*', '_')


def _save_concept_art_file(base64_str, card_name):
    if not base64_str or not base64_str.startswith('data:'):
        return base64_str
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    meta, encoded = base64_str.split(',', 1)
    raw = base64.b64decode(encoded)

    ext = 'png'
    if raw[:6] in (b'GIF89a', b'GIF87a'):
        ext = 'gif'
    elif len(raw) >= 12 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        ext = 'webp'
    elif raw[:8] == b'\x89PNG\r\n\x1a\n':
        ext = 'png'
    elif raw[:3] == b'\xff\xd8\xff':
        ext = 'jpg'
    else:
        if 'image/webp' in meta:
            ext = 'webp'
        elif 'image/png' in meta:
            ext = 'png'
        elif 'image/jpeg' in meta or 'image/jpg' in meta:
            ext = 'jpg'
        elif 'image/gif' in meta:
            ext = 'gif'

    safe_name = _safe_card_name(card_name)
    filepath = os.path.join(UPLOADS_DIR, f"{safe_name}.{ext}")
    if ext in ('gif', 'webp'):
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("concept art image must be 5MB or smaller")
        with open(filepath, 'wb') as f:
            f.write(raw)
    else:
        try:
            from PIL import Image
            img = Image.open(BytesIO(raw))
            img.save(filepath)
        except ImportError:
            with open(filepath, 'wb') as f:
                f.write(raw)
    return f"/img/uploads/{safe_name}.{ext}"


def _delete_concept_art_file(card_name):
    if not os.path.isdir(UPLOADS_DIR):
        return
    safe_name = _safe_card_name(card_name)
    for ext in ('png', 'webp', 'jpg', 'jpeg', 'gif'):
        filepath = os.path.join(UPLOADS_DIR, f"{safe_name}.{ext}")
        if os.path.exists(filepath):
            os.remove(filepath)
            break


def _safe_image_name(name):
    import re
    name = re.sub(r'[/\\:|<>"?*\x00-\x1f]', '_', name)
    name = name.strip('. ')
    return name or '_'


def _save_card_image_file(raw_bytes, card_name, image_name):
    safe_card = _safe_card_name(card_name)
    safe_img = _safe_image_name(image_name)
    card_dir = os.path.join(UPLOADS_DIR, safe_card)
    os.makedirs(card_dir, exist_ok=True)
    filepath = os.path.join(card_dir, safe_img)
    with open(filepath, 'wb') as f:
        f.write(raw_bytes)
    return f"/img/uploads/{safe_card}/{safe_img}"


def _save_card_image_from_base64(base64_str, card_name, image_name):
    if not base64_str or not base64_str.startswith('data:'):
        return base64_str
    _, encoded = base64_str.split(',', 1)
    raw = base64.b64decode(encoded)
    return _save_card_image_file(raw, card_name, image_name)


def _delete_card_image_file(card_name, image_name):
    safe_card = _safe_card_name(card_name)
    safe_img = _safe_image_name(image_name)
    filepath = os.path.join(UPLOADS_DIR, safe_card, safe_img)
    if os.path.exists(filepath):
        os.remove(filepath)


player = Player()
player.udp_url = os.getenv("UDP_URL", None)
player.serial_device = os.getenv("SERIAL_DEVICE", None)
player.current_mode = os.getenv("CURRENT_MODE", "disabled")
player.offset_value = int(os.getenv("OFFSET", 0))
player.motion_range = int(os.getenv("MOTION_RANGE", "9999"))

joystick_controller = JoystickController()
joystick_controller.current_mode = os.getenv("CURRENT_MODE", "serial")
joystick_controller.serial_device = os.getenv("SERIAL_DEVICE", None)

llm_client = LLMClient(
    base_url=os.getenv("BASE_URL", ""),
    api_key=os.getenv("API_KEY", ""),
    model=os.getenv("MODEL", "")
)
llm_temperature = float(os.getenv("TEMPERATURE", 1.0))
llm_reasoning_effort = os.getenv("REASONING_EFFORT", "")

comfyui_client = ComfyUIClient(
    os.getenv("COMFYUI_URL", ""),
    os.getenv("COMFYUI_ASPECT_RATIO", "portrait"),
    os.getenv("COMFYUI_TYPE", ""),
    os.getenv("COMFYUI_diffusion", ""),
    os.getenv("COMFYUI_CLIP", ""),
    os.getenv("COMFYUI_VAE", ""),
)

intiface_client: IntifaceClient | None = None
intiface_ws_url = os.getenv("INTIFACE_WS_URL", "")
intiface_device_index = int(os.getenv("INTIFACE_DEVICE_INDEX", "0"))
intiface_feature_index = int(os.getenv("INTIFACE_FEATURE_INDEX", "0"))
intiface_step_count = int(os.getenv("INTIFACE_STEP_COUNT", "100"))
intiface_device_name = os.getenv("INTIFACE_DEVICE_NAME", "")

handy_client: HandyClient | None = None
handy_connection_key = os.getenv("HANDY_CONNECTION_KEY", "")
handy_api_version = os.getenv("HANDY_API_VERSION", "v3")
handy_min_depth = float(os.getenv("HANDY_MIN_DEPTH", "0"))
handy_max_depth = float(os.getenv("HANDY_MAX_DEPTH", "100"))
player.handy_min_depth = handy_min_depth
player.handy_max_depth = handy_max_depth
if handy_connection_key:
    handy_client = HandyClient(
        api_key=handy_connection_key,
        api_version=handy_api_version,
        min_speed=10,
        max_speed=80,
        min_depth=handy_min_depth,
        max_depth=handy_max_depth,
    )
    player.handy_client = handy_client

USER_JSON_PATH = os.path.join(public_dir, "json", "user.json")

def load_user_info():
    if os.path.exists(USER_JSON_PATH):
        with open(USER_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        os.makedirs(os.path.dirname(USER_JSON_PATH), exist_ok=True)
        default = {"username": "", "profile": ""}
        with open(USER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default

def save_user_info(username, profile):
    data = {"username": username, "profile": profile}
    with open(USER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

_user_info = load_user_info()
user_username = _user_info.get("username", "")
user_profile = _user_info.get("profile", "")
password_enabled = False
user_password = ""
https_enabled = False
startup_page = os.getenv("STARTUP_PAGE", "llm")
auth_tokens = set()


def get_host_ip_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    return ip


CARDS_DIR = os.path.join(public_dir, "json", "cards")

def _migrate_cards_from_old_path():
    old_path = os.path.join(public_dir, "json", "prompts", "cards.json")
    if not os.path.exists(old_path):
        return
    _log.info("Migrating cards from old path %s", old_path)
    if not os.path.exists(CARDS_DIR):
        os.makedirs(CARDS_DIR, exist_ok=True)
    with open(old_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    for name, card in cards.items():
        safe_name = _safe_card_name(name)
        filepath = os.path.join(CARDS_DIR, f"{safe_name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({name: card}, f, ensure_ascii=False, indent=2)
    os.remove(old_path)

def load_cards():
    if not os.path.exists(CARDS_DIR):
        _migrate_cards_from_old_path()
    if not os.path.exists(CARDS_DIR):
        os.makedirs(CARDS_DIR, exist_ok=True)
    card_list = []
    needs_rewrite = []
    for filename in os.listdir(CARDS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CARDS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for name, card in data.items():
                art = card.get("concept_art", "")
                if art and art.startswith("data:"):
                    card["concept_art"] = _save_concept_art_file(art, name)
                    needs_rewrite.append((filepath, {name: card}))
                card_list.append((name, card))
    for filepath, data in needs_rewrite:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    card_list.sort(key=lambda x: x[1].get('updated_at', 0), reverse=True)
    _log.info("Loaded %d cards", len(card_list))
    return dict(card_list)


def save_cards(cards):
    os.makedirs(CARDS_DIR, exist_ok=True)
    for filename in os.listdir(CARDS_DIR):
        if filename.endswith(".json"):
            os.remove(os.path.join(CARDS_DIR, filename))
    for name, card in cards.items():
        safe_name = _safe_card_name(name)
        filepath = os.path.join(CARDS_DIR, f"{safe_name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({name: card}, f, ensure_ascii=False, indent=2)


def _save_one_card(name, card):
    safe_name = _safe_card_name(name)
    filepath = os.path.join(CARDS_DIR, f"{safe_name}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({name: card}, f, ensure_ascii=False, indent=2)


def _delete_one_card_file(name):
    safe_name = _safe_card_name(name)
    filepath = os.path.join(CARDS_DIR, f"{safe_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)


CUSTOM_MODULES_PATH = os.path.join(public_dir, "json", "prompts", "custom_modules.json")


def load_custom_modules():
    if not os.path.exists(CUSTOM_MODULES_PATH):
        return {}
    try:
        with open(CUSTOM_MODULES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_custom_modules(data):
    os.makedirs(os.path.dirname(CUSTOM_MODULES_PATH), exist_ok=True)
    with open(CUSTOM_MODULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


TOKENS_DIR = os.path.join(BASE_DIR, "logs", "tokens")

token_usage: dict = {}

def load_token_usage():
    global token_usage
    token_usage = {}
    if not os.path.isdir(TOKENS_DIR):
        return
    log_files = sorted(f for f in os.listdir(TOKENS_DIR) if f.startswith("tokens.log"))
    for filename in log_files:
        filepath = os.path.join(TOKENS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ts = record.get("timestamp", "")
                        model = record.get("model", "")
                        if not ts or not model:
                            continue
                        date = ts[:10]
                        prompt = record.get("prompt_tokens")
                        completion = record.get("completion_tokens")
                        if prompt is None or completion is None:
                            import re
                            usage_str = record.get("usage", "")
                            m = re.search(r'prompt_tokens=(\d+)', usage_str)
                            n = re.search(r'completion_tokens=(\d+)', usage_str)
                            if m and n:
                                prompt = int(m.group(1))
                                completion = int(n.group(1))
                            else:
                                continue
                        if date not in token_usage:
                            token_usage[date] = {}
                        if model not in token_usage[date]:
                            token_usage[date][model] = {"prompt": 0, "completion": 0}
                        token_usage[date][model]["prompt"] += prompt
                        token_usage[date][model]["completion"] += completion
                    except Exception:
                        continue
        except Exception:
            pass

def update_token_usage(timestamp: str, model: str, prompt_tokens: int, completion_tokens: int):
    date = timestamp[:10]
    if date not in token_usage:
        token_usage[date] = {}
    if model not in token_usage[date]:
        token_usage[date][model] = {"prompt": 0, "completion": 0}
    token_usage[date][model]["prompt"] += prompt_tokens
    token_usage[date][model]["completion"] += completion_tokens

_cards_cache = load_cards()


async def async_load_cards():
    return _cards_cache


async def async_save_cards(cards, changed_name=None):
    global _cards_cache
    _cards_cache = cards
    if changed_name:
        if changed_name in cards:
            await asyncio.to_thread(_save_one_card, changed_name, cards[changed_name])
        else:
            await asyncio.to_thread(_delete_one_card_file, changed_name)
    else:
        await asyncio.to_thread(save_cards, dict(cards))
