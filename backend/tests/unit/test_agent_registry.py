import pytest
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.agents.registry import AgentRegistry


class MockCustomAgent(BaseAgent):
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="MockCustomAgent",
            description="Mock plugin agent for unit test discovery.",
            capabilities=["mock_capability"],
        )

    async def can_handle(self, query: str, context=None) -> float:
        return 0.88 if "mock" in query.lower() else 0.10

    async def execute(self, query: str, context=None) -> AgentResponse:
        return AgentResponse(agent_name="MockCustomAgent", content="Mock response content")


def test_agent_registry_discovery_and_registration():
    registry = AgentRegistry.get_registry()
    agents = registry.list_agents()
    
    # Verify core standard agents are discovered
    agent_names = [a.metadata.name for a in agents]
    assert "KnowledgeAgent" in agent_names
    assert "WorkflowAgent" in agent_names
    assert "LearningAgent" in agent_names
    assert "TroubleshootingAgent" in agent_names
    assert "TicketAgent" in agent_names

    # Verify lookup by name
    w_agent = registry.get_agent("WorkflowAgent")
    assert w_agent is not None
    assert w_agent.metadata.name == "WorkflowAgent"

    # Test dynamic manual registration
    mock_agent = MockCustomAgent()
    registry.register_agent(mock_agent)
    assert registry.get_agent("MockCustomAgent") is not None
