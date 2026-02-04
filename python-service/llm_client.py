from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, TypedDict

from openai import AsyncOpenAI

from .config import get_settings
from .logging_utils import log_with_context

logger = logging.getLogger(__name__)


class IntentPassResult(TypedDict):
    intent: str
    missing_slots: list[str]
    extracted_entities: Dict[str, Any]


@dataclass
class LLMClient:
    """
    Thin wrapper around an OpenAI-compatible LLM provider.

    This class is provider-agnostic as long as the target supports the
    Chat Completions API. All higher-level orchestration logic lives in
    the workflow and intent engines.
    """

    model: str
    api_key: str | None
    base_url: str | None

    client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            logger.warning(
                "HELLOBOT_LLM_API_KEY is not set; LLM calls will fail at runtime."
            )

        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

    @classmethod
    def from_settings(cls) -> "LLMClient":
        settings = get_settings()
        return cls(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=str(settings.llm_base_url) if settings.llm_base_url else None,
        )

    async def run_intent_pass(
        self,
        user_message: str,
        context_summary: str | None = None,
    ) -> IntentPassResult:
        """
        PASS 1 — Use the LLM to classify intent and extract entities.

        The model is instructed to ALWAYS return strict JSON with:
        {
          "intent": "string",
          "missing_slots": ["slot_a", ...],
          "extracted_entities": { "slot_a": "value" }
        }
        """

        system_prompt = (
            "You are an intent classification and slot-extraction engine for an "
            "e-commerce assistant called HelloBot.\n\n"
            "You MUST respond with STRICT JSON only, with no explanations, no prose, "
            "and no markdown code fences. The JSON object MUST have exactly these keys:\n"
            "  - intent: string\n"
            "  - missing_slots: array of strings\n"
            "  - extracted_entities: object mapping slot names to values\n\n"
            "Supported intents include (but are not limited to):\n"
            "  - get_order_status: customer asks about status of an order\n"
            "  - ask_delivery_time: customer asks how long delivery will take\n"
            "  - ask_refund_policy: customer asks about refunds/returns\n"
            "If none of these fit, use 'chitchat'.\n\n"
            "For get_order_status, the primary slot is 'order_id'. "
            "If the user did not provide it, include it in missing_slots.\n\n"
            "IMPORTANT:\n"
            "- If you are unsure, prefer 'chitchat'.\n"
            "- Do NOT wrap the JSON in ```json or any markdown.\n"
        )

        user_payload: Dict[str, Any] = {
            "user_message": user_message,
        }
        if context_summary:
            user_payload["context_summary"] = context_summary

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]

        raw = await self._call_provider(messages=messages, mode="json")

        parsed = self._parse_json_safely(raw)

        intent = str(parsed.get("intent") or "chitchat")
        missing_slots_raw = parsed.get("missing_slots") or []
        extracted_entities_raw = parsed.get("extracted_entities") or {}

        if not isinstance(missing_slots_raw, list):
            missing_slots: list[str] = []
        else:
            missing_slots = [str(s) for s in missing_slots_raw]

        if not isinstance(extracted_entities_raw, dict):
            extracted_entities: Dict[str, Any] = {}
        else:
            extracted_entities = dict(extracted_entities_raw)

        log_with_context(
            logger,
            logging.INFO,
            "Intent pass result",
            intent=intent,
            missing_slots=missing_slots,
            extracted_entities=extracted_entities,
        )

        return IntentPassResult(
            intent=intent,
            missing_slots=missing_slots,
            extracted_entities=extracted_entities,
        )

    async def run_slot_followup_pass(
        self,
        intent: str,
        missing_slots: list[str],
    ) -> str:
        """
        PASS 2 — Ask a natural-language follow-up question to fill missing slots.
        """

        if not missing_slots:
            return ""

        system_prompt = (
            "You are a conversational assistant helping a user complete "
            "a request for an e-commerce assistant called HelloBot.\n\n"
            "Given the user's intent and which slots are missing, you must generate "
            "ONE short, friendly follow-up question that asks for ALL missing slots.\n\n"
            "Guidelines:\n"
            "- Use simple, customer-friendly language.\n"
            "- Do not mention 'slots' or technical concepts.\n"
            "- Do not add JSON or any metadata; return only the question text.\n"
        )

        user_payload = {
            "intent": intent,
            "missing_slots": missing_slots,
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]

        text = await self._call_provider(messages=messages, mode="text")
        followup = text.strip()

        log_with_context(
            logger,
            logging.INFO,
            "Generated slot follow-up question",
            intent=intent,
            missing_slots=missing_slots,
            followup=followup,
        )

        return followup

    async def run_response_pass(
        self,
        intent: str,
        slots: Dict[str, Any],
        retrieved_data: Dict[str, Any] | None,
        knowledge_snippets: list[Dict[str, Any]] | None,
        conversation_history: list[Dict[str, Any]],
    ) -> str:
        """
        PASS 3 — Generate a polished, user-facing response from structured data.
        """

        system_prompt = (
            "You are HelloBot, a helpful customer support assistant for an "
            "e-commerce platform.\n\n"
            "You receive:\n"
            "- intent: the classified intent of the user\n"
            "- slots: structured values like order_id\n"
            "- retrieved_data: records from the orders database (if any)\n"
            "- knowledge_snippets: policy documents from the knowledge base (if any)\n"
            "- conversation_history: prior messages in this conversation\n\n"
            "Your job is to generate a concise, friendly response that:\n"
            "- Answers the user's implied question or request.\n"
            "- Uses retrieved_data for concrete facts like order status.\n"
            "- Uses knowledge_snippets for policies like delivery times or refunds.\n"
            "- Avoids exposing internal schema names or raw JSON.\n\n"
            "Do NOT include JSON in your reply. Respond as natural language prose only."
        )

        user_payload = {
            "intent": intent,
            "slots": slots,
            "retrieved_data": retrieved_data,
            "knowledge_snippets": knowledge_snippets,
            "conversation_history": conversation_history,
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]

        text = await self._call_provider(messages=messages, mode="text")
        response = text.strip()

        log_with_context(
            logger,
            logging.INFO,
            "Response pass completed",
            intent=intent,
            response_preview=response[:120],
        )

        return response

    async def _call_provider(
        self,
        *,
        messages: List[Dict[str, str]],
        mode: Literal["json", "text"],
    ) -> str:
        """
        Call the underlying OpenAI-compatible provider.

        - For `mode='json'`, we request a JSON object via response_format.
        - For `mode='text'`, we allow free-form natural language.
        """

        log_with_context(
            logger,
            logging.DEBUG,
            "Calling LLM provider",
            mode=mode,
            model=self.model,
        )

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1 if mode == "json" else 0.3,
        }

        if mode == "json":
            kwargs["response_format"] = {"type": "json_object"}

        completion = await self.client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        content = choice.message.content or ""

        log_with_context(
            logger,
            logging.DEBUG,
            "LLM raw response received",
            length=len(content),
        )

        return content

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """
        Remove surrounding ``` or ```json fences if present.

        This makes the JSON parsing robust against models that ignore
        instructions and wrap output in markdown code blocks.
        """
        stripped = text.strip()

        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                inner = "\n".join(lines[1:-1])
                return inner.strip()

        fence_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            stripped,
            flags=re.DOTALL,
        )
        if fence_match:
            return fence_match.group(1).strip()

        return stripped

    @classmethod
    def _parse_json_safely(cls, text: str) -> Dict[str, Any]:
        """
        Best-effort JSON parsing that tolerates markdown fencing and
        minor formatting deviations. Falls back to an empty dict on error.
        """
        candidate = cls._strip_markdown_fences(text)

        try:
            return json.loads(candidate)
        except Exception as exc:  # noqa: BLE001
            log_with_context(
                logger,
                logging.WARNING,
                "Failed to parse JSON from LLM response",
                error=str(exc),
                raw_preview=candidate[:200],
            )
            return {}

