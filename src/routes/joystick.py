import asyncio
from fastapi import APIRouter
from src import state
from src.logger import get_runtime_logger
_log = get_runtime_logger("joystick")

router = APIRouter(tags=["joystick"])


@router.post("/api/devices/joystick/start")
async def start_joystick():
    await asyncio.to_thread(state.player.stop)
    result = await asyncio.to_thread(state.joystick_controller.start_joystick)
    _log.info("Joystick started")
    return result


@router.post("/api/devices/joystick/stop")
async def stop_joystick():
    result = await asyncio.to_thread(state.joystick_controller.stop_joystick)
    _log.info("Joystick stopped")
    return result


@router.get("/api/devices/joystick")
async def joystick_status():
    result = await asyncio.to_thread(state.joystick_controller.joystick_status)
    return result
