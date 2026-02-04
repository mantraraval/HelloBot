from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from .config import get_settings
from .logging_utils import log_with_context

logger = logging.getLogger(__name__)


@dataclass
class DBService:
    """
    Mediates all access to the relational database.

    The LLM never touches the database directly; instead, the workflow
    engine calls into this service with strongly-typed parameters.
    """

    session_factory: async_sessionmaker[AsyncSession]

    @classmethod
    def from_settings(cls) -> "DBService":
        settings = get_settings()
        # For simplicity we assume the DSN uses an async-capable driver.
        engine = create_async_engine(settings.sql_dsn, echo=False, future=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        return cls(session_factory=factory)

    async def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an order by its business identifier.
        """

        async with self.session_factory() as session:
            query = text(
                "SELECT order_id, user_id, status, created_at "
                "FROM orders WHERE order_id = :order_id"
            )
            log_with_context(
                logger,
                logging.INFO,
                "Executing order lookup",
                order_id=order_id,
            )
            result = await session.execute(query, {"order_id": order_id})
            row = result.m.fetchone() if hasattr(result, "m") else result.fetchone()
            if not row:
                return None
            mapping = dict(row._mapping)  # type: ignore[attr-defined]
            return mapping

