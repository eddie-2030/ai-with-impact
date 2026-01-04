# tools/tool_registry.py
from typing import Dict, Optional
from .base_tool import BaseTool
from .web_search import WebSearchTool
from .web_scraper import WebScraperTool
from .citation_formatter import APACitationFormatter

class ToolRegistry:
    """Central registry for all agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._initialize_default_tools()
    
    def _initialize_default_tools(self):
        """Initialize default tools"""
        self.register_tool("web_search", WebSearchTool())
        self.register_tool("scrape_webpage", WebScraperTool())
        self.register_tool("format_apa_citation", APACitationFormatter())
    
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

