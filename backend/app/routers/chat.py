import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agents.coordinator.agent import coordinator_agent
from app.core.logging import logger
from app.core.security import rate_limiter, security_guardrail
from app.models.chat_log import ChatLogModel
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.database.repositories import chat_log_repo
from app.services.memory.session_memory import session_memory_manager

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & Multi-Agent Orchestration"])


@router.post("", response_model=ChatResponse)
async def handle_chat_request(chat_req: ChatRequest, request: Request):
    """Main API Endpoint orchestrating Coordinator Agent over dynamic agent registry."""
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    start_time = time.time()

    session_id = chat_req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    current_time = time.time()

    # 1. Rate limiting check
    if rate_limiter.is_rate_limited(session_id, current_time):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down your requests.",
        )

    # 2. Prompt Injection Guardrail Scan
    security_guardrail.detect_prompt_injection(chat_req.message)

    # 3. RBAC Role Sanitation
    validated_role = security_guardrail.validate_user_role(chat_req.user_role)

    # 4. Get/Create Session Memory
    session = await session_memory_manager.get_or_create_session(
        session_id=session_id, user_id=chat_req.user_id, user_role=validated_role
    )

    # 5. Build Execution Context
    context = {
        "request_id": request_id,
        "session_id": session_id,
        "user_id": chat_req.user_id,
        "user_role": validated_role,
        "previous_questions": session.previous_questions,
        "current_workflow": session.current_workflow,
    }

    # 6. Execute Coordinator Agent (Supervisor)
    final_text, agent_responses, routing_scores = await coordinator_agent.orchestrate(
        query=chat_req.message, context=context
    )

    # 7. Output Sanitization Guardrail
    sanitized_text = security_guardrail.sanitize_output(final_text)

    latency_ms = (time.time() - start_time) * 1000

    selected_names = [resp.agent_name for resp in agent_responses]
    all_citations = []
    for resp in agent_responses:
        all_citations.extend(resp.citations)
    all_citations = list(set(all_citations))

    # 8. Update Session Memory State
    await session_memory_manager.update_session_state(
        session_id=session_id,
        question=chat_req.message,
        retrieved_docs=all_citations,
    )

    # 9. Persist Chat Log in DB
    chat_log_entry = ChatLogModel(
        log_id=f"log_{uuid.uuid4().hex[:10]}",
        request_id=request_id,
        session_id=session_id,
        user_id=chat_req.user_id,
        user_query=chat_req.message,
        agent_selected=selected_names,
        response_content=sanitized_text,
        latency_ms=latency_ms,
        retrieved_documents=all_citations,
        tool_calls=[],
    )
    await chat_log_repo.insert(chat_log_entry)

    # 10. Structured Metric Logging
    logger.log_agent_execution(
        request_id=request_id,
        session_id=session_id,
        agent_selected=selected_names,
        latency_ms=latency_ms,
        retrieved_documents=all_citations,
        routing_score=routing_scores,
    )

    return ChatResponse(
        request_id=request_id,
        session_id=session_id,
        response=sanitized_text,
        agent_selected=selected_names,
        citations=all_citations,
        latency_ms=round(latency_ms, 2),
        routing_scores=routing_scores,
    )
