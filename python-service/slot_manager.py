from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SlotManager:
    """
    Responsible for extracting, tracking, and validating slots over
    the course of a multi-turn conversation.
    """

    required_slots_by_intent: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "get_order_status": ["order_id"],
            "ask_delivery_time": [],
            "ask_refund_policy": [],
        }
    )

    def get_required_slots(self, intent: str) -> List[str]:
        return self.required_slots_by_intent.get(intent, [])

    def merge_slots(
        self,
        existing_slots: Dict[str, Any],
        new_entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge newly extracted entities into the existing slot map.
        New values override old ones for simplicity.
        """

        merged = dict(existing_slots)
        merged.update(new_entities)
        return merged

    def compute_missing_slots(
        self,
        intent: str,
        current_slots: Dict[str, Any],
    ) -> List[str]:
        """
        Determine which required slots are still missing.
        """

        required = self.get_required_slots(intent)
        return [slot for slot in required if slot not in current_slots or current_slots[slot] in ("", None)]

