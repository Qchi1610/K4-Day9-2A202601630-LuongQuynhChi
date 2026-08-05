import os
import uuid
from typing import Any, Dict, Optional
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.models.ticket import TicketModel
from app.services.database.repositories import ticket_repo
from app.services.llm.factory import LLMFactory


class TicketAgent(BaseAgent):
    """Ticket Agent: Generates structured support tickets and persists them into the database."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/ticket.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="TicketAgent",
            description="Generates structured support tickets for unresolvable technical or operational issues.",
            capabilities=["ticket_generation", "issue_escalation", "support_ticket_creation"],
            input_schema={"issue_details": "string"},
            output_schema={"ticket_id": "string", "title": "string", "priority": "string", "category": "string"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["ticket", "create ticket", "escalate", "support request", "open issue", "submit ticket"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.5 + (matches * 0.25), 0.98)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        session_id = (context or {}).get("session_id", str(uuid.uuid4()))
        user_id = (context or {}).get("user_id", "guest_user")

        full_prompt = (
            f"User Issue Details: {query}\n\n"
            f"Generate a formal, structured Support Ticket containing:\n"
            f"- Title\n"
            f"- Description\n"
            f"- Category (e.g., Battery, ECU, Motor, Software, Warranty)\n"
            f"- Priority (Low, Medium, High, Critical)\n"
            f"- Required Screenshots / Diagnostic Logs"
        )

        llm = LLMFactory.get_provider()
        ticket_content = await llm.generate(
            prompt=full_prompt,
            system_prompt=self.system_prompt,
            temperature=0.1,
        )

        ticket_id = f"TICK-{uuid.uuid4().hex[:8].upper()}"

        # Persist structured ticket entity
        ticket_obj = TicketModel(
            ticket_id=ticket_id,
            session_id=session_id,
            user_id=user_id,
            title=f"Escalation: {query[:50]}",
            description=ticket_content,
            category="technical_issue",
            priority="high",
            required_screenshots=["battery_telemetry_log.png", "error_code_screenshot.png"],
        )
        await ticket_repo.insert(ticket_obj)

        formatted_output = f"### 🎫 Support Ticket Generated Successfully\n**Ticket ID**: `{ticket_id}`\n\n{ticket_content}"

        return AgentResponse(
            agent_name=self.metadata.name,
            content=formatted_output,
            confidence=1.0,
            citations=[],
            metadata={"ticket_id": ticket_id, "status": "open"},
        )
