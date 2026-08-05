from fastapi import APIRouter
from app.agents.registry import AgentRegistry
from app.core.config import settings

router = APIRouter(prefix="/api/v1/health", tags=["Health & System Metrics"])


@router.get("")
async def health_check():
    """Health check endpoint exposing active provider and registered agent plugin count."""
    registry = AgentRegistry.get_registry()
    agents = registry.list_agent_metadata()

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "model_name": settings.MODEL_NAME,
        "vector_db": settings.VECTOR_DB,
        "registered_agents": [a.name for a in agents],
        "agent_count": len(agents),
    }
