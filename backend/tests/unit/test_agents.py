import pytest
from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.workflow.agent import WorkflowAgent
from app.agents.learning.agent import LearningAgent
from app.agents.troubleshooting.agent import TroubleshootingAgent
from app.agents.ticket.agent import TicketAgent
from app.agents.coordinator.agent import CoordinatorAgent


@pytest.mark.asyncio
async def test_knowledge_agent_scoring():
    agent = KnowledgeAgent()
    score = await agent.can_handle("What is the warranty policy for battery packs?")
    assert score > 0.4


@pytest.mark.asyncio
async def test_workflow_agent_execution():
    agent = WorkflowAgent()
    score = await agent.can_handle("How do I process a warranty claim step by step?")
    assert score > 0.6

    res = await agent.execute("How do I process a warranty claim?", context={"user_role": "sales_rep"})
    assert res.agent_name == "WorkflowAgent"
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_troubleshooting_agent_delegation():
    agent = TroubleshootingAgent()
    res = await agent.execute("Unknown code catastrophic smoke battery fire", context={})
    assert res.delegate_to == "TicketAgent"


@pytest.mark.asyncio
async def test_ticket_agent_execution():
    agent = TicketAgent()
    res = await agent.execute("Brake motor failed completely", context={"session_id": "test_sess"})
    assert res.agent_name == "TicketAgent"
    assert "TICK-" in res.content


@pytest.mark.asyncio
async def test_coordinator_dynamic_routing():
    coordinator = CoordinatorAgent()
    
    # Test workflow routing
    answer, responses, scores = await coordinator.orchestrate("How do I intake a new customer vehicle step by step?")
    assert len(responses) > 0
    assert any(r.agent_name == "WorkflowAgent" for r in responses)

    # Test unknown query routing does not fail
    answer_un, resp_un, scores_un = await coordinator.orchestrate("xyz 123 random nonsense query")
    assert len(resp_un) > 0
