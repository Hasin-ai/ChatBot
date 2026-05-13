from __future__ import annotations

from typing import Any


def extract_text_from_content(content: Any) -> str:
    """Extract plain text from ChatKit content blocks without assuming a single schema."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part for part in (extract_text_from_content(item) for item in content) if part)
    if isinstance(content, dict):
        for key in ("text", "content", "value"):
            value = content.get(key)
            if isinstance(value, str):
                return value
        return ""
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    value = getattr(content, "content", None)
    if isinstance(value, str):
        return value
    return ""


def extract_item_text(item: Any) -> str:
    return extract_text_from_content(getattr(item, "content", None)).strip()


def infer_item_role(item: Any) -> str:
    class_name = item.__class__.__name__.lower()
    item_type = str(getattr(item, "type", "") or getattr(item, "role", "")).lower()
    joined = f"{class_name} {item_type}"
    if "user" in joined:
        return "user"
    if "assistant" in joined:
        return "assistant"
    if "system" in joined:
        return "system"
    if "tool" in joined:
        return "tool"
    return "unknown"


def compact_title(text: str, limit: int = 80) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."
