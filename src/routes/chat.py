import asyncio
from fastapi import APIRouter, Body, HTTPException
import os
import json
from src import state
from src.logger import get_runtime_logger
_log = get_runtime_logger("chat")

router = APIRouter(tags=["chat"])

CHATS_DIR = os.path.join(state.public_dir, "json", "chats")


def _ensure_chats_dir():
    os.makedirs(CHATS_DIR, exist_ok=True)


def _safe_card_name(name: str) -> str:
    return name.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_').replace('|', '_').replace('<', '_').replace('>', '_').replace('"', '_').replace('?', '_').replace('*', '_')


def _write_json(filepath: str, data: dict):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _clear_cache_files() -> int:
    deleted_count = 0
    for fname in os.listdir(CHATS_DIR):
        if fname.endswith(".json"):
            filepath = os.path.join(CHATS_DIR, fname)
            try:
                os.remove(filepath)
                deleted_count += 1
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete {filepath}: {str(e)}")
    return deleted_count


@router.post("/api/chat/cache")
async def save_chat_cache(
    card_name: str = Body(...),
    context: list = Body(...),
    chat_started: bool = Body(...),
    selected_message_idx: int = Body(...),
    system_prompt: str = Body(""),
    role: str = Body(""),
    mode: str = Body(""),
    t2i: str = Body("")
):
    await asyncio.to_thread(_ensure_chats_dir)
    safe_name = _safe_card_name(card_name)
    filepath = os.path.join(CHATS_DIR, f"{safe_name}.json")
    data = {
        "context": context,
        "chat_started": chat_started,
        "selected_message_idx": selected_message_idx,
        "system_prompt": system_prompt,
        "role": role,
        "mode": mode,
        "t2i": t2i
    }
    await asyncio.to_thread(
        lambda: _write_json(filepath, data)
    )
    _log.info("Saved chat cache for '%s' (%d context msgs)", card_name, len(context))
    return {"message": "Chat cache saved", "card_name": card_name}


@router.get("/api/chat/cache/{card_name}")
async def get_chat_cache(card_name: str):
    await asyncio.to_thread(_ensure_chats_dir)
    safe_name = _safe_card_name(card_name)
    filepath = os.path.join(CHATS_DIR, f"{safe_name}.json")
    exists = await asyncio.to_thread(os.path.exists, filepath)
    if not exists:
        raise HTTPException(status_code=404, detail="Cache not found")
    data = await asyncio.to_thread(_read_json, filepath)
    return data


@router.delete("/api/chat/cache/{card_name}")
async def delete_chat_cache(card_name: str):
    await asyncio.to_thread(_ensure_chats_dir)
    safe_name = _safe_card_name(card_name)
    filepath = os.path.join(CHATS_DIR, f"{safe_name}.json")
    exists = await asyncio.to_thread(os.path.exists, filepath)
    if not exists:
        return {"message": "Chat cache not found", "card_name": card_name}
    await asyncio.to_thread(os.remove, filepath)
    _log.info("Deleted chat cache for '%s'", card_name)
    return {"message": "Chat cache deleted", "card_name": card_name}


@router.delete("/api/chat/cache")
async def clear_chat_cache():
    await asyncio.to_thread(_ensure_chats_dir)
    exists = await asyncio.to_thread(os.path.exists, CHATS_DIR)
    if not exists:
        return {"message": "Chat cache cleared successfully", "deleted_count": 0}
    deleted_count = await asyncio.to_thread(_clear_cache_files)
    return {
        "message": "Chat cache cleared successfully",
        "deleted_count": deleted_count
    }
