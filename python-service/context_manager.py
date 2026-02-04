from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from .config import get_settings


class Message(TypedDict):
    role: str  # "user" | "assistant" | "system"
    content: str


class ConversationState(TypedDict, total=False):
    conversation_id: str
    created_at: float
    updated_at: float
    intent: str
    slots: Dict[str, Any]
    history: List[Message]


@dataclass
class ContextManager:
    """
    Simple in-memory context store for multi-turn conversations.

    In production, this would be backed by Redis or another durable store.
    The API is designed to make that swap trivial.
    """

    _store: Dict[str, ConversationState] = field(default_factory=dict)

    def _now(self) -> float:
        return time.time()

    def get_or_create_conversation(self, conversation_id: str) -> ConversationState:
        if conversation_id in self._store:
            state = self._store[conversation_id]
        else:
            state = ConversationState(
                conversation_id=conversation_id,
                created_at=self._now(),
                updated_at=self._now(),
                intent="",
                slots={},
                history=[],
            )
            self._store[conversation_id] = state
        self._expire_old()
        return state

    def update_conversation(
        self,
        conversation_id: str,
        *,
        intent: Optional[str] = None,
        slots: Optional[Dict[str, Any]] = None,
        new_messages: Optional[List[Message]] = None,
    ) -> ConversationState:
        state = self.get_or_create_conversation(conversation_id)

        if intent is not None:
            state["intent"] = intent

        if slots is not None:
            merged_slots = dict(state.get("slots", {}))
            merged_slots.update(slots)
            state["slots"] = merged_slots

        if new_messages:
            history = state.get("history", [])
            history.extend(new_messages)

            # Truncate history to configured maximum
            max_turns = get_settings().max_history_turns
            if len(history) > max_turns:
                history = history[-max_turns:]
            state["history"] = history

        state["updated_at"] = self._now()
        return state

    def get_summary(self, conversation_id: str) -> str:
        """
        Lightweight "summary" for prompt conditioning. We avoid a second
        LLM pass here and instead build a simple textual synopsis.
        """

        state = self.get_or_create_conversation(conversation_id)
        intent = state.get("intent", "")
        slots = state.get("slots", {})
        return f"Intent={intent}, Slots={slots}"

    def _expire_old(self) -> None:
        """
        Remove conversations that have exceeded the configured TTL.
        """

        ttl = get_settings().context_ttl_seconds
        cutoff = self._now() - ttl
        to_delete = [
            cid
            for cid, state in self._store.items()
            if state.get("updated_at", 0) < cutoff
        ]
        for cid in to_delete:
            self._store.pop(cid, None)

