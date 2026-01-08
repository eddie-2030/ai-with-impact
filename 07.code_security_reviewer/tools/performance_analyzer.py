# tools/performance_analyzer.py
import re
from typing import Dict, List
from .base_tool import BaseTool

class PerformanceAnalyzerTool(BaseTool):
    """Tool for analyzing code performance issues"""
    
    def __init__(self):
        super().__init__(
            name="performance_analyzer",
            description="Analyze code for performance issues and inefficiencies"
        )
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize performance issue patterns"""
        self.patterns = {
            "n_plus_one": {
                "pattern": re.compile(r'for\s+\w+\s+in\s+\w+.*:\s*\n.*\.objects\.filter|\.objects\.get', re.MULTILINE),
                "severity": "high",
                "description": "N+1 query problem detected"
            },
            "nested_loop": {
                "pattern": re.compile(r'for\s+\w+\s+in.*:\s*\n\s+for\s+\w+\s+in', re.MULTILINE),
                "severity": "medium",
                "description": "Nested loops detected - potential O(n²) complexity"
            },
            "missing_index": {
                "pattern": re.compile(r'WHERE\s+\w+\s*=', re.IGNORECASE),
                "severity": "medium",
                "description": "Query may benefit from index"
            },
            "inefficient_search": {
                "pattern": re.compile(r'for\s+\w+\s+in\s+\w+.*:\s*\n.*if\s+\w+\s*==', re.MULTILINE),
                "severity": "medium",
                "description": "Linear search in loop - consider using set or dict"
            }
        }
    
    def execute(self, code: str, language: str = "python") -> Dict:
        """Analyze code for performance issues"""
        findings = []
        
        lines = code.split('\n')
        
        # Check for N+1 query problem (Python/Django specific)
        if language.lower() == "python":
            n_plus_one = self._check_n_plus_one(code)
            findings.extend(n_plus_one)
            
            # Check for inefficient algorithms
            algo_issues = self._check_algorithm_efficiency(code)
            findings.extend(algo_issues)
        
        # Check for missing indexes in SQL
        if language.lower() == "sql":
            index_issues = self._check_missing_indexes(code)
            findings.extend(index_issues)
        
        # Check for nested loops
        nested_loops = self._check_nested_loops(code)
        findings.extend(nested_loops)
        
        return {
            "findings": findings,
            "total_findings": len(findings),
            "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
            "high_count": sum(1 for f in findings if f["severity"] == "high"),
            "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
            "low_count": sum(1 for f in findings if f["severity"] == "low")
        }
    
    def _check_n_plus_one(self, code: str) -> List[Dict]:
        """Check for N+1 query problems"""
        findings = []
        lines = code.split('\n')
        
        # Look for query inside loop
        in_loop = False
        for line_num, line in enumerate(lines, 1):
            if re.match(r'\s*for\s+', line):
                in_loop = True
                loop_start = line_num
            elif re.match(r'\s*(if|elif|else|def|class)', line) and in_loop:
                in_loop = False
            elif in_loop and re.search(r'\.objects\.(filter|get|all)\(', line):
                findings.append({
                    "finding_type": "n_plus_one",
                    "severity": "high",
                    "description": "N+1 query problem: Database query inside loop",
                    "line_number": line_num,
                    "code_snippet": line.strip(),
                    "current_complexity": "O(n)",
                    "suggested_complexity": "O(1)",
                    "confidence_score": 85.0
                })
        
        return findings
    
    def _check_algorithm_efficiency(self, code: str) -> List[Dict]:
        """Check for inefficient algorithms"""
        findings = []
        lines = code.split('\n')
        
        # Check for nested loops
        for line_num, line in enumerate(lines, 1):
            if re.search(r'for\s+\w+\s+in.*:\s*\n.*for\s+\w+\s+in', code[code.find(line):code.find(line)+200], re.MULTILINE):
                findings.append({
                    "finding_type": "nested_loop",
                    "severity": "medium",
                    "description": "Nested loops detected - O(n²) complexity",
                    "line_number": line_num,
                    "code_snippet": line.strip(),
                    "current_complexity": "O(n²)",
                    "suggested_complexity": "O(n)",
                    "confidence_score": 80.0
                })
        
        return findings
    
    def _check_missing_indexes(self, sql_code: str) -> List[Dict]:
        """Check SQL for missing indexes"""
        findings = []
        lines = sql_code.split('\n')
        
        # Simple heuristic: WHERE clauses without CREATE INDEX
        has_where = False
        has_index = "CREATE INDEX" in sql_code.upper()
        
        for line in lines:
            if re.search(r'WHERE\s+\w+\s*=', line, re.IGNORECASE):
                has_where = True
        
        if has_where and not has_index:
            findings.append({
                "finding_type": "missing_index",
                "severity": "medium",
                "description": "Query may benefit from index on WHERE clause columns",
                "line_number": 1,
                "code_snippet": "WHERE clause detected",
                "current_complexity": "O(n)",
                "suggested_complexity": "O(log n)",
                "confidence_score": 70.0
            })
        
        return findings
    
    def _check_nested_loops(self, code: str) -> List[Dict]:
        """Check for nested loops"""
        findings = []
        lines = code.split('\n')
        in_outer_loop = False
        
        for line_num, line in enumerate(lines, 1):
            if re.match(r'\s*for\s+', line):
                if in_outer_loop:
                    findings.append({
                        "finding_type": "nested_loop",
                        "severity": "medium",
                        "description": "Nested loop detected - consider optimization",
                        "line_number": line_num,
                        "code_snippet": line.strip(),
                        "current_complexity": "O(n²)",
                        "suggested_complexity": "O(n)",
                        "confidence_score": 75.0
                    })
                in_outer_loop = True
            elif re.match(r'\s*(if|elif|else|def|class)', line):
                in_outer_loop = False
        
        return findings

