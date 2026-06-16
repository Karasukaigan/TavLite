import asyncio
from fastapi import APIRouter, Body, HTTPException
import os
import shutil
from src import state
from src.logger import get_runtime_logger
_log = get_runtime_logger("t2i")

router = APIRouter(tags=["t2i"])


def _delete_cache_dir(dir_path: str) -> int:
    deleted_count = 0
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                deleted_count += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_count += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete {file_path}: {str(e)}")
    return deleted_count


@router.post("/api/t2i")
async def text_to_image(prompt: str = Body(..., embed=True)):
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if not state.comfyui_client.type or state.comfyui_client.type == "disabled":
        raise HTTPException(status_code=400, detail="T2I is disabled")
    workflow_path = state.comfyui_client.workflow_path
    if not os.path.exists(workflow_path):
        _log.error("T2I workflow file not found: %s", workflow_path)
        raise HTTPException(status_code=500, detail=f"Workflow file not found: {workflow_path}")
    image_path = await state.comfyui_client.run_t2i(prompt=prompt.strip())
    if not image_path:
        _log.warning("T2I generation failed for prompt: %s", prompt.strip()[:60])
        raise HTTPException(status_code=500, detail="Failed to generate image via ComfyUI")
    _log.info("T2I image generated: %s", image_path)
    return {"image_url": image_path}


@router.delete("/api/t2i/cache")
async def clear_t2i_cache():
    comfyui_img_dir = os.path.join(state.public_dir, "img", "comfyui")
    exists = await asyncio.to_thread(os.path.exists, comfyui_img_dir)
    if not exists:
        return {"message": "Cache directory does not exist", "deleted_count": 0}
    deleted_count = await asyncio.to_thread(_delete_cache_dir, comfyui_img_dir)
    return {
        "message": "ComfyUI image cache cleared successfully",
        "deleted_count": deleted_count
    }
