from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ErrorEvent,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.chatkit_store import SQLiteChatKitStore
from app.item_utils import extract_item_text, infer_item_role
from app.llm import LiquidLangChainService
from app.qdrant_memory import QdrantConversationMemory


@dataclass
class RequestContext:
    user_id: str
    locale: str = "en"


class LiquidChatKitServer(ChatKitServer[RequestContext]):
    """Self-hosted ChatKit server that calls Liquid AI through LangChain."""

    def __init__(self, store: SQLiteChatKitStore, llm_service: LiquidLangChainService, memory: QdrantConversationMemory):
        super().__init__(store=store)
        self.llm_service = llm_service
        self.memory = memory

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        question = extract_item_text(input) if input is not None else ""
        try:
            items_page = await self.store.load_thread_items(
                thread.id,
                after=None,
                limit=24,
                order="asc",
                context=context,
            )
            recent_messages = self._to_langchain_messages(items_page.data)
            if not question:
                last_human = next((m for m in reversed(recent_messages) if isinstance(m, HumanMessage)), None)
                question = str(last_human.content) if last_human else "Hello"

            answer = await self.llm_service.generate(
                user_id=context.user_id,
                question=question,
                recent_messages=recent_messages,
            )
            if not answer:
                answer = "I could not generate a response from the Liquid model. Please try again."

            assistant_item = AssistantMessageItem(
                thread_id=thread.id,
                id=self.store.generate_item_id("message", thread, context),
                created_at=datetime.now(timezone.utc),
                content=[AssistantMessageContent(text=answer)],
            )

            # The ChatKit runtime stores ThreadItemDoneEvent items, but this upsert makes persistence explicit.
            await self.store.save_item(thread.id, assistant_item, context=context)
            await asyncio.to_thread(
                self.memory.add_turn,
                user_id=context.user_id,
                thread_id=thread.id,
                user_text=question,
                assistant_text=answer,
            )
            yield ThreadItemDoneEvent(item=assistant_item)
        except Exception as exc:
            yield ErrorEvent(
                message=(
                    "The chatbot could not reach the Liquid AI model or Qdrant memory service. "
                    f"Details: {exc}"
                ),
                allow_retry=True,
            )

    def _to_langchain_messages(self, items: list[object]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for item in items:
            text = extract_item_text(item)
            if not text:
                continue
            role = infer_item_role(item)
            if role == "user":
                messages.append(HumanMessage(content=text))
            elif role == "assistant":
                messages.append(AIMessage(content=text))
        return messages
