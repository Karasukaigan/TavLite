from fastapi import APIRouter, Query, Body, HTTPException
from dotenv import set_key
from src import state

router = APIRouter(tags=["script"])


@router.post("/api/script")
async def load(script_data: dict):
    state.joystick_controller.stop_joystick()
    state.player.stop()
    result = state.player.load_script(script_data)
    return result


@router.get("/api/script/play")
async def play(at: int = Query(0, description="Start time, unit: milliseconds")):
    state.joystick_controller.stop_joystick()
    result = state.player.play(at)
    return result


@router.get("/api/script/stop")
async def stop():
    result = state.player.stop()
    return result


@router.post("/api/script/custom")
async def custom_play(
    range: int = Body(100),
    inverted: bool = Body(False),
    max_pos: int = Body(100),
    min_pos: int = Body(0),
    freq: float = Body(1.0),
    decline_ratio: float = Body(0.5),
    start_pos: int = Body(None),
    loop_count: int = Body(100),
    custom_actions: list = Body(None)
):
    try:
        state.player.custom_play(
            range=range,
            inverted=inverted,
            max_pos=max_pos,
            min_pos=min_pos,
            freq=freq,
            decline_ratio=decline_ratio,
            start_pos=start_pos,
            loop_count=loop_count,
            custom_actions=custom_actions
        )
        return {"message": "Custom play started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})


@router.get("/api/offset")
async def adjust_offset(ms: int = Query(..., description="Offset adjustment value, unit: milliseconds")):
    old_offset = state.player.offset_value
    state.player.offset_value += int(ms)
    set_key(".env", "OFFSET", str(state.player.offset_value))
    return {
        "message": "Offset adjusted successfully",
        "old_offset": old_offset,
        "new_offset": state.player.offset_value,
        "adjustment": ms
    }
