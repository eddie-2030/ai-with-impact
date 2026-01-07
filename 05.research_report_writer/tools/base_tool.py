# tools/base_tool.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """Base class for all agent tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with given arguments"""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name})"


