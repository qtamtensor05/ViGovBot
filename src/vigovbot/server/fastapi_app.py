"""FastAPI adapter for the existing chat application contract."""

from __future__ import annotations

import asyncio
import logging
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from vigovbot.rag.pipeline import graph_inference_session, inference_session, prepare
from vigovbot.server.app import ChatApplication

LOG = logging.getLogger(__name__)
_LOCAL_UI_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def create_app(config, retriever, tokenizer, *, graph_retriever=None) -> FastAPI:
    """Expose the stable ChatApplication payload through FastAPI routes."""
    application = ChatApplication(config, retriever, tokenizer, graph_retriever=graph_retriever)
    api = FastAPI(title="ViGovBot GraphRAG API", version="0.2.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=_LOCAL_UI_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @api.get("/api/health")
    def health():
        return {"status": "ok", "graph_enabled": graph_retriever is not None}

    @api.get("/api/models")
    def models():
        return {"models": application.public_models()}

    @api.post("/api/chat")
    def chat(payload: dict):
        try:
            return application.chat(payload)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOG.exception("Lỗi khi trả lời câu hỏi qua FastAPI")
            raise HTTPException(status_code=500, detail="Không thể xử lý câu hỏi. Hãy xem log của server.") from exc

    @api.post("/api/chat/stream")
    async def chat_stream(payload: dict):
        events = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def emit(event):
            loop.call_soon_threadsafe(events.put_nowait, event)

        try:
            application.start_chat(payload, emit)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def encode():
            while True:
                event = await events.get()
                if event is None:
                    return
                event_type = event["type"]
                data = {key: value for key, value in event.items() if key != "type"}
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            encode(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return api


def serve(config, host="127.0.0.1", port=8000):
    """Load inference resources once and host the FastAPI adapter until shutdown."""
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("FastAPI server cần cài extra 'rag'") from exc
    paths = prepare(config)
    with inference_session(config, paths) as (retriever, tokenizer), graph_inference_session(config) as graph_retriever:
        LOG.info("FastAPI đang chạy tại http://%s:%d", host, port)
        uvicorn.run(create_app(config, retriever, tokenizer, graph_retriever=graph_retriever), host=host, port=port)
