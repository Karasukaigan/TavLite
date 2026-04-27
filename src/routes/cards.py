import time
from fastapi import APIRouter, Body, HTTPException
from src import state

router = APIRouter(tags=["cards"])


@router.get("/api/cards")
async def list_cards(mode: str = "summary"):
    cards = state.load_cards()
    if mode == "full":
        return cards
    if mode == "chat":
        return {name: {"system_prompt": c.get("system_prompt", ""), "context": c.get("context", []), "messages": c.get("messages", [])} for name, c in cards.items()}
    return {name: {"updated_at": c.get("updated_at", 0)} for name, c in cards.items()}


@router.get("/api/cards/{name}")
async def get_card(name: str, field: str = None):
    cards = state.load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    if field == "concept_art":
        return {"concept_art": cards[name].get("concept_art", "")}
    return {name: cards[name]}


@router.post("/api/cards")
async def create_card(name: str = Body(...), prompt: str = Body(""), content: str = Body(""), concept_art: str = Body(""), messages: list = Body([])):
    cards = state.load_cards()
    if name in cards:
        raise HTTPException(status_code=400, detail="card already exists")
    card = {"system_prompt": prompt}
    if content:
        card["context"] = [{"role": "assistant", "content": content}]
    if messages:
        card["messages"] = messages
    if concept_art:
        card["concept_art"] = concept_art
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    state.save_cards(cards)
    return {"message": "card created successfully"}


@router.put("/api/cards/{name}")
async def update_card(name: str, prompt: str = Body(""), content: str = Body(""), concept_art: str = Body(""), messages: list = Body([])):
    cards = state.load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    card = {"system_prompt": prompt}
    if content:
        card["context"] = [{"role": "assistant", "content": content}]
    else:
        card.pop("context", None)
    if messages:
        card["messages"] = messages
    else:
        card.pop("messages", None)
    if concept_art:
        card["concept_art"] = concept_art
    else:
        card.pop("concept_art", None)
    card["updated_at"] = int(time.time() * 1000)
    cards[name] = card
    state.save_cards(cards)
    return {"message": "card updated successfully"}


@router.delete("/api/cards/{name}")
async def delete_card(name: str):
    cards = state.load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    del cards[name]
    state.save_cards(cards)
    return {"message": "card deleted successfully"}
