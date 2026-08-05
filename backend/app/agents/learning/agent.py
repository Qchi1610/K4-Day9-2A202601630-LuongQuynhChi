import os
from typing import Any, Dict, Optional
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.services.llm.factory import LLMFactory


class LearningAgent(BaseAgent):
    """Learning Agent: Recommends personalized learning roadmaps, flashcards, and role-based quizzes."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/learning.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="LearningAgent",
            description="Recommends personalized onboarding roadmaps, training modules, flashcards, and quizzes tailored to dealership roles.",
            capabilities=["learning_roadmap", "quizzes", "flashcards", "training_recommendations", "role_onboarding"],
            input_schema={"query": "string", "user_role": "string"},
            output_schema={"roadmap": "list", "quiz": "list", "next_lessons": "list"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["learn", "training", "roadmap", "quiz", "flashcard", "onboard me", "module", "curriculum", "lesson"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.5 + (matches * 0.2), 0.98)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        user_role = (context or {}).get("user_role", "sales_rep")

        full_prompt = (
            f"User Role: {user_role}\n"
            f"User Request: {query}\n\n"
            f"Generate a personalized learning package containing:\n"
            f"1. Onboarding Roadmap & Next Lessons\n"
            f"2. Key Flashcards / Summary Points\n"
            f"3. 2 Interactive Practice Quiz Questions with Answers"
        )

        llm = LLMFactory.get_provider()
        response_text = await llm.generate(
            prompt=full_prompt,
            system_prompt=self.system_prompt,
            temperature=0.3,
        )

        return AgentResponse(
            agent_name=self.metadata.name,
            content=response_text,
            confidence=0.92,
            citations=[],
            metadata={"user_role": user_role},
        )
