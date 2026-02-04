from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .context_manager import ContextManager
from .db_service import DBService
from .intent_engine import IntentEngine
from .knowledge_service import KnowledgeService
from .llm_client import LLMClient
from .logging_utils import configure_logging, log_with_context
from .slot_manager import SlotManager
from .workflow_engine import WorkflowEngine, WorkflowResult

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="HelloBot Orchestration Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        description="Stable identifier for the ongoing conversation/session.",
    )
    user_message: str = Field(..., min_length=1, description="Raw user input text.")


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    slots: Dict[str, Any]
    response_text: str
    awaiting_more_input: bool


class ConversationStateResponse(BaseModel):
    conversation_id: str
    intent: str
    slots: Dict[str, Any]
    history: List[Dict[str, Any]]


# Dependency wiring
def get_context_manager() -> ContextManager:
    # Singleton-like in-process instance
    if not hasattr(app.state, "context_manager"):
        app.state.context_manager = ContextManager()
    return app.state.context_manager


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    if not hasattr(app.state, "llm_client"):
        app.state.llm_client = LLMClient.from_settings()
    return app.state.llm_client


def get_db_service(settings: Settings = Depends(get_settings)) -> DBService:
    if not hasattr(app.state, "db_service"):
        app.state.db_service = DBService.from_settings()
    return app.state.db_service


def get_knowledge_service(settings: Settings = Depends(get_settings)) -> KnowledgeService:
    if not hasattr(app.state, "knowledge_service"):
        app.state.knowledge_service = KnowledgeService.from_settings()
    return app.state.knowledge_service


def get_slot_manager() -> SlotManager:
    if not hasattr(app.state, "slot_manager"):
        app.state.slot_manager = SlotManager()
    return app.state.slot_manager


def get_intent_engine(llm_client: LLMClient = Depends(get_llm_client)) -> IntentEngine:
    if not hasattr(app.state, "intent_engine"):
        app.state.intent_engine = IntentEngine(llm_client=llm_client)
    return app.state.intent_engine


def get_workflow_engine(
    context_manager: ContextManager = Depends(get_context_manager),
    intent_engine: IntentEngine = Depends(get_intent_engine),
    slot_manager: SlotManager = Depends(get_slot_manager),
    llm_client: LLMClient = Depends(get_llm_client),
    db_service: DBService = Depends(get_db_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> WorkflowEngine:
    if not hasattr(app.state, "workflow_engine"):
        app.state.workflow_engine = WorkflowEngine(
            context_manager=context_manager,
            intent_engine=intent_engine,
            slot_manager=slot_manager,
            llm_client=llm_client,
            db_service=db_service,
            knowledge_service=knowledge_service,
        )
    return app.state.workflow_engine


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    workflow: WorkflowEngine = Depends(get_workflow_engine),
) -> ChatResponse:
    """
    Main conversational endpoint.

    The API surface is intentionally minimal: the client provides a
    `conversation_id` and the latest `user_message`, and the orchestration
    layer handles the full 3-pass reasoning pipeline.
    """

    log_with_context(
        logger,
        logging.INFO,
        "Incoming chat request",
        path=str(request.url.path),
        conversation_id=payload.conversation_id,
    )

    try:
        result: WorkflowResult = await workflow.handle_turn(
            conversation_id=payload.conversation_id,
            user_message=payload.user_message,
        )
    except Exception as exc:  # noqa: BLE001
        log_with_context(
            logger,
            logging.ERROR,
            "Unhandled error in chat endpoint",
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    return ChatResponse(
        conversation_id=result.conversation_id,
        intent=result.intent,
        slots=result.slots,
        response_text=result.response_text,
        awaiting_more_input=result.awaiting_more_input,
    )


@app.get("/conversations/{conversation_id}", response_model=ConversationStateResponse)
async def get_conversation_state(
    conversation_id: str,
    context_manager: ContextManager = Depends(get_context_manager),
) -> ConversationStateResponse:
    """
    Read-only inspection endpoint for the current state of a conversation.
    This powers the "context/state inspection panel" in the UI.
    """

    state = context_manager.get_or_create_conversation(conversation_id)
    return ConversationStateResponse(
        conversation_id=conversation_id,
        intent=state.get("intent", ""),
        slots=state.get("slots", {}),
        history=state.get("history", []),
    )


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    """
    Lightweight liveness probe.
    """

    return {"status": "ok"}


@app.get("/readyz")
async def readiness(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Readiness probe. In a full implementation, this would verify that all
    downstream dependencies (databases, LLM provider, etc.) are reachable.
    """

    return {
        "status": "ready",
        "environment": settings.environment,
        "app_name": settings.app_name,
    }

