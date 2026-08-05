from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.registry import AgentRegistry
from app.core.config import settings
from app.core.exceptions import (
    BaseAppException,
    app_exception_handler,
    generic_exception_handler,
)
from app.routers import chat, documents, health, tickets
from app.services.database.connection import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    await db_manager.connect()
    AgentRegistry.get_registry().discover_agents()
    yield
    # Shutdown actions
    await db_manager.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-Ready Multi-Agent AI Onboarding Assistant Backend for Electric Motorcycle Dealerships",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(tickets.router)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }
