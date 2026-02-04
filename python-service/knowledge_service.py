from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings
from .logging_utils import log_with_context

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeService:
    """
    Encapsulates all access to the MongoDB-backed knowledge base.
    """

    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase

    @classmethod
    def from_settings(cls) -> "KnowledgeService":
        settings = get_settings()
        client = AsyncIOMotorClient(settings.mongo_dsn)
        db = client[settings.mongo_db_name]
        return cls(client=client, db=db)

    async def get_delivery_policies(self) -> List[Dict[str, Any]]:
        log_with_context(logger, logging.INFO, "Fetching delivery time policies")
        cursor = self.db["delivery_time_policy"].find({})
        return [doc async for doc in cursor]

    async def get_refund_policies(self) -> List[Dict[str, Any]]:
        log_with_context(logger, logging.INFO, "Fetching refund policies")
        cursor = self.db["refund_policy"].find({})
        return [doc async for doc in cursor]

    async def get_shipping_guidelines(self) -> List[Dict[str, Any]]:
        log_with_context(logger, logging.INFO, "Fetching shipping guidelines")
        cursor = self.db["shipping_guidelines"].find({})
        return [doc async for doc in cursor]

