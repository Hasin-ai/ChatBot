from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams

from app.config import get_settings


class QdrantConversationMemory:
    """Stores conversation turns in Qdrant for user-scoped semantic recall."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embeddings = FastEmbedEmbeddings(model_name=self.settings.embedding_model)
        self.client = QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)
        self._ensure_collection()
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.settings.qdrant_collection,
            embedding=self.embeddings,
        )

    def _ensure_collection(self) -> None:
        collection_name = self.settings.qdrant_collection
        if self.client.collection_exists(collection_name=collection_name):
            return
        dimension = len(self.embeddings.embed_query("dimension check"))
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def add_turn(self, *, user_id: str, thread_id: str, user_text: str, assistant_text: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        docs: list[Document] = []
        if user_text.strip():
            docs.append(
                Document(
                    page_content=user_text.strip(),
                    metadata={
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "role": "user",
                        "created_at": now,
                    },
                )
            )
        if assistant_text.strip():
            docs.append(
                Document(
                    page_content=assistant_text.strip(),
                    metadata={
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "role": "assistant",
                        "created_at": now,
                    },
                )
            )
        if not docs:
            return
        self.vector_store.add_documents(documents=docs, ids=[str(uuid4()) for _ in docs])

    def search_user_memory(self, *, user_id: str, query: str, k: int | None = None) -> list[Document]:
        if not query.strip():
            return []
        limit = k or self.settings.memory_search_k
        user_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        )
        return self.vector_store.similarity_search(query=query, k=limit, filter=user_filter)
