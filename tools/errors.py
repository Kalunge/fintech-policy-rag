"""Consistent error type for all tool failures.

Tool implementations (mock or live) raise ToolError so the agent sees a
predictable, structured failure regardless of what actually went wrong
upstream. The agent loop converts these into messages the LLM can read
and react to.
"""
from __future__ import annotations


class ToolError(Exception):
    """Raised by any tool implementation when a call cannot be completed.

    Attributes:
        code: a stable machine-readable identifier (e.g., AGENT_NOT_FOUND).
              The agent uses this to decide whether to retry, reformulate,
              or give up.
        message: human-readable explanation suitable for the LLM to read
                 and summarise for the user.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message

    def as_dict(self) -> dict:
        return {"error": True, "code": self.code, "message": self.message}
