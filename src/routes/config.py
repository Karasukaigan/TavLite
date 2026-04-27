from fastapi import APIRouter, Body
from dotenv import set_key, load_dotenv
import os
from src import state
from src.comfyui import ComfyUIClient

router = APIRouter(tags=["config"])


@router.post("/api/config")
async def set_config(u: str = None, s: str = None, m: str = None):
    if u is not None:
        state.player.udp_url = u
        set_key(".env", "UDP_URL", u)
    if s is not None:
        state.player.serial_device = s
        set_key(".env", "SERIAL_DEVICE", s)
    if m is not None and m in ["udp", "serial", "disabled"]:
        state.player.current_mode = m
        set_key(".env", "CURRENT_MODE", m)
    return {
        "message": "Configuration updated successfully",
        "udp_url": state.player.udp_url,
        "serial_device": state.player.serial_device,
        "mode": state.player.current_mode
    }


@router.get("/api/config")
async def get_config():
    return {
        "udp_url": state.player.udp_url,
        "serial_device": state.player.serial_device,
        "mode": state.player.current_mode,
        "offset": state.player.offset_value
    }


@router.post("/api/config/llm")
async def set_llm_config(
    base_url: str = Body(""),
    api_key: str = Body(""),
    model: str = Body(""),
    temperature: float = Body(1.0)
):
    if base_url and base_url != state.llm_client.base_url:
        set_key(".env", "BASE_URL", base_url)
    if api_key != state.llm_client.api_key or api_key == "":
        set_key(".env", "API_KEY", api_key)
    state.llm_client.new(base_url, api_key)
    if model != state.llm_client.model:
        set_key(".env", "MODEL", model)
        state.llm_client.model = model
    temp_str = f"{temperature:.1f}"
    if temperature != state.llm_temperature:
        set_key(".env", "TEMPERATURE", temp_str)
        state.llm_temperature = temperature
    return {
        "message": "LLM configuration updated successfully",
        "base_url": state.llm_client.base_url,
        "api_key": state.llm_client.api_key,
        "model": state.llm_client.model,
        "temperature": state.llm_temperature
    }


@router.get("/api/config/llm")
async def get_llm_config():
    return {
        "base_url": state.llm_client.base_url,
        "api_key": state.llm_client.api_key,
        "model": state.llm_client.model,
        "temperature": state.llm_temperature
    }


@router.post("/api/config/comfyui")
async def set_comfyui_config(
    url: str = Body(""),
    aspect_ratio: str = Body("portrait"),
    type_: str = Body("", alias="type"),
    diffusion: str = Body(""),
    clip: str = Body(""),
    vae: str = Body("")
):
    if url != os.getenv("COMFYUI_URL"):
        set_key(".env", "COMFYUI_URL", url)
    if aspect_ratio != os.getenv("COMFYUI_ASPECT_RATIO"):
        set_key(".env", "COMFYUI_ASPECT_RATIO", aspect_ratio)
    if type_ != os.getenv("COMFYUI_TYPE"):
        set_key(".env", "COMFYUI_TYPE", type_)
    if diffusion != os.getenv("COMFYUI_diffusion"):
        set_key(".env", "COMFYUI_diffusion", diffusion)
    if clip != os.getenv("COMFYUI_CLIP"):
        set_key(".env", "COMFYUI_CLIP", clip)
    if vae != os.getenv("COMFYUI_VAE"):
        set_key(".env", "COMFYUI_VAE", vae)
    load_dotenv(override=True)
    state.comfyui_client = ComfyUIClient(
        os.getenv("COMFYUI_URL", ""),
        os.getenv("COMFYUI_ASPECT_RATIO", "portrait"),
        os.getenv("COMFYUI_TYPE", ""),
        os.getenv("COMFYUI_diffusion", ""),
        os.getenv("COMFYUI_CLIP", ""),
        os.getenv("COMFYUI_VAE", ""),
    )
    return {
        "message": "ComfyUI configuration updated successfully",
        "url": state.comfyui_client.base_url,
        "aspect_ratio": os.getenv("COMFYUI_ASPECT_RATIO", "portrait"),
        "type": state.comfyui_client.type,
        "diffusion": state.comfyui_client.diffusion,
        "clip": state.comfyui_client.clip,
        "vae": state.comfyui_client.vae,
    }


@router.get("/api/config/comfyui")
async def get_comfyui_config():
    return {
        "url": os.getenv("COMFYUI_URL", ""),
        "aspect_ratio": os.getenv("COMFYUI_ASPECT_RATIO", "portrait"),
        "type": os.getenv("COMFYUI_TYPE", ""),
        "diffusion": os.getenv("COMFYUI_diffusion", ""),
        "clip": os.getenv("COMFYUI_CLIP", ""),
        "vae": os.getenv("COMFYUI_VAE", ""),
    }


@router.get("/api/config/user")
async def get_user_config():
    info = state.load_user_info()
    return {
        "username": info.get("username", ""),
        "profile": info.get("profile", ""),
        "password_enabled": state.password_enabled,
        "password": state.user_password
    }


@router.post("/api/config/user")
async def set_user_config(
    username: str = Body(""),
    profile: str = Body(""),
    pw_enabled: bool = Body(False, alias="password_enabled"),
    password: str = Body("")
):
    if pw_enabled and not password:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    state.save_user_info(username, profile)
    state.user_username = username
    state.user_profile = profile
    if pw_enabled != (os.getenv("PASSWORD_ENABLED", "false") == "true"):
        set_key(".env", "PASSWORD_ENABLED", "true" if pw_enabled else "false")
    if password and password != os.getenv("PASSWORD", ""):
        set_key(".env", "PASSWORD", password)
    load_dotenv(override=True)
    state.password_enabled = os.getenv("PASSWORD_ENABLED", "false") == "true"
    state.user_password = os.getenv("PASSWORD", "")
    if not state.password_enabled:
        state.auth_tokens.clear()
    return {
        "message": "User configuration updated successfully",
        "username": state.user_username,
        "profile": state.user_profile,
        "password_enabled": state.password_enabled
    }
