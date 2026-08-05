import os
from typing import Any, Dict, Optional
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.services.llm.factory import LLMFactory


class WorkflowAgent(BaseAgent):
    """Workflow Agent: Generates step-by-step procedural workflows & Mermaid diagrams."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/workflow.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="WorkflowAgent",
            description="Generates step-by-step procedural guidelines, workflows, and Mermaid process diagrams for dealership tasks.",
            capabilities=["workflow_generation", "procedural_guidance", "mermaid_diagrams", "process_mapping"],
            input_schema={"query": "string", "user_role": "string"},
            output_schema={"steps": "string", "mermaid_diagram": "string"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["how do i", "process", "workflow", "steps to", "procedure", "guide", "intake", "claim process", "step by step"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.5 + (matches * 0.2), 0.98)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        user_role = (context or {}).get("user_role", "sales_rep")
        
        full_prompt = (
            f"User Role: {user_role}\n"
            f"Requested Process/Workflow: {query}\n\n"
            f"Generate a clear Step 1, Step 2, Step 3 procedural guide. "
            f"Include a valid Mermaid diagram markdown block ```mermaid ... ```."
        )

        llm = LLMFactory.get_provider()
        response_text = await llm.generate(
            prompt=full_prompt,
            system_prompt=self.system_prompt,
            temperature=0.2,
        )

        return AgentResponse(
            agent_name=self.metadata.name,
            content=response_text,
            confidence=0.95,
            citations=[],
            metadata={"has_diagram": "```mermaid" in response_text},
        )
