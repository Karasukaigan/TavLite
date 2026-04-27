from fastapi import APIRouter, Body, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import threading
from queue import Queue, Empty
from src import state

router = APIRouter(tags=["llm"])


@router.get("/api/llm/test")
async def test_llm_connection():
    success = state.llm_client.test_connection()
    if not success:
        raise HTTPException(status_code=500, detail={"error": "Failed to connect to LLM"})
    return {"success": success}


@router.get("/api/llm/model")
async def get_llm_models():
    models = state.llm_client.get_model_list()
    return {"models": models}


@router.post("/api/llm/chat")
async def chat_with_llm(
    request: Request,
    user_message: str = Body(...),
    model: str = Body(None),
    image_base64: str = Body(None),
    system_prompt: str = Body(""),
    context_messages: list = Body(None),
    temperature: float = Body(None),
    num_predict: int = Body(32000)
):
    actual_temperature = temperature if temperature is not None else state.llm_temperature

    async def generate_stream():
        token_queue = Queue()
        stop_event = threading.Event()

        def background_chat():
            try:
                gen = state.llm_client.chat(
                    user_message=user_message,
                    model=model,
                    image_base64=image_base64,
                    system_prompt=system_prompt,
                    context_messages=context_messages,
                    temperature=actual_temperature,
                    num_predict=num_predict,
                    stop_event=stop_event
                )
                for token in gen:
                    if stop_event.is_set():
                        break
                    token_queue.put(("token", token))
                token_queue.put(("done", None))
            except Exception as e:
                if not stop_event.is_set():
                    token_queue.put(("error", str(e)))

        thread = threading.Thread(target=background_chat, daemon=True)
        thread.start()

        try:
            while True:
                if await request.is_disconnected():
                    stop_event.set()
                    break

                try:
                    item_type, value = token_queue.get(timeout=0.1)
                    if item_type == "token":
                        yield f"data: {json.dumps({'token': value})}\n\n"
                    elif item_type == "error":
                        if not await request.is_disconnected():
                            yield f"data: {json.dumps({'token': '__ERROR__ Internal stream error: ' + value})}\n\n"
                        break
                    elif item_type == "done":
                        break
                except Empty:
                    continue
        finally:
            stop_event.set()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
