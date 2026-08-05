from typing import Any, Dict, Optional
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse


class BaseAppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AgentExecutionException(BaseAppException):
    """Raised when an agent execution fails."""

    def __init__(self, agent_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Agent '{agent_name}' execution error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class LLMProviderException(BaseAppException):
    """Raised when LLM provider fails or responds unexpectedly."""

    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"LLM Provider '{provider}' error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RAGPipelineException(BaseAppException):
    """Raised when retrieval or embedding operations fail."""

    def __init__(self, message: str):
        super().__init__(
            message=f"RAG Pipeline error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class PromptInjectionDetectedException(BaseAppException):
    """Raised when malicious prompt injection is detected."""

    def __init__(self, reason: str = "Potential prompt injection detected"):
        super().__init__(
            message=reason,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ResourceNotFoundException(BaseAppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with ID '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Global handler for application custom exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected server error occurred.",
            "details": str(exc) if request.app.debug else {},
            "path": str(request.url),
        },
    )
