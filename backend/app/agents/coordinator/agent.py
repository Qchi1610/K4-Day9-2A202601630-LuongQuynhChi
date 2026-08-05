import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import AgentMetadata, AgentResponse, BaseAgent
from app.agents.registry import AgentRegistry
from app.core.exceptions import AgentExecutionException
from app.core.logging import logger
from app.services.llm.factory import LLMFactory


class CoordinatorAgent:
    """Coordinator Agent (Supervisor) enforcing DYNAMIC Agent Discovery & Zero-Hardcode Routing."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/coordinator.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

        self.registry = AgentRegistry.get_registry()

    async def select_and_rank_agents(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[BaseAgent, float]]:
        """Dynamically match query intent against registered agent capabilities & compute match scores."""
        available_agents = self.registry.list_agents()

        if not available_agents:
            logger.warning("No agent plugins registered in AgentRegistry!")
            return []

        # Evaluate capability fit dynamically for every registered agent
        scored_agents: List[Tuple[BaseAgent, float]] = []
        for agent in available_agents:
            score = await agent.can_handle(query=query, context=context)
            scored_agents.append((agent, score))

        # Sort agents by score descending
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        return scored_agents

    async def execute_agents(
        self,
        query: str,
        selected_agents: List[BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[AgentResponse]:
        """Execute selected agent(s) asynchronously, supporting delegation and parallel execution."""
        if not selected_agents:
            return []

        tasks = [agent.execute(query=query, context=context) for agent in selected_agents]
        responses: List[AgentResponse] = await asyncio.gather(*tasks, return_exceptions=True)

        final_responses: List[AgentResponse] = []
        for agent, resp in zip(selected_agents, responses):
            if isinstance(resp, Exception):
                logger.error(f"Agent '{agent.metadata.name}' failed with error: {resp}")
                final_responses.append(
                    AgentResponse(
                        agent_name=agent.metadata.name,
                        content=f"Agent '{agent.metadata.name}' encountered an error.",
                        confidence=0.0,
                    )
                )
            else:
                final_responses.append(resp)

                # Check for agent delegation (e.g. TroubleshootingAgent -> TicketAgent if low confidence)
                if resp.delegate_to:
                    logger.info(f"Agent '{agent.metadata.name}' requested delegation to '{resp.delegate_to}'")
                    delegate_agent = self.registry.get_agent(resp.delegate_to)
                    if delegate_agent and delegate_agent not in selected_agents:
                        del_resp = await delegate_agent.execute(query=query, context=context)
                        final_responses.append(del_resp)

        return final_responses

    async def aggregate_responses(
        self, query: str, agent_responses: List[AgentResponse]
    ) -> str:
        """Merge single or multiple agent responses into one coherent answer."""
        if not agent_responses:
            return "I apologize, but no specialized agent was able to process your request."

        if len(agent_responses) == 1:
            return agent_responses[0].content

        # Multiple agent outputs: synthesize using LLM or structured aggregation
        combined_text = "\n\n---\n\n".join(
            [f"### [{resp.agent_name}]\n{resp.content}" for resp in agent_responses]
        )

        synthesis_prompt = (
            f"User Question: {query}\n\n"
            f"Outputs from specialized agents:\n{combined_text}\n\n"
            f"Synthesize these agent outputs into a unified, coherent response for the user. "
            f"Do not lose essential citations, diagrams, or ticket details."
        )

        try:
            llm = LLMFactory.get_provider()
            synthesized = await llm.generate(
                prompt=synthesis_prompt,
                system_prompt=self.system_prompt,
                temperature=0.2,
            )
            return synthesized
        except Exception as e:
            logger.warning(f"Response synthesis LLM call failed: {e}. Falling back to combined text.")
            return combined_text

    async def orchestrate(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[AgentResponse], Dict[str, float]]:
        """Main orchestration pipeline: intent evaluation -> agent selection -> execution -> aggregation."""
        context = context or {}

        # Step 1: Dynamic agent discovery & capability ranking
        ranked = await self.select_and_rank_agents(query=query, context=context)
        routing_scores = {agent.metadata.name: score for agent, score in ranked}

        # Step 2: Select top-scoring candidates (or top 2 if close confidence scores)
        selected: List[BaseAgent] = []
        if ranked:
            top_agent, top_score = ranked[0]
            if top_score >= 0.3:
                selected.append(top_agent)

            # Parallel multi-agent execution if second agent has high score (> 0.6)
            if len(ranked) > 1 and ranked[1][1] >= 0.6 and ranked[1][0] not in selected:
                selected.append(ranked[1][0])

        if not selected and ranked:
            # Fallback to top agent if no high scores
            selected.append(ranked[0][0])

        # Step 3: Asynchronous execution
        responses = await self.execute_agents(query=query, selected_agents=selected, context=context)

        # Step 4: Aggregate responses
        final_answer = await self.aggregate_responses(query=query, agent_responses=responses)

        return final_answer, responses, routing_scores


coordinator_agent = CoordinatorAgent()
