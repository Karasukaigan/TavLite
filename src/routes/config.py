import asyncio
from fastapi import APIRouter, Body, HTTPException, Request
from dotenv import set_key, load_dotenv
import os
from src import state
from src.comfyui import ComfyUIClient
from src.intiface_client import IntifaceClient, PositionFeature
from src.handy_client import HandyClient
from src.logger import get_runtime_logger
_log = get_runtime_logger("config")

router = APIRouter(tags=["config"])


@router.post("/api/config")
async def set_config(u: str = None, s: str = None, m: str = None, iw: str = None, mr: int = None, hck: str = None, hav: str = None, hmd: float = None, hxd: float = None):
    if u is not None:
        state.player.udp_url = u
        await asyncio.to_thread(set_key, ".env", "UDP_URL", u)
    if s is not None:
        state.player.serial_device = s
        await asyncio.to_thread(set_key, ".env", "SERIAL_DEVICE", s)
    if m is not None and m in ["udp", "serial", "disabled", "intiface", "handy"]:
        state.player.current_mode = m
        await asyncio.to_thread(set_key, ".env", "CURRENT_MODE", m)
    if iw is not None:
        state.intiface_ws_url = iw
        await asyncio.to_thread(set_key, ".env", "INTIFACE_WS_URL", iw)
    if mr is not None and mr in (9999, 1000):
        state.player.motion_range = mr
        await asyncio.to_thread(set_key, ".env", "MOTION_RANGE", str(mr))
    if hck is not None:
        state.handy_connection_key = hck
        await asyncio.to_thread(set_key, ".env", "HANDY_CONNECTION_KEY", hck)
        min_d = hmd if hmd is not None else state.handy_min_depth
        max_d = hxd if hxd is not None else state.handy_max_depth
        state.handy_client = HandyClient(
            api_key=hck,
            api_version=hav or state.handy_api_version or "v3",
            min_speed=10,
            max_speed=80,
            min_depth=min_d,
            max_depth=max_d,
        )
        state.player.handy_client = state.handy_client
    if hav is not None and hav in ("v2", "v3"):
        state.handy_api_version = hav
        await asyncio.to_thread(set_key, ".env", "HANDY_API_VERSION", hav)
        if state.handy_client:
            state.handy_client.set_api_version(hav)
    if hmd is not None:
        hmd = max(0.0, min(100.0, float(hmd)))
        state.handy_min_depth = hmd
        state.player.handy_min_depth = hmd
        await asyncio.to_thread(set_key, ".env", "HANDY_MIN_DEPTH", str(hmd))
        if state.handy_client:
            state.handy_client.update_settings(state.handy_client.min_user_speed, state.handy_client.max_user_speed, hmd, state.handy_max_depth)
    if hxd is not None:
        hxd = max(0.0, min(100.0, float(hxd)))
        state.handy_max_depth = hxd
        state.player.handy_max_depth = hxd
        await asyncio.to_thread(set_key, ".env", "HANDY_MAX_DEPTH", str(hxd))
        if state.handy_client:
            state.handy_client.update_settings(state.handy_client.min_user_speed, state.handy_client.max_user_speed, state.handy_min_depth, hxd)
    if m == "handy" and state.handy_client:
        state.player.handy_client = state.handy_client
    if m == "intiface" and state.intiface_client:
        state.player.intiface_client = state.intiface_client
        step_count = state.intiface_step_count
        device_index = state.intiface_device_index
        feature_index = state.intiface_feature_index
        device_name = state.intiface_device_name
        if not device_name:
            devices = state.intiface_client.find_position_devices()
            if devices:
                d = devices[0]
                device_index = d.device_index
                feature_index = d.feature_index
                step_count = d.step_count
                device_name = d.device_name
        state.player._intiface_target = PositionFeature(
            device_index=device_index,
            feature_index=feature_index,
            device_name=device_name or "Intiface Device",
            step_count=step_count,
        )
    _log.info("OSR config updated: mode=%s, udp=%s, serial=%s, intiface_ws=%s, motion_range=%s", m, u, s, iw, mr)
    return {
        "message": "Configuration updated successfully",
        "udp_url": state.player.udp_url,
        "serial_device": state.player.serial_device,
        "mode": state.player.current_mode,
        "motion_range": state.player.motion_range,
    }


