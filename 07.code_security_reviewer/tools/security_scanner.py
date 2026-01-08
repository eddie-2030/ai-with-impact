# tools/security_scanner.py
import re
from typing import Dict, List
from .base_tool import BaseTool

class SecurityScannerTool(BaseTool):
    """Tool for scanning code for security vulnerabilities"""
    
    def __init__(self):
        super().__init__(
            name="security_scanner",
            description="Scan code for security vulnerabilities (OWASP Top 10, CWE)"
        )
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize security vulnerability patterns"""
        self.patterns = {
            "sql_injection": {
                "pattern": re.compile(r'(SELECT|INSERT|UPDATE|DELETE).*[+\'"]\s*\+.*|f["\'].*SELECT|["\'].*\+.*SELECT', re.IGNORECASE),
                "cwe": "CWE-89",
                "owasp": "A03:2021",
                "severity": "critical"
            },
            "hardcoded_secret": {
                "pattern": re.compile(r'(api[_-]?key|password|secret|token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
                "cwe": "CWE-798",
                "owasp": "A07:2021",
                "severity": "critical"
            },
            "xss": {
                "pattern": re.compile(r'innerHTML\s*=|\.html\(|document\.write\(', re.IGNORECASE),
                "cwe": "CWE-79",
                "owasp": "A03:2021",
                "severity": "high"
            },
            "command_injection": {
                "pattern": re.compile(r'(os\.system|subprocess\.call|exec\(|eval\()', re.IGNORECASE),
                "cwe": "CWE-78",
                "owasp": "A03:2021",
                "severity": "critical"
            },
            "path_traversal": {
                "pattern": re.compile(r'open\(.*\+.*|file\(.*\+.*', re.IGNORECASE),
                "cwe": "CWE-22",
                "owasp": "A01:2021",
                "severity": "high"
            },
            "insecure_random": {
                "pattern": re.compile(r'random\.randint|random\.choice', re.IGNORECASE),
                "cwe": "CWE-330",
                "owasp": "A02:2021",
                "severity": "medium"
            }
        }
    
    def execute(self, code: str, language: str = "python") -> Dict:
        """Scan code for security vulnerabilities"""
        findings = []
        
        lines = code.split('\n')
        
        for pattern_name, pattern_info in self.patterns.items():
            for line_num, line in enumerate(lines, 1):
                if pattern_info["pattern"].search(line):
                    findings.append({
                        "finding_type": pattern_name,
                        "severity": pattern_info["severity"],
                        "cwe_id": pattern_info["cwe"],
                        "owasp_category": pattern_info["owasp"],
                        "description": f"Potential {pattern_name.replace('_', ' ').title()} vulnerability detected",
                        "line_number": line_num,
                        "code_snippet": line.strip(),
                        "confidence_score": 85.0
                    })
        
        # Additional checks for SQL injection in SQL files
        if language.lower() == "sql":
            sql_findings = self._check_sql_injection(code)
            findings.extend(sql_findings)
        
        return {
            "findings": findings,
            "total_findings": len(findings),
            "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
            "high_count": sum(1 for f in findings if f["severity"] == "high"),
            "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
            "low_count": sum(1 for f in findings if f["severity"] == "low")
        }
    
    def _check_sql_injection(self, sql_code: str) -> List[Dict]:
        """Check SQL code for injection vulnerabilities"""
        findings = []
        lines = sql_code.split('\n')
        
        # Check for string concatenation in SQL
        for line_num, line in enumerate(lines, 1):
            if re.search(r"['\"]\s*\+\s*|['\"]\s*\|\|", line, re.IGNORECASE):
                findings.append({
                    "finding_type": "sql_injection",
                    "severity": "critical",
                    "cwe_id": "CWE-89",
                    "owasp_category": "A03:2021",
                    "description": "SQL injection vulnerability: String concatenation in SQL query",
                    "line_number": line_num,
                    "code_snippet": line.strip(),
                    "confidence_score": 90.0
                })
        
        return findings

