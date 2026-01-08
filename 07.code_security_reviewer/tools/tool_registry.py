# tools/tool_registry.py
from typing import Dict, Optional
from .base_tool import BaseTool
from .security_scanner import SecurityScannerTool
from .performance_analyzer import PerformanceAnalyzerTool

class ToolRegistry:
    """Central registry for all agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._initialize_default_tools()
    
    def _initialize_default_tools(self):
        """Initialize default tools"""
        self.register_tool("security_scanner", SecurityScannerTool())
        self.register_tool("performance_analyzer", PerformanceAnalyzerTool())
    
    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool"""
        self.tools[name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> list:
        """List all available tools"""
        return list(self.tools.keys())

# Global tool registry instance
tool_registry = ToolRegistry()

