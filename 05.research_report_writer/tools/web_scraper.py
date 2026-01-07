# tools/web_scraper.py
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from datetime import datetime
from .base_tool import BaseTool
import re

class WebScraperTool(BaseTool):
    """Tool for scraping and extracting content from web pages"""
    
    def __init__(self):
        super().__init__(
            name="scrape_webpage",
            description="Scrape and extract content from web pages"
        )
    
    def execute(self, url: str) -> Dict:
        """Scrape webpage and extract content and metadata"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            # Extract main content (try article tag, then body)
            article = soup.find('article')
            if article:
                content = article.get_text(separator=' ', strip=True)
            else:
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                content = soup.get_text(separator=' ', strip=True)
            
            # Extract metadata
            metadata = {
                "title": title_text,
                "url": url,
                "access_date": datetime.now().date().isoformat(),
                "content_length": len(content)
            }
            
            # Try to extract author from meta tags
            author_tag = soup.find('meta', {'name': re.compile('author', re.I)})
            if author_tag:
                metadata["author"] = author_tag.get('content', '')
            
            # Try to extract publication date
            date_tag = soup.find('meta', {'property': re.compile('published', re.I)})
            if date_tag:
                metadata["publication_date"] = date_tag.get('content', '')
            
            return {
                "content": content[:10000],  # Limit content length
                "metadata": metadata,
                "success": True
            }
        except Exception as e:
            return {
                "content": "",
                "metadata": {"url": url, "error": str(e)},
                "success": False
            }


