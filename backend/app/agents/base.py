from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    name: str
    description: str
    capabilities: List[str]
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_name: str
    content: str
    confidence: float = 1.0
    citations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: List[str] = Field(default_factory=list)
    delegate_to: Optional[str] = None


class BaseAgent(ABC):
    """Abstract Base Class for all Agent Plugins in the system."""

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Returns the metadata describing the agent name, description, capabilities, and schemas."""
        pass

    @abstractmethod
    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Evaluate how well this agent can handle the user query (returns score 0.0 to 1.0)."""
        pass

    @abstractmethod
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute agent business logic asynchronously and return structured AgentResponse."""
        pass
