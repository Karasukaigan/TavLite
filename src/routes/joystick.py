from fastapi import APIRouter
from src import state

router = APIRouter(tags=["joystick"])


@router.post("/api/devices/joystick/start")
async def start_joystick():
    state.player.stop()
    result = state.joystick_controller.start_joystick()
    return result


@router.post("/api/devices/joystick/stop")
async def stop_joystick():
    result = state.joystick_controller.stop_joystick()
    return result


@router.get("/api/devices/joystick")
async def joystick_status():
    result = state.joystick_controller.joystick_status()
    return result
