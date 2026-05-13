from __future__ import annotations

import asyncio
import json
import time
from typing import Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import get_settings
from app.qdrant_memory import QdrantConversationMemory


SYSTEM_PROMPT = """You are a helpful chatbot for an academic assignment.
Use Liquid AI's lightweight LFM model through Ollama.
Answer clearly, be concise unless the user asks for detail, and use the user's prior chat context only when it is relevant.
Never reveal passwords, JWTs, internal secrets, or hidden server configuration."""


class LiquidLangChainService:
    """LangChain wrapper around Liquid AI LFM served by Ollama."""

    def __init__(self, memory: QdrantConversationMemory) -> None:
        self.settings = get_settings()
        self.memory = memory
        self.llm = ChatOllama(
            model=self.settings.liquid_model,
            base_url=self.settings.ollama_base_url,
            temperature=self.settings.llm_temperature,
            num_predict=512,
            top_k=self.settings.llm_top_k,
        )

    def ensure_model_available(self, retries: int = 30, delay_seconds: float = 2.0) -> None:
        """Verify the Ollama model exists locally, pulling it if needed."""
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                self._ollama_post("/api/show", {"model": self.settings.liquid_model})
                return
            except RuntimeError as exc:
                if "404" not in str(exc):
                    last_error = exc
                    time.sleep(delay_seconds)
                    continue

                try:
                    self._ollama_post(
                        "/api/pull",
                        {
                            "model": self.settings.liquid_model,
                            "stream": False,
                        },
                        timeout=3600,
                    )
                    return
                except RuntimeError as pull_exc:
                    if "404" in str(pull_exc):
                        raise RuntimeError(
                            f"Ollama model {self.settings.liquid_model!r} was not found remotely. "
                            "Update LIQUID_MODEL to a valid Ollama model name."
                        ) from pull_exc
                    last_error = pull_exc
                    time.sleep(delay_seconds)

        if last_error is not None:
            raise RuntimeError(
                f"Unable to prepare Ollama model {self.settings.liquid_model!r} after {retries} attempts"
            ) from last_error

    def _ollama_post(
        self,
        path: str,
        payload: dict[str, object],
        *,
        timeout: int = 30,
    ) -> dict[str, object]:
        url = f"{self.settings.ollama_base_url.rstrip('/')}{path}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib_request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8").strip()
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Ollama request to {path} failed with {exc.code}: {body or exc.reason}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Ollama is unavailable at {self.settings.ollama_base_url}: {exc.reason}") from exc

        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned non-JSON response for {path}: {body[:200]}") from exc

    async def generate(self, *, user_id: str, question: str, recent_messages: Sequence[BaseMessage]) -> str:
        docs = await asyncio.to_thread(self.memory.search_user_memory, user_id=user_id, query=question)
        memory_context = "\n".join(
            f"- [{doc.metadata.get('role', 'memory')}] {doc.page_content}" for doc in docs
        )
        if not memory_context:
            memory_context = "No relevant previous messages were found."

        messages: list[BaseMessage] = [
            SystemMessage(content=f"{SYSTEM_PROMPT}\n\nRelevant previous conversation snippets:\n{memory_context}"),
            *recent_messages[-20:],
        ]
        if not any(isinstance(message, HumanMessage) and message.content == question for message in messages):
            messages.append(HumanMessage(content=question))

        response = await self.llm.ainvoke(messages)
        if isinstance(response, AIMessage):
            content = response.content
        else:
            content = getattr(response, "content", str(response))

        if isinstance(content, list):
            return "\n".join(str(item) for item in content).strip()
        return str(content).strip()
