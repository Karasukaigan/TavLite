import asyncio
import time
import json as json_mod
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
from src import state
from src.card_parser import SillyTavernCardParser
from src.state import _save_concept_art_file, _delete_concept_art_file, _safe_image_name, _save_card_image_file, _save_card_image_from_base64, _delete_card_image_file
from src.logger import get_runtime_logger
_log = get_runtime_logger("cards")

router = APIRouter(tags=["cards"])


@router.get("/api/cards")
async def list_cards(mode: str = "summary", with_art: bool = False, q: str = ""):
    cards = await state.async_load_cards()
    if q:
        keywords = [kw.strip().lower() for kw in q.split() if kw.strip()]
        if keywords:
            cards = {
                name: c for name, c in cards.items()
                if all(
                    kw in name.lower() or
                    any(kw in tag.lower() for tag in c.get("tags", []))
                    for kw in keywords
                )
            }
    if mode == "full":
        result = cards
    elif mode == "chat":
        result = {name: {"system_prompt": c.get("system_prompt", ""), "context": c.get("context", []), "messages": c.get("messages", []), "html": c.get("html", "")} for name, c in cards.items()}
    else:
        result = {name: {"updated_at": c.get("updated_at", 0)} for name, c in cards.items()}
    if with_art:
        for name in result:
            result[name]["concept_art"] = cards[name].get("concept_art", "")
    return result


@router.get("/api/cards/{name}")
async def get_card(name: str, field: str = None):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    if field == "concept_art":
        return {"concept_art": cards[name].get("concept_art", "")}
    return {name: cards[name]}


