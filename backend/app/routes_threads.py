from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ChatItemRow, ChatThreadRow, User
from app.schemas import MessageOut, ThreadSummary

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=list[ThreadSummary])
def list_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ThreadSummary]:
    rows = db.scalars(
        select(ChatThreadRow)
        .where(ChatThreadRow.user_id == current_user.id)
        .order_by(ChatThreadRow.updated_at.desc())
    ).all()

    summaries: list[ThreadSummary] = []
    for row in rows:
        count = db.scalar(
            select(func.count(ChatItemRow.id)).where(
                ChatItemRow.thread_id == row.id,
                ChatItemRow.user_id == current_user.id,
            )
        ) or 0
        summaries.append(
            ThreadSummary(
                id=row.id,
                title=row.title or "Untitled chat",
                created_at=row.created_at,
                updated_at=row.updated_at,
                message_count=int(count),
            )
        )
    return summaries


@router.get("/{thread_id}/messages", response_model=list[MessageOut])
def get_thread_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    thread = db.scalar(
        select(ChatThreadRow).where(
            ChatThreadRow.id == thread_id,
            ChatThreadRow.user_id == current_user.id,
        )
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    rows = db.scalars(
        select(ChatItemRow)
        .where(ChatItemRow.thread_id == thread_id, ChatItemRow.user_id == current_user.id)
        .order_by(ChatItemRow.created_at.asc())
    ).all()
    return [
        MessageOut(
            id=row.id,
            thread_id=row.thread_id,
            role=row.role,
            text=row.text,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    thread = db.scalar(
        select(ChatThreadRow).where(
            ChatThreadRow.id == thread_id,
            ChatThreadRow.user_id == current_user.id,
        )
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    db.delete(thread)
    db.commit()
