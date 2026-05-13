from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from chatkit.server import StreamingResult

from app.auth import get_current_user
from app.chatkit_server import LiquidChatKitServer, RequestContext
from app.chatkit_store import SQLiteChatKitStore
from app.config import get_settings
from app.database import create_db_and_tables
from app.llm import LiquidLangChainService
from app.models import User
from app.qdrant_memory import QdrantConversationMemory
from app.routes_auth import router as auth_router
from app.routes_health import router as health_router
from app.routes_threads import router as threads_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    store = SQLiteChatKitStore()
    memory = QdrantConversationMemory()
    llm_service = LiquidLangChainService(memory=memory)
    llm_service.ensure_model_available()
    app.state.chatkit_server = LiquidChatKitServer(
        store=store,
        llm_service=llm_service,
        memory=memory,
    )
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(threads_router, prefix=settings.api_prefix)


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    context = RequestContext(
        user_id=current_user.id,
        locale=request.headers.get("accept-language", "en").split(",")[0],
    )
    result = await request.app.state.chatkit_server.process(await request.body(), context=context)
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