@router.get("/api/config")
async def get_config():
    return {
        "udp_url": state.player.udp_url,
        "serial_device": state.player.serial_device,
        "mode": state.player.current_mode,
        "offset": state.player.offset_value,
        "motion_range": state.player.motion_range,
        "handy_connection_key": state.handy_connection_key,
        "handy_api_version": state.handy_api_version,
        "handy_connected": state.handy_client is not None and state.handy_client.is_connected,
        "handy_min_depth": state.handy_min_depth,
        "handy_max_depth": state.handy_max_depth,
    }


ALLOWED_REASONING_EFFORT_VALUES = ("xhigh", "max", "high", "medium", "low", "minimal", "none")

@router.post("/api/config/llm")
async def set_llm_config(
    base_url: str = Body(""),
    api_key: str = Body(""),
    model: str = Body(""),
    temperature: float = Body(1.0),
    reasoning_effort: str = Body("")
):
    if reasoning_effort and reasoning_effort not in ALLOWED_REASONING_EFFORT_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reasoning_effort value. Must be one of: {', '.join(ALLOWED_REASONING_EFFORT_VALUES)}"
        )
    if base_url and base_url != state.llm_client.base_url:
        await asyncio.to_thread(set_key, ".env", "BASE_URL", base_url)
    if api_key != state.llm_client.api_key or api_key == "":
        await asyncio.to_thread(set_key, ".env", "API_KEY", api_key)
    state.llm_client.new(base_url, api_key)
    if model != state.llm_client.model:
        await asyncio.to_thread(set_key, ".env", "MODEL", model)
        state.llm_client.model = model
    temp_str = f"{temperature:.1f}"
    if temperature != state.llm_temperature:
        await asyncio.to_thread(set_key, ".env", "TEMPERATURE", temp_str)
        state.llm_temperature = temperature
    if reasoning_effort != state.llm_reasoning_effort:
        await asyncio.to_thread(set_key, ".env", "REASONING_EFFORT", reasoning_effort)
        state.llm_reasoning_effort = reasoning_effort
    _log.info("LLM config updated: model=%s, temperature=%s, reasoning_effort=%s", state.llm_client.model, state.llm_temperature, state.llm_reasoning_effort)
    return {
        "message": "LLM configuration updated successfully",
        "base_url": state.llm_client.base_url,
        "api_key": state.llm_client.api_key,
        "model": state.llm_client.model,
        "temperature": state.llm_temperature,
        "reasoning_effort": state.llm_reasoning_effort
    }


@router.get("/api/config/llm")
async def get_llm_config():
    return {
        "base_url": state.llm_client.base_url,
        "api_key": state.llm_client.api_key,
        "model": state.llm_client.model,
        "temperature": state.llm_temperature,
        "reasoning_effort": state.llm_reasoning_effort
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
        await asyncio.to_thread(set_key, ".env", "COMFYUI_URL", url)
        os.environ["COMFYUI_URL"] = url
    if aspect_ratio != os.getenv("COMFYUI_ASPECT_RATIO"):
        await asyncio.to_thread(set_key, ".env", "COMFYUI_ASPECT_RATIO", aspect_ratio)
        os.environ["COMFYUI_ASPECT_RATIO"] = aspect_ratio
    if type_ != os.getenv("COMFYUI_TYPE"):
        await asyncio.to_thread(set_key, ".env", "COMFYUI_TYPE", type_)
        os.environ["COMFYUI_TYPE"] = type_
    if diffusion != os.getenv("COMFYUI_diffusion"):
        await asyncio.to_thread(set_key, ".env", "COMFYUI_diffusion", diffusion)
        os.environ["COMFYUI_diffusion"] = diffusion
    if clip != os.getenv("COMFYUI_CLIP"):
        await asyncio.to_thread(set_key, ".env", "COMFYUI_CLIP", clip)
        os.environ["COMFYUI_CLIP"] = clip
    if vae != os.getenv("COMFYUI_VAE"):
        await asyncio.to_thread(set_key, ".env", "COMFYUI_VAE", vae)
        os.environ["COMFYUI_VAE"] = vae
    state.comfyui_client = await asyncio.to_thread(
        lambda: ComfyUIClient(
            os.getenv("COMFYUI_URL", ""),
            os.getenv("COMFYUI_ASPECT_RATIO", "portrait"),
            os.getenv("COMFYUI_TYPE", ""),
            os.getenv("COMFYUI_diffusion", ""),
            os.getenv("COMFYUI_CLIP", ""),
            os.getenv("COMFYUI_VAE", ""),
        )
    )
    _log.info("ComfyUI config updated: url=%s, type=%s, aspect=%s", url, type_, aspect_ratio)
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
        "url": state.comfyui_client.base_url,
        "aspect_ratio": state.comfyui_client.aspect_ratio,
        "type": state.comfyui_client.type,
        "diffusion": state.comfyui_client.diffusion,
        "clip": state.comfyui_client.clip,
        "vae": state.comfyui_client.vae,
    }


