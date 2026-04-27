import locale
import socket
import secrets
import os
import json
from dotenv import load_dotenv, set_key

load_dotenv()

from src.player import Player
from src.joystick import JoystickController
from src.llm_client import LLMClient
from src.comfyui import ComfyUIClient

version_info = "TavLite v1.0.0"
PORT = 12333
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
public_dir = os.path.join(BASE_DIR, "public")

player = Player()
player.udp_url = os.getenv("UDP_URL", None)
player.serial_device = os.getenv("SERIAL_DEVICE", None)
player.current_mode = os.getenv("CURRENT_MODE", "disabled")
player.offset_value = int(os.getenv("OFFSET", 0))

joystick_controller = JoystickController()
joystick_controller.current_mode = os.getenv("CURRENT_MODE", "serial")
joystick_controller.serial_device = os.getenv("SERIAL_DEVICE", None)

llm_client = LLMClient(
    base_url=os.getenv("BASE_URL", ""),
    api_key=os.getenv("API_KEY", ""),
    model=os.getenv("MODEL", "")
)
llm_temperature = float(os.getenv("TEMPERATURE", 1.0))

comfyui_client = ComfyUIClient(
    os.getenv("COMFYUI_URL", ""),
    os.getenv("COMFYUI_TYPE", ""),
    os.getenv("COMFYUI_diffusion", ""),
    os.getenv("COMFYUI_CLIP", ""),
    os.getenv("COMFYUI_VAE", ""),
)

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
password_enabled = os.getenv("PASSWORD_ENABLED", "false") == "true"
user_password = os.getenv("PASSWORD", "")
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
    if not os.path.exists(CARDS_DIR):
        os.makedirs(CARDS_DIR, exist_ok=True)
    with open(old_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    for name, card in cards.items():
        safe_name = name.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')
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
    for filename in os.listdir(CARDS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CARDS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name, card in data.items():
                    card_list.append((name, card))
    card_list.sort(key=lambda x: x[1].get('updated_at', 0), reverse=True)
    return dict(card_list)


def save_cards(cards):
    os.makedirs(CARDS_DIR, exist_ok=True)
    for filename in os.listdir(CARDS_DIR):
        if filename.endswith(".json"):
            os.remove(os.path.join(CARDS_DIR, filename))
    for name, card in cards.items():
        safe_name = name.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')
        filepath = os.path.join(CARDS_DIR, f"{safe_name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({name: card}, f, ensure_ascii=False, indent=2)
