# agents/research_agent.py
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from .base_agent import BaseAgent
from tools.tool_registry import tool_registry

class ResearchAgent(BaseAgent):
    """Agent responsible for gathering information from various sources"""
    
    def __init__(self):
        super().__init__(
            name="research_agent",
            role="Information Gathering",
            allowed_tools=["web_search", "scrape_webpage"]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Execute research task"""
        query = task.get("query", "")
        max_sources = task.get("max_sources", 10)
        
        findings = []
        sources = []
        
        # Search for information
        search_results = self.use_tool("web_search", query=query, num_results=max_sources)
        
        for result in search_results[:max_sources]:
            url = result.get("url", "")
            if not url:
                continue
            
            # Scrape the webpage
            scraped = self.use_tool("scrape_webpage", url=url)
            
            if scraped.get("success"):
                # Extract source metadata
                metadata = scraped.get("metadata", {})
                source_id = str(uuid.uuid4())
                
                # Use LLM to extract structured information
                content = scraped.get("content", "")[:5000]  # Limit for LLM
                
                # Extract key information using LLM
                extraction_prompt = f"""Extract key information from this webpage content related to: {query}

Content:
{content}

Return JSON with:
- key_findings: List of key findings
- authors: List of authors (if available)
- publication_date: Publication date (YYYY-MM-DD or null)
- source_type: Type (academic_paper, news_article, report, website)
- publisher: Publisher or organization name

Return ONLY valid JSON."""
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You extract structured information from web content. Return valid JSON only."},
                            {"role": "user", "content": extraction_prompt}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    
                    extracted = json.loads(response.choices[0].message.content)
                    key_findings = extracted.get("key_findings", [])
                    authors = extracted.get("authors", [])
                    
                    # Create source record
                    source = {
                        "source_id": source_id,
                        "title": metadata.get("title", result.get("title", "Untitled")),
                        "authors": authors if authors else [],
                        "publication_date": extracted.get("publication_date") or metadata.get("publication_date"),
                        "url": url,
                        "source_type": extracted.get("source_type", "website"),
                        "publisher": extracted.get("publisher") or metadata.get("publisher", ""),
                        "access_date": datetime.now().date().isoformat()
                    }
                    sources.append(source)
                    
                    # Create findings
                    for finding in key_findings:
                        findings.append({
                            "content": finding,
                            "source_id": source_id,
                            "quote": finding if len(finding) < 200 else None,
                            "confidence_score": 0.7
                        })
                
                except Exception as e:
                    print(f"Error extracting from {url}: {e}")
                    # Still add source even if extraction fails
                    source = {
                        "source_id": source_id,
                        "title": metadata.get("title", result.get("title", "Untitled")),
                        "authors": metadata.get("author", "").split(",") if metadata.get("author") else [],
                        "publication_date": metadata.get("publication_date"),
                        "url": url,
                        "source_type": "website",
                        "publisher": metadata.get("publisher", ""),
                        "access_date": datetime.now().date().isoformat()
                    }
                    sources.append(source)
                    
                    findings.append({
                        "content": scraped.get("content", "")[:500],
                        "source_id": source_id,
                        "confidence_score": 0.5
                    })
        
        return {
            "findings": findings,
            "sources": sources,
            "status": "completed"
        }

