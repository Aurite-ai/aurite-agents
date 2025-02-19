from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from src.clients.client import MCPClient
from src.clients.client_handler import get_client, clear_all_clients

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# data models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[Message]
    max_tokens: int | None = 512
    temperature: float | None = 0.1
    stream: bool | None = False


async def _resp_async_generator(text_resp: str, model):
    tokens = text_resp.split(" ")

    # Generate a unique ID for this completion
    completion_id = f"chatcmpl-{uuid.uuid4()}"

    # Initial chunk with role
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "fp_" + uuid.uuid4().hex[:12],
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "logprobs": None, "finish_reason": None}],
    }
    yield f"data: {json.dumps(chunk)}\n\n"

    # Content chunks
    for token in tokens:
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "system_fingerprint": "fp_" + uuid.uuid4().hex[:12],
            "choices": [{"index": 0, "delta": {"content": token + " "}, "logprobs": None, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.01)

    # Final chunk
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "fp_" + uuid.uuid4().hex[:12],
        "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(chunk)}\n\n"

    # Stream termination
    yield "data: [DONE]\n\n"


@router.post("/completions")
async def chat_completions(request: ChatCompletionRequest):
    #logger.info(f"request recieved: {request}")
    
    client = await get_client(request.model)
    logger.info(client)
    logger.info(request.messages[-1].content)

    if client:
        try:
            resp_content = await client.process_query(request.messages[-1].content)
            await clear_all_clients()
        except Exception as e:
            resp_content = f"Error occured: {str(e)}"
    else:
        resp_content = "Model not recognized"

    if request.stream:
        return StreamingResponse(_resp_async_generator(resp_content, request.model), media_type="text/event-stream")

    return {
        "id": "0",
        "object": "chat.completion",
        "created": time.time(),
        "model": request.model,
        "choices": [{"message": Message(role="assistant", content=resp_content)}],
    }
