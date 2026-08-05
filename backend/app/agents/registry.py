import importlib
import inspect
import os
import pkgutil
from typing import Dict, List, Optional, Type

from app.agents.base import BaseAgent, AgentMetadata
from app.core.logging import logger


class AgentRegistry:
    """Dynamic Agent Registry providing auto-discovery, registration, metadata exposure, and lookup."""

    _instance: Optional["AgentRegistry"] = None

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    @classmethod
    def get_registry(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = AgentRegistry()
            cls._instance.discover_agents()
        return cls._instance

    def discover_agents(self, package_path: Optional[str] = None):
        """Dynamically scan agents package directory and instantiate all BaseAgent subclasses."""
        if package_path is None:
            # Default package location: app.agents
            agents_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            agents_dir = package_path

        logger.info(f"Scanning for agent plugins in directory: {agents_dir}")

        for _, name, is_pkg in pkgutil.iter_modules([agents_dir]):
            # Skip base module or special files
            if name in ["base", "registry"]:
                continue

            try:
                module_name = f"app.agents.{name}.agent" if is_pkg else f"app.agents.{name}"
                module = importlib.import_module(module_name)

                for member_name, obj in inspect.getmembers(module, inspect.isclass):
                    # Register classes that inherit from BaseAgent, are not BaseAgent itself, and aren't abstract
                    if (
                        issubclass(obj, BaseAgent)
                        and obj is not BaseAgent
                        and not inspect.isabstract(obj)
                    ):
                        instance = obj()
                        agent_name = instance.metadata.name
                        if agent_name not in self._agents:
                            self._agents[agent_name] = instance
                            logger.info(
                                f"Successfully registered agent plugin: '{agent_name}' with capabilities {instance.metadata.capabilities}"
                            )
            except Exception as e:
                logger.warning(f"Could not load agent module '{name}': {e}")

    def register_agent(self, agent: BaseAgent):
        """Manually register an agent plugin instance."""
        self._agents[agent.metadata.name] = agent
        logger.info(f"Manually registered agent: '{agent.metadata.name}'")

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Look up a registered agent by name."""
        return self._agents.get(agent_name)

    def list_agents(self) -> List[BaseAgent]:
        """Return all registered agent instances."""
        return list(self._agents.values())

    def list_agent_metadata(self) -> List[AgentMetadata]:
        """Return metadata for all registered agents."""
        return [agent.metadata for agent in self._agents.values()]
