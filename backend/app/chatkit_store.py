from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from chatkit.store import NotFoundError, Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from pydantic import TypeAdapter
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.item_utils import compact_title, extract_item_text, infer_item_role
from app.models import ChatItemRow, ChatThreadRow

_THREAD_ITEM_ADAPTER = TypeAdapter(ThreadItem)


def _json_dump_model(model: Any) -> str:
    if hasattr(model, "model_dump"):
        payload = model.model_dump(mode="json")
    else:
        payload = model
    return json.dumps(payload, ensure_ascii=False)


def _json_load_model(data: str) -> Any:
    return json.loads(data)


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.now(timezone.utc)


class SQLiteChatKitStore(Store[object]):
    """Database-backed ChatKit store scoped by the authenticated user id in context."""

    def _session(self) -> Session:
        return SessionLocal()

    @staticmethod
    def _user_id(context: object) -> str:
        user_id = getattr(context, "user_id", None)
        if not isinstance(user_id, str) or not user_id:
            raise NotFoundError("Missing authenticated user context")
        return user_id

    def _paginate(self, rows: list[Any], after: str | None, limit: int, order: str, cursor_key: Callable[[Any], str]) -> Page[Any]:
        start = 0
        if after:
            for idx, row in enumerate(rows):
                if cursor_key(row) == after:
                    start = idx + 1
                    break
        data = rows[start : start + limit]
        has_more = start + limit < len(rows)
        next_after = cursor_key(data[-1]) if has_more and data else None
        return Page(data=data, has_more=has_more, after=next_after)

    async def load_thread(self, thread_id: str, context: object) -> ThreadMetadata:
        user_id = self._user_id(context)
        with self._session() as db:
            row = db.scalar(select(ChatThreadRow).where(ChatThreadRow.id == thread_id, ChatThreadRow.user_id == user_id))
            if row is None:
                raise NotFoundError(f"Thread {thread_id} not found")
            return ThreadMetadata.model_validate(_json_load_model(row.data))

    async def save_thread(self, thread: ThreadMetadata, context: object) -> None:
        user_id = self._user_id(context)
        payload = _json_dump_model(thread)
        created_at = _as_datetime(getattr(thread, "created_at", None))
        with self._session() as db:
            requested_title = getattr(thread, "title", None)
            row = db.get(ChatThreadRow, thread.id)
            title = requested_title
            if row is None:
                row = ChatThreadRow(
                    id=thread.id,
                    user_id=user_id,
                    title=title,
                    created_at=created_at,
                    updated_at=datetime.now(timezone.utc),
                    data=payload,
                )
                db.add(row)
            else:
                if row.user_id != user_id:
                    raise NotFoundError(f"Thread {thread.id} not found")
                title = requested_title or row.title
                if title and not requested_title:
                    thread_payload = _json_load_model(payload)
                    thread_payload["title"] = title
                    payload = json.dumps(thread_payload, ensure_ascii=False)
                row.title = title
                row.updated_at = datetime.now(timezone.utc)
                row.data = payload
            db.commit()

    async def load_threads(self, limit: int, after: str | None, order: str, context: object) -> Page[ThreadMetadata]:
        user_id = self._user_id(context)
        with self._session() as db:
            stmt: Select[tuple[ChatThreadRow]] = select(ChatThreadRow).where(ChatThreadRow.user_id == user_id)
            stmt = stmt.order_by(ChatThreadRow.created_at.desc() if order == "desc" else ChatThreadRow.created_at.asc())
            rows = list(db.scalars(stmt).all())
            threads = [ThreadMetadata.model_validate(_json_load_model(row.data)) for row in rows]
            return self._paginate(threads, after, limit, order, cursor_key=lambda thread: thread.id)

    async def load_thread_items(self, thread_id: str, after: str | None, limit: int, order: str, context: object) -> Page[ThreadItem]:
        user_id = self._user_id(context)
        with self._session() as db:
            thread = db.scalar(select(ChatThreadRow).where(ChatThreadRow.id == thread_id, ChatThreadRow.user_id == user_id))
            if thread is None:
                raise NotFoundError(f"Thread {thread_id} not found")
            stmt = select(ChatItemRow).where(ChatItemRow.thread_id == thread_id, ChatItemRow.user_id == user_id)
            stmt = stmt.order_by(ChatItemRow.created_at.desc() if order == "desc" else ChatItemRow.created_at.asc())
            rows = list(db.scalars(stmt).all())
            items = [_THREAD_ITEM_ADAPTER.validate_python(_json_load_model(row.data)) for row in rows]
            return self._paginate(items, after, limit, order, cursor_key=lambda item: item.id)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: object) -> None:
        await self.save_item(thread_id, item, context)

    async def save_item(self, thread_id: str, item: ThreadItem, context: object) -> None:
        user_id = self._user_id(context)
        payload = _json_dump_model(item)
        text = extract_item_text(item)
        role = infer_item_role(item)
        created_at = _as_datetime(getattr(item, "created_at", None))
        now = datetime.now(timezone.utc)

        with self._session() as db:
            thread = db.scalar(select(ChatThreadRow).where(ChatThreadRow.id == thread_id, ChatThreadRow.user_id == user_id))
            if thread is None:
                raise NotFoundError(f"Thread {thread_id} not found")
            row = db.get(ChatItemRow, item.id)
            if row is None:
                row = ChatItemRow(
                    id=item.id,
                    thread_id=thread_id,
                    user_id=user_id,
                    role=role,
                    text=text,
                    created_at=created_at,
                    data=payload,
                )
                db.add(row)
            else:
                if row.user_id != user_id or row.thread_id != thread_id:
                    raise NotFoundError(f"Item {item.id} not found in thread {thread_id}")
                row.role = role
                row.text = text
                row.data = payload
                row.created_at = created_at

            if role == "user" and text and not thread.title:
                thread.title = compact_title(text)
                try:
                    thread_payload = _json_load_model(thread.data)
                    thread_payload["title"] = thread.title
                    thread.data = json.dumps(thread_payload, ensure_ascii=False)
                except Exception:
                    pass
            thread.updated_at = now
            db.commit()

    async def load_item(self, thread_id: str, item_id: str, context: object) -> ThreadItem:
        user_id = self._user_id(context)
        with self._session() as db:
            row = db.scalar(
                select(ChatItemRow).where(
                    ChatItemRow.thread_id == thread_id,
                    ChatItemRow.id == item_id,
                    ChatItemRow.user_id == user_id,
                )
            )
            if row is None:
                raise NotFoundError(f"Item {item_id} not found in thread {thread_id}")
            return _THREAD_ITEM_ADAPTER.validate_python(_json_load_model(row.data))

    async def delete_thread(self, thread_id: str, context: object) -> None:
        user_id = self._user_id(context)
        with self._session() as db:
            row = db.scalar(select(ChatThreadRow).where(ChatThreadRow.id == thread_id, ChatThreadRow.user_id == user_id))
            if row is not None:
                db.delete(row)
                db.commit()

    async def delete_thread_item(self, thread_id: str, item_id: str, context: object) -> None:
        user_id = self._user_id(context)
        with self._session() as db:
            row = db.scalar(
                select(ChatItemRow).where(
                    ChatItemRow.thread_id == thread_id,
                    ChatItemRow.id == item_id,
                    ChatItemRow.user_id == user_id,
                )
            )
            if row is not None:
                db.delete(row)
                db.commit()

    async def save_attachment(self, attachment: Attachment, context: object) -> None:
        raise NotImplementedError("Attachments are disabled in this assignment build.")

    async def load_attachment(self, attachment_id: str, context: object) -> Attachment:
        raise NotImplementedError("Attachments are disabled in this assignment build.")

    async def delete_attachment(self, attachment_id: str, context: object) -> None:
        raise NotImplementedError("Attachments are disabled in this assignment build.")