@router.get("/api/config/user")
async def get_user_config():
    info = await asyncio.to_thread(state.load_user_info)
    return {
        "username": info.get("username", ""),
        "profile": info.get("profile", ""),
        "startup_page": state.startup_page
    }


@router.post("/api/config/user")
async def set_user_config(
    username: str = Body(""),
    profile: str = Body(""),
    startup_page: str = Body("llm")
):
    await asyncio.to_thread(state.save_user_info, username, profile)
    state.user_username = username
    state.user_profile = profile
    if startup_page in ("llm", "qr", "home", "disabled") and startup_page != state.startup_page:
        await asyncio.to_thread(set_key, ".env", "STARTUP_PAGE", startup_page)
        state.startup_page = startup_page
    await asyncio.to_thread(load_dotenv, override=True)
    return {
        "message": "User configuration updated successfully",
        "username": state.user_username,
        "profile": state.user_profile,
        "startup_page": state.startup_page
    }


@router.get("/api/config/intiface")
async def get_intiface_config():
    devices = []
    if state.intiface_client and state.intiface_client._running:
        try:
            devices = [
                {
                    "device_index": d.device_index,
                    "feature_index": d.feature_index,
                    "device_name": d.device_name,
                    "feature_name": d.feature_name,
                    "step_count": d.step_count,
                }
                for d in state.intiface_client.find_position_devices()
            ]
        except Exception:
            pass
    return {
        "ws_url": state.intiface_ws_url,
        "connected": state.intiface_client is not None and state.intiface_client._running,
        "device_index": state.intiface_device_index,
        "feature_index": state.intiface_feature_index,
        "step_count": state.intiface_step_count,
        "device_name": state.intiface_device_name,
        "devices": devices,
    }


@router.post("/api/config/intiface/connect")
async def intiface_connect(request: Request):
    body = await request.json()
    ws_url = body.get("ws_url", "ws://127.0.0.1:12345")
    state.intiface_ws_url = ws_url
    await asyncio.to_thread(set_key, ".env", "INTIFACE_WS_URL", ws_url)

    if state.intiface_client is not None:
        try:
            await asyncio.to_thread(state.intiface_client.disconnect)
        except Exception:
            pass
        state.intiface_client = None

    client = IntifaceClient(url=ws_url, timeout=15.0)
    try:
        await asyncio.to_thread(client.connect)
    except Exception as e:
        extra = f" (last_error: {client.last_error})" if client.last_error else ""
        raise HTTPException(status_code=502, detail=f"Failed to connect to Intiface Central: {e}{extra}")

    state.intiface_client = client
    state.player.intiface_client = client
    if state.intiface_device_name:
        state.player._intiface_target = PositionFeature(
            device_index=state.intiface_device_index,
            feature_index=state.intiface_feature_index,
            device_name=state.intiface_device_name,
            step_count=state.intiface_step_count,
        )
    _log.info("Intiface Central connected: %s", ws_url)

    devices = []
    try:
        for d in client.refresh_devices(timeout=7.0, start_scan=True):
            devices.append({
                "device_index": d.device_index,
                "feature_index": d.feature_index,
                "device_name": d.device_name,
                "feature_name": d.feature_name,
                "step_count": d.step_count,
            })
    except Exception:
        pass

    return {"connected": True, "devices": devices}


@router.post("/api/config/intiface/disconnect")
async def intiface_disconnect():
    if state.intiface_client is not None:
        try:
            await asyncio.to_thread(state.intiface_client.disconnect)
        except Exception:
            pass
        state.intiface_client = None
    state.player.intiface_client = None
    state.player._intiface_target = None
    _log.info("Intiface Central disconnected")
    return {"connected": False}


