from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .llm_client import LLMClient, IntentPassResult


@dataclass
class IntentEngine:
    """
    High-level wrapper around the LLM-based intent detection pass.

    This layer abstracts away the raw LLM interaction and exposes a
    domain-friendly interface the rest of the system can depend on.
    """

    llm_client: LLMClient

    async def detect_intent_and_slots(
        self,
        user_message: str,
        context_summary: str | None = None,
    ) -> IntentPassResult:
        """
        Run PASS 1 of the reasoning pipeline.
        """

        return await self.llm_client.run_intent_pass(
            user_message=user_message,
            context_summary=context_summary,
        )

