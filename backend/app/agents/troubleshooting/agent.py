import os
from typing import Any, Dict, Optional
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.core.config import settings
from app.services.llm.factory import LLMFactory


class TroubleshootingAgent(BaseAgent):
    """Troubleshooting Agent: Diagnoses operational/technical issues and escalates low confidence cases."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/troubleshooting.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="TroubleshootingAgent",
            description="Diagnoses motorcycle operational issues, error codes, and hardware/software faults.",
            capabilities=["issue_diagnosis", "error_troubleshooting", "root_cause_analysis", "repair_guidance"],
            input_schema={"error_description": "string"},
            output_schema={"causes": "list[string]", "fixes": "list[string]", "confidence": "float"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["error", "fault", "not working", "broken", "issue", "troubleshoot", "diagnostic", "warning light", "fail", "code", "battery level dropped"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.5 + (matches * 0.2), 0.98)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        full_prompt = (
            f"Operational Error Description: {query}\n\n"
            f"Provide:\n"
            f"1. Possible Root Causes\n"
            f"2. Suggested Step-by-Step Fixes\n"
            f"3. Assessment of whether this can be fixed locally or requires a support ticket."
        )

        llm = LLMFactory.get_provider()
        response_text = await llm.generate(
            prompt=full_prompt,
            system_prompt=self.system_prompt,
            temperature=0.2,
        )

        # Estimate diagnostic confidence based on clarity/specificity of response
        is_unknown_or_complex = any(
            phrase in query.lower() for phrase in ["unknown code", "catastrophic", "smoke", "unexplained fire", "unresponsive ecu"]
        )
        confidence = 0.55 if is_unknown_or_complex else 0.85

        delegate_target = None
        if confidence < settings.TROUBLESHOOTING_CONFIDENCE_THRESHOLD:
            delegate_target = "TicketAgent"

        return AgentResponse(
            agent_name=self.metadata.name,
            content=response_text,
            confidence=confidence,
            citations=[],
            metadata={"confidence_threshold": settings.TROUBLESHOOTING_CONFIDENCE_THRESHOLD},
            delegate_to=delegate_target,
        )
