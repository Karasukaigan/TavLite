from fastapi import APIRouter, Body, HTTPException
import os
import shutil
from src import state

router = APIRouter(tags=["t2i"])


@router.post("/api/t2i")
async def text_to_image(prompt: str = Body(..., embed=True)):
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    image_path = await state.comfyui_client.run_t2i(prompt=prompt.strip())
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to generate image via ComfyUI")
    return {"image_url": image_path}


@router.delete("/api/t2i/cache")
async def clear_t2i_cache():
    comfyui_img_dir = os.path.join(state.public_dir, "img", "comfyui")
    if not os.path.exists(comfyui_img_dir):
        return {"message": "Cache directory does not exist", "deleted_count": 0}
    deleted_count = 0
    for filename in os.listdir(comfyui_img_dir):
        file_path = os.path.join(comfyui_img_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                deleted_count += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_count += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete {file_path}: {str(e)}")
    return {
        "message": "ComfyUI image cache cleared successfully",
        "deleted_count": deleted_count
    }
