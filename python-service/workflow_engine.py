from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .context_manager import ContextManager
from .db_service import DBService
from .intent_engine import IntentEngine
from .knowledge_service import KnowledgeService
from .llm_client import LLMClient
from .slot_manager import SlotManager


@dataclass
class WorkflowResult:
    """
    Canonical result of a single conversational turn.
    """

    conversation_id: str
    intent: str
    slots: Dict[str, Any]
    response_text: str
    awaiting_more_input: bool


@dataclass
class WorkflowEngine:
    """
    Orchestrates the full 3-pass reasoning pipeline and all side-effecting
    operations (database queries, knowledge retrieval, etc.).
    """

    context_manager: ContextManager
    intent_engine: IntentEngine
    slot_manager: SlotManager
    llm_client: LLMClient
    db_service: DBService
    knowledge_service: KnowledgeService

    async def handle_turn(
        self,
        conversation_id: str,
        user_message: str,
    ) -> WorkflowResult:
        """
        Core orchestration entrypoint for a single user turn.
        """

        # 1. Load and update context with the new user message
        state = self.context_manager.get_or_create_conversation(conversation_id)
        state = self.context_manager.update_conversation(
            conversation_id,
            new_messages=[{"role": "user", "content": user_message}],
        )

        context_summary = self.context_manager.get_summary(conversation_id)

        # 2. PASS 1 — intent & initial slot extraction via LLM
        intent_result = await self.intent_engine.detect_intent_and_slots(
            user_message=user_message,
            context_summary=context_summary,
        )

        current_slots = state.get("slots", {})
        merged_slots = self.slot_manager.merge_slots(
            current_slots=current_slots,
            new_entities=intent_result["extracted_entities"],
        )

        # Re-compute missing slots based on canonical intent definition
        canonical_missing = self.slot_manager.compute_missing_slots(
            intent=intent_result["intent"],
            current_slots=merged_slots,
        )

        # 3. PASS 2 — if anything is missing, generate a follow-up prompt
        if canonical_missing:
            followup = await self.llm_client.run_slot_followup_pass(
                intent=intent_result["intent"],
                missing_slots=canonical_missing,
            )

            # Persist context and respond without touching databases yet
            updated = self.context_manager.update_conversation(
                conversation_id,
                intent=intent_result["intent"],
                slots=merged_slots,
                new_messages=[{"role": "assistant", "content": followup}],
            )
            return WorkflowResult(
                conversation_id=conversation_id,
                intent=intent_result["intent"],
                slots=updated.get("slots", {}),
                response_text=followup,
                awaiting_more_input=True,
            )

        # 4. All required slots present: perform side effects (DB, knowledge)
        retrieved_data, knowledge_snippets = await self._perform_side_effects(
            intent=intent_result["intent"],
            slots=merged_slots,
        )

        # 5. PASS 3 — response framing
        history = self.context_manager.get_or_create_conversation(conversation_id).get(
            "history", []
        )
        response_text = await self.llm_client.run_response_pass(
            intent=intent_result["intent"],
            slots=merged_slots,
            retrieved_data=retrieved_data,
            knowledge_snippets=knowledge_snippets,
            conversation_history=history,
        )

        updated = self.context_manager.update_conversation(
            conversation_id,
            intent=intent_result["intent"],
            slots=merged_slots,
            new_messages=[{"role": "assistant", "content": response_text}],
        )

        return WorkflowResult(
            conversation_id=conversation_id,
            intent=intent_result["intent"],
            slots=updated.get("slots", {}),
            response_text=response_text,
            awaiting_more_input=False,
        )

    async def _perform_side_effects(
        self,
        intent: str,
        slots: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """
        Perform any database or knowledge-base operations required
        for the given intent.
        """

        retrieved_data: Optional[Dict[str, Any]] = None
        knowledge_snippets: Optional[List[Dict[str, Any]]] = None

        if intent == "get_order_status":
            order_id = str(slots.get("order_id"))
            retrieved_data = await self.db_service.get_order_by_id(order_id)

        elif intent == "ask_delivery_time":
            knowledge_snippets = await self.knowledge_service.get_delivery_policies()

        elif intent == "ask_refund_policy":
            knowledge_snippets = await self.knowledge_service.get_refund_policies()

        return retrieved_data, knowledge_snippets

