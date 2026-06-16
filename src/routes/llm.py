import asyncio
import json
import threading
from queue import Queue, Empty
from fastapi import APIRouter, Body, Request, HTTPException
from fastapi.responses import StreamingResponse
from src import state
from src.logger import get_runtime_logger
import tiktoken

_log = get_runtime_logger("llm")

_token_encoding = None

def _get_encoding():
    global _token_encoding
    if _token_encoding is None:
        _token_encoding = tiktoken.get_encoding("cl100k_base")
    return _token_encoding

router = APIRouter(tags=["llm"])


@router.get("/api/llm/test")
async def test_llm_connection():
    success = await asyncio.to_thread(state.llm_client.test_connection)
    if not success:
        _log.warning("LLM connection test failed")
        raise HTTPException(status_code=500, detail={"error": "Failed to connect to LLM"})
    _log.info("LLM connection test successful")
    return {"success": success}


@router.get("/api/llm/model")
async def get_llm_models():
    models = await asyncio.to_thread(state.llm_client.get_model_list)
    return {"models": models}


@router.post("/api/llm/count-tokens")
async def count_tokens(body: dict = Body(...)):
    text = body.get("text", "")
    try:
        tokens = await asyncio.to_thread(lambda: _get_encoding().encode(text))
        return {"count": len(tokens)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token counting failed: {e}")


@router.post("/api/llm/chat")
async def chat_with_llm(
    request: Request,
    user_message: str = Body(...),
    model: str = Body(None),
    image_base64: str = Body(None),
    system_prompt: str = Body(""),
    context_messages: list = Body(None),
    temperature: float = Body(None),
    num_predict: int = Body(32000),
    reasoning_effort: str = Body(None)
):
    actual_temperature = temperature if temperature is not None else state.llm_temperature
    actual_reasoning_effort = reasoning_effort if reasoning_effort is not None else state.llm_reasoning_effort
    _log.info("Chat stream start: model=%s, msg_len=%d, ctx=%d", model or state.llm_client.model, len(user_message), len(context_messages or []))

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
                    stop_event=stop_event,
                    reasoning_effort=actual_reasoning_effort
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
                    item_type, value = token_queue.get_nowait()
                    if item_type == "token":
                        if value.startswith("__USAGE__"):
                            usage_data = value[len("__USAGE__"):]
                            yield f"data: {json.dumps({'token': f'<usage>{usage_data}</usage>'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'token': value})}\n\n"
                    elif item_type == "error":
                        if not await request.is_disconnected():
                            yield f"data: {json.dumps({'token': '__ERROR__ Internal stream error: ' + value})}\n\n"
                        break
                    elif item_type == "done":
                        break
                except Empty:
                    await asyncio.sleep(0.01)
                    continue
        finally:
            stop_event.set()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")



