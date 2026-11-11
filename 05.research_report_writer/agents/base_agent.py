from abc import ABC, abstractmethod
import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI, OpenAIError

from tools.tool_registry import tool_registry


class ModelUnavailable(RuntimeError):
    """An actionable, safe error from a model-dependent stage."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class BaseAgent(ABC):
    def __init__(self, name: str, role: str, allowed_tools: List[str]):
        self.name = name
        self.role = role
        self.allowed_tools = allowed_tools
        self.tools = {tool: tool_registry.get_tool(tool)
                      for tool in allowed_tools if tool_registry.get_tool(tool)}

    def use_tool(self, tool_name: str, *args, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available to {self.name}")
        return self.tools[tool_name].execute(*args, **kwargs)

    def complete_json(self, system: str, prompt: str) -> dict:
        """Initialize the SDK only when a live stage needs a model response."""
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise ModelUnavailable("model_not_configured", "Set OPENAI_API_KEY on the server.")
        try:
            with OpenAI(api_key=key, timeout=30, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
        except OpenAIError as exc:
            raise ModelUnavailable(
                "model_unavailable", "The model request failed. Check model access or try again later."
            ) from exc
        except (AttributeError, RecursionError, TypeError, ValueError) as exc:
            raise self.invalid_response() from exc

        try:
            choices = response.choices
            if not isinstance(choices, list) or not choices:
                raise ValueError("Missing choices")
            choice = choices[0]
            if choice.finish_reason != "stop":
                raise ValueError("Incomplete completion")
            content = json.loads(choice.message.content)
            if not isinstance(content, dict):
                raise ValueError("Expected an object")
        except (AttributeError, RecursionError, TypeError, ValueError) as exc:
            raise self.invalid_response() from exc
        return content

    @staticmethod
    def invalid_response() -> ModelUnavailable:
        return ModelUnavailable("model_invalid_response", "The model returned an unusable research result.")

    @abstractmethod
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, role={self.role})"