@router.post("/api/config/intiface/select")
async def intiface_select(
    device_index: int = Body(...),
    feature_index: int = Body(...),
    step_count: int = Body(100),
    device_name: str = Body(""),
):
    state.intiface_device_index = device_index
    state.intiface_feature_index = feature_index
    state.intiface_step_count = step_count
    state.intiface_device_name = device_name
    await asyncio.to_thread(set_key, ".env", "INTIFACE_DEVICE_INDEX", str(device_index))
    await asyncio.to_thread(set_key, ".env", "INTIFACE_FEATURE_INDEX", str(feature_index))
    await asyncio.to_thread(set_key, ".env", "INTIFACE_STEP_COUNT", str(step_count))
    await asyncio.to_thread(set_key, ".env", "INTIFACE_DEVICE_NAME", device_name)
    _log.info("Intiface device selected: idx=%d, feat=%d, name=%s, steps=%d", device_index, feature_index, device_name, step_count)
    if state.intiface_client:
        state.player.intiface_client = state.intiface_client
    if state.player.intiface_client:
        state.player._intiface_target = PositionFeature(
            device_index=device_index,
            feature_index=feature_index,
            device_name=device_name,
            step_count=step_count,
        )
    return {"message": "Device selected successfully"}


@router.get("/api/config/intiface/devices")
async def intiface_devices():
    if not state.intiface_client or not state.intiface_client._running:
        raise HTTPException(status_code=400, detail="Intiface Central is not connected")
    devices = []
    try:
        devices = [
            {
                "device_index": d.device_index,
                "feature_index": d.feature_index,
                "device_name": d.device_name,
                "feature_name": d.feature_name,
                "step_count": d.step_count,
            }
            for d in state.intiface_client.find_position_devices()
        ]
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"devices": devices}


@router.get("/api/config/custom-modules")
async def get_custom_modules():
    return await asyncio.to_thread(state.load_custom_modules)


@router.post("/api/config/custom-modules")
async def create_custom_module(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Module name is required")
    modules = await asyncio.to_thread(state.load_custom_modules)
    if name in modules:
        raise HTTPException(status_code=409, detail="Module already exists")
    modules[name] = {
        "system_prompt": body.get("system_prompt", ""),
        "position": body.get("position", "end"),
        "messages": body.get("messages", "")
    }
    await asyncio.to_thread(state.save_custom_modules, modules)
    return {"message": "Module created", "name": name}


@router.put("/api/config/custom-modules/{name:path}")
async def update_custom_module(name: str, request: Request):
    body = await request.json()
    modules = await asyncio.to_thread(state.load_custom_modules)
    if name not in modules:
        raise HTTPException(status_code=404, detail="Module not found")
    new_name = body.get("name", name).strip()
    if new_name != name:
        if new_name in modules:
            raise HTTPException(status_code=409, detail="Module name already exists")
        modules[new_name] = modules.pop(name)
    modules[new_name].update({
        "system_prompt": body.get("system_prompt", modules[new_name].get("system_prompt", "")),
        "position": body.get("position", modules[new_name].get("position", "end")),
        "messages": body.get("messages", modules[new_name].get("messages", ""))
    })
    await asyncio.to_thread(state.save_custom_modules, modules)
    return {"message": "Module updated", "name": new_name}


@router.delete("/api/config/custom-modules/{name:path}")
async def delete_custom_module(name: str):
    modules = await asyncio.to_thread(state.load_custom_modules)
    if name not in modules:
        raise HTTPException(status_code=404, detail="Module not found")
    del modules[name]
    await asyncio.to_thread(state.save_custom_modules, modules)
    return {"message": "Module deleted"}


@router.post("/api/config/handy/test")
async def handy_test(request: Request):
    body = await request.json()
    connection_key = body.get("connection_key", state.handy_connection_key)
    api_version = body.get("api_version", state.handy_api_version or "v3")
    if not connection_key:
        raise HTTPException(status_code=400, detail="Connection key is required")

    client = HandyClient(
        api_key=connection_key,
        api_version=api_version,
        timeout=10.0,
    )
    connected = await asyncio.to_thread(client.connect, verify=True)
    status = None
    if connected:
        try:
            status = await asyncio.to_thread(client.get_status)
        except Exception:
            pass
    return {"connected": connected, "status": status}