@router.post("/api/cards")
async def create_card(name: str = Body(...), prompt: str = Body(""), content: str = Body(""), concept_art: str = Body(""), messages: list = Body([]), context: list = Body(None), tags: list = Body([]), html: str = Body(""), images: dict = Body(None)):
    cards = await state.async_load_cards()
    if name in cards:
        raise HTTPException(status_code=400, detail="card already exists")
    card = {"system_prompt": prompt}
    if context is not None:
        card["context"] = context
    elif content:
        card["context"] = [{"role": "assistant", "content": content}]
    if messages:
        card["messages"] = messages
    if tags:
        card["tags"] = tags
    if html:
        card["html"] = html
    if concept_art:
        try:
            card["concept_art"] = _save_concept_art_file(concept_art, name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if images:
        processed_images = {}
        for img_key, img_val in images.items():
            if isinstance(img_val, dict) and img_val.get("data"):
                data = img_val["data"]
                if data.startswith("data:"):
                    try:
                        data = await asyncio.to_thread(_save_card_image_from_base64, data, name, img_key)
                    except Exception:
                        continue
                processed_images[img_key] = {"data": data, "description": img_val.get("description", "")}
        if processed_images:
            card["images"] = processed_images
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    await state.async_save_cards(cards, name)
    _log.info("Created card '%s' (%d msgs, %d tags)", name, len(messages), len(tags))
    return {"message": "card created successfully"}


@router.put("/api/cards/{name}")
async def update_card(name: str, prompt: str = Body(""), content: str = Body(""), concept_art: str = Body(""), messages: list = Body([]), tags: list = Body([]), html: str = Body(None), images: dict = Body(None)):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    card = dict(cards[name])
    card["system_prompt"] = prompt
    if content:
        card["context"] = [{"role": "assistant", "content": content}]
    else:
        card.pop("context", None)
    if messages:
        card["messages"] = messages
    else:
        card.pop("messages", None)
    if tags:
        card["tags"] = tags
    else:
        card.pop("tags", None)
    if html is not None:
        if html:
            card["html"] = html
        else:
            card.pop("html", None)
    if concept_art:
        try:
            card["concept_art"] = _save_concept_art_file(concept_art, name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        _delete_concept_art_file(name)
        card.pop("concept_art", None)
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    await state.async_save_cards(cards, name)
    _log.info("Updated card '%s'", name)
    return {"message": "card updated successfully"}


@router.delete("/api/cards/{name}")
async def delete_card(name: str):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    _delete_concept_art_file(name)
    del cards[name]
    await state.async_save_cards(cards, name)
    _log.info("Deleted card '%s'", name)
    return {"message": "card deleted successfully"}


@router.post("/api/cards/import/png")
async def import_card_png(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="no file provided")
    if file.content_type not in ("image/png", "image/webp") and not (file.filename or "").lower().endswith(".png"):
        if not (file.filename or "").lower().endswith(".png"):
            raise HTTPException(status_code=400, detail="file must be a PNG image")

    raw_bytes = await file.read()
    if len(raw_bytes) < 8 or raw_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        raise HTTPException(status_code=400, detail="file is not a valid PNG")

    try:
        parser = SillyTavernCardParser()
        result = await asyncio.to_thread(parser.parse_png_character_card, raw_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"failed to parse character card: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unexpected error during parsing: {e}")

    processed = await asyncio.to_thread(parser.process_data, result)
    if processed is False:
        raise HTTPException(status_code=400, detail="invalid character card data: could not extract card info")

    card_name = next(iter(processed.keys()))

    cards = await state.async_load_cards()
    if card_name in cards:
        raise HTTPException(status_code=409, detail=f"card '{card_name}' already exists")

    card_data = processed[card_name]
    if "concept_art" in card_data:
        try:
            card_data["concept_art"] = _save_concept_art_file(card_data["concept_art"], card_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    cards[card_name] = card_data
    cards[card_name]["updated_at"] = int(time.time() * 1000)
    await state.async_save_cards(cards, card_name)
    _log.info("Imported PNG card '%s'", card_name)

    return {
        "message": "card imported successfully",
        "name": card_name,
        "has_concept_art": "concept_art" in card_data,
        "has_context": "context" in card_data,
        "has_messages": "messages" in card_data and len(card_data.get("messages", [])) > 0
    }


@router.post("/api/cards/import/json")
async def import_card_json(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="no file provided")
    raw_bytes = await file.read()
    try:
        imported = json_mod.loads(raw_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON file")

    if not isinstance(imported, dict):
        raise HTTPException(status_code=400, detail="invalid card structure")

    cards = await state.async_load_cards()
    success_count = 0
    errors = []

    for card_name, card_data in imported.items():
        if not isinstance(card_data, dict):
            errors.append(f"'{card_name}': invalid data")
            continue
        if card_name in cards:
            errors.append(f"'{card_name}': already exists")
            continue

        if card_data.get("concept_art"):
            try:
                card_data["concept_art"] = _save_concept_art_file(card_data["concept_art"], card_name)
            except Exception:
                card_data.pop("concept_art", None)

        if card_data.get("images") and isinstance(card_data["images"], dict):
            processed_images = {}
            for img_key, img_val in card_data["images"].items():
                if isinstance(img_val, dict) and img_val.get("data"):
                    data = img_val["data"]
                    if data.startswith("data:"):
                        try:
                            data = _save_card_image_from_base64(data, card_name, img_key)
                        except Exception:
                            continue
                    processed_images[img_key] = {"data": data, "description": img_val.get("description", "")}
            if processed_images:
                card_data["images"] = processed_images
            else:
                card_data.pop("images", None)

        card_data["updated_at"] = int(time.time() * 1000)
        cards[card_name] = card_data
        await state.async_save_cards(cards, card_name)
        success_count += 1
        _log.info("Imported JSON card '%s'", card_name)

    return {"message": f"imported {success_count} card(s)", "success": success_count, "errors": errors}


@router.post("/api/cards/{name}/images")
async def upload_card_image(name: str, file: UploadFile = File(...), image_name: str = Form(""), description: str = Form("")):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")

    if not image_name:
        image_name = file.filename or "image.png"
    safe_name = _safe_image_name(image_name)
    if not safe_name or safe_name == '_':
        raise HTTPException(status_code=400, detail="invalid image name")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="empty file")

    url = await asyncio.to_thread(_save_card_image_file, raw_bytes, name, safe_name)

    card = dict(cards[name])
    if "images" not in card or not isinstance(card.get("images"), dict):
        card["images"] = {}
    card["images"][safe_name] = {"data": url, "description": description}
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    await state.async_save_cards(cards, name)
    _log.info("Uploaded image '%s' for card '%s'", safe_name, name)
    return {"url": url, "image_name": safe_name}


@router.delete("/api/cards/{name}/images/{image_key:path}")
async def delete_card_image(name: str, image_key: str):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    card = dict(cards[name])
    images = card.get("images", {})
    if image_key not in images:
        raise HTTPException(status_code=404, detail="image not found")

    await asyncio.to_thread(_delete_card_image_file, name, image_key)
    del images[image_key]
    if images:
        card["images"] = images
    else:
        card.pop("images", None)
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    await state.async_save_cards(cards, name)
    _log.info("Deleted image '%s' from card '%s'", image_key, name)
    return {"message": "image deleted"}


@router.put("/api/cards/{name}/images/{image_key:path}")
async def update_card_image_desc(name: str, image_key: str, description: str = Body("", embed=True)):
    cards = await state.async_load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    card = dict(cards[name])
    images = card.get("images", {})
    if image_key not in images:
        raise HTTPException(status_code=404, detail="image not found")

    images[image_key]["description"] = description
    card["images"] = images
    cards[name] = card
    await state.async_save_cards(cards, name)
    _log.info("Updated description for image '%s' in card '%s'", image_key, name)
    return {"message": "description updated"}
