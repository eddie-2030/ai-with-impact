# agents/code_analyzer_agent.py
import ast
from typing import Dict, Optional
from .base_agent import BaseAgent

class CodeAnalyzerAgent(BaseAgent):
    """Agent responsible for analyzing code structure and patterns"""
    
    def __init__(self):
        super().__init__(
            name="code_analyzer",
            role="Code Structure Analysis",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Analyze code structure"""
        code = task.get("code", "")
        language = task.get("language", "python")
        
        analysis = {
            "language": language,
            "lines_of_code": len(code.split('\n')),
            "structure": {},
            "complexity": {}
        }
        
        if language.lower() == "python":
            analysis.update(self._analyze_python(code))
        elif language.lower() == "sql":
            analysis.update(self._analyze_sql(code))
        
        return {
            "analysis": analysis,
            "status": "completed"
        }
    
    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code structure"""
        try:
            tree = ast.parse(code)
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "lines": node.end_lineno - node.lineno if node.end_lineno else 1
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
            
            return {
                "structure": {
                    "functions": len(functions),
                    "classes": len(classes),
                    "function_list": functions
                },
                "complexity": {
                    "cyclomatic_complexity": "medium"  # Simplified
                }
            }
        except SyntaxError:
            return {
                "structure": {"error": "Syntax error in code"},
                "complexity": {}
            }
    
    def _analyze_sql(self, code: str) -> Dict:
        """Analyze SQL code structure"""
        queries = code.split(';')
        return {
            "structure": {
                "queries": len([q for q in queries if q.strip()]),
                "has_select": "SELECT" in code.upper(),
                "has_insert": "INSERT" in code.upper(),
                "has_update": "UPDATE" in code.upper(),
                "has_delete": "DELETE" in code.upper()
            },
            "complexity": {}
        }

