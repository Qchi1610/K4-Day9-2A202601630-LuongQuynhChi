from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.session import SessionModel
from app.services.database.repositories import session_repo


class SessionMemoryManager:
    """Manager for active session memory (user role, workflow state, history, retrieved docs)."""

    async def get_or_create_session(
        self, session_id: str, user_id: str = "guest_user", user_role: str = "sales_rep"
    ) -> SessionModel:
        session = await session_repo.get_by_id(session_id)
        if not session:
            session = SessionModel(
                session_id=session_id,
                user_id=user_id,
                user_role=user_role,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            await session_repo.insert(session)
        return session

    async def update_session_state(
        self,
        session_id: str,
        question: Optional[str] = None,
        retrieved_docs: Optional[List[str]] = None,
        current_workflow: Optional[str] = None,
    ) -> SessionModel:
        session = await session_repo.get_by_id(session_id)
        if not session:
            session = SessionModel(session_id=session_id, user_id="guest_user")

        if question:
            session.previous_questions.append(question)
            # Keep last 10 questions in active memory context
            session.previous_questions = session.previous_questions[-10:]

        if retrieved_docs:
            session.retrieved_documents.extend(retrieved_docs)
            session.retrieved_documents = list(set(session.retrieved_documents))[-20:]

        if current_workflow:
            session.current_workflow = current_workflow

        session.updated_at = datetime.now(timezone.utc)
        await session_repo.insert(session)
        return session


session_memory_manager = SessionMemoryManager()
