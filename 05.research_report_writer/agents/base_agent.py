# agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from tools.tool_registry import tool_registry
import os
from openai import OpenAI

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, role: str, allowed_tools: List[str]):
        self.name = name
        self.role = role
        self.allowed_tools = allowed_tools
        self.tools = {tool: tool_registry.get_tool(tool) 
                     for tool in allowed_tools if tool_registry.get_tool(tool)}
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    def use_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Use a tool that this agent has access to"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available to {self.name}")
        tool = self.tools[tool_name]
        return tool.execute(*args, **kwargs)
    
    @abstractmethod
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Execute the agent's task"""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, role={self.role})"

