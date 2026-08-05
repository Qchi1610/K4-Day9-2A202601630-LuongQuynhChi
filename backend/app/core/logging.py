import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional
from app.core.config import settings


class StructuredLogger:
    """Structured JSON Logger for Agent Execution & Request Metrics."""

    def __init__(self, name: str = "onboarding_backend"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(settings.LOG_LEVEL.upper())

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **extra):
        log_payload = {
            "timestamp": time.time(),
            "level": level.upper(),
            "message": message,
            **extra
        }
        log_str = json.dumps(log_payload, default=str)
        if level.upper() == "ERROR":
            self.logger.error(log_str)
        elif level.upper() == "WARNING":
            self.logger.warning(log_str)
        else:
            self.logger.info(log_str)

    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)

    def log_agent_execution(
        self,
        request_id: str,
        session_id: str,
        agent_selected: List[str],
        latency_ms: float,
        tokens: int = 0,
        cost: float = 0.0,
        retrieved_documents: Optional[List[str]] = None,
        tool_calls: Optional[List[str]] = None,
        routing_score: Optional[Dict[str, float]] = None,
    ):
        self.info(
            message="Agent Execution Summary",
            request_id=request_id,
            session_id=session_id,
            agent_selected=agent_selected,
            latency_ms=round(latency_ms, 2),
            tokens=tokens,
            cost=round(cost, 6),
            retrieved_documents=retrieved_documents or [],
            tool_calls=tool_calls or [],
            routing_score=routing_score or {},
        )


logger = StructuredLogger()
