import re
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.exceptions import PromptInjectionDetectedException

# Basic patterns associated with prompt injection & system instruction overrides
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+prompts",
    r"system\s*:\s*you\s+are",
    r"override\s+system\s+prompt",
    r"forget\s+everything\s+you\s+were\s+told",
    r"you\s+are\s+now\s+DAN",
    r"act\s+as\s+an?\s+unrestricted",
    r"jailbreak",
]

ALLOWED_ROLES = ["technician", "sales_rep", "store_manager", "service_advisor", "admin"]


class SecurityGuardrail:
    """Security Guardrail for Prompt Injection Detection, Output Filtering, and RBAC."""

    @staticmethod
    def detect_prompt_injection(user_input: str) -> None:
        """Scan input string for common injection attempts."""
        if not settings.PROMPT_INJECTION_PROTECTION:
            return

        normalized_input = user_input.lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, normalized_input, re.IGNORECASE):
                raise PromptInjectionDetectedException(
                    reason=f"Security risk: Potential prompt injection pattern detected: '{pattern}'"
                )

    @staticmethod
    def sanitize_output(output_text: str) -> str:
        """Filter system leakage or sensitive key tokens from response."""
        if not output_text:
            return ""
        
        # Redact potential API keys or tokens if leaked
        sanitized = re.sub(r"sk-[a-zA-Z0-9]{32,}", "[REDACTED_API_KEY]", output_text)
        sanitized = re.sub(r"sk-or-v1-[a-zA-Z0-9]{32,}", "[REDACTED_API_KEY]", sanitized)
        return sanitized

    @staticmethod
    def validate_user_role(role: str) -> str:
        """Enforce RBAC role standardizing."""
        normalized = role.lower().strip() if role else "sales_rep"
        if normalized not in ALLOWED_ROLES:
            return "sales_rep"  # default safe fallback
        return normalized


class RateLimiter:
    """Simple in-memory sliding window rate limiter per session/user."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_timestamps: Dict[str, List[float]] = {}

    def is_rate_limited(self, identifier: str, current_time: float) -> bool:
        if identifier not in self.request_timestamps:
            self.request_timestamps[identifier] = []

        # Remove old timestamps outside window
        cutoff = current_time - self.window_seconds
        self.request_timestamps[identifier] = [
            ts for ts in self.request_timestamps[identifier] if ts > cutoff
        ]

        if len(self.request_timestamps[identifier]) >= self.max_requests:
            return True

        self.request_timestamps[identifier].append(current_time)
        return False


security_guardrail = SecurityGuardrail()
rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE)
