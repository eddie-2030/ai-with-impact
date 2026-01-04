# tools/citation_formatter.py
from typing import Dict, List, Optional
from datetime import datetime
from .base_tool import BaseTool

class APACitationFormatter(BaseTool):
    """Tool for formatting citations in APA 7th edition style"""
    
    def __init__(self):
        super().__init__(
            name="format_apa_citation",
            description="Format sources in APA 7th edition citation style"
        )
    
    def execute(self, source: Dict) -> str:
        """Format a source in APA style"""
        source_type = source.get("source_type", "website")
        
        if source_type == "academic_paper":
            return self._format_academic_paper(source)
        elif source_type == "web_article":
            return self._format_web_article(source)
        elif source_type == "report":
            return self._format_report(source)
        elif source_type == "news_article":
            return self._format_news_article(source)
        else:
            return self._format_website(source)
    
    def _format_academic_paper(self, source: Dict) -> str:
        """Format academic paper citation"""
        authors = source.get("authors", [])
        title = source.get("title", "Untitled")
        publisher = source.get("publisher", "")
        publication_date = source.get("publication_date", "")
        doi = source.get("doi", "")
        
        # Format authors
        if authors:
            author_str = self._format_authors(authors)
        else:
            author_str = "Anonymous"
        
        # Format date
        date_str = self._format_date(publication_date)
        
        # Build citation
        citation = f"{author_str} ({date_str}). {title}. {publisher}"
        
        if doi:
            citation += f". https://doi.org/{doi}"
        elif source.get("url"):
            citation += f". {source['url']}"
        
        return citation
    
    def _format_web_article(self, source: Dict) -> str:
        """Format web article citation"""
        authors = source.get("authors", [])
        title = source.get("title", "Untitled")
        publisher = source.get("publisher", "")
        publication_date = source.get("publication_date", "")
        url = source.get("url", "")
        access_date = source.get("access_date", datetime.now().date().isoformat())
        
        author_str = self._format_authors(authors) if authors else "Anonymous"
        date_str = self._format_date(publication_date)
        access_date_str = self._format_date(access_date)
        
        citation = f"{author_str} ({date_str}). {title}. {publisher}. Retrieved {access_date_str}, from {url}"
        
        return citation
    
    def _format_report(self, source: Dict) -> str:
        """Format report citation"""
        authors = source.get("authors", [])
        title = source.get("title", "Untitled")
        publisher = source.get("publisher", "")
        publication_date = source.get("publication_date", "")
        url = source.get("url", "")
        
        author_str = self._format_authors(authors) if authors else publisher
        date_str = self._format_date(publication_date)
        
        citation = f"{author_str}. ({date_str}). {title}. {publisher}"
        if url:
            citation += f". {url}"
        
        return citation
    
    def _format_news_article(self, source: Dict) -> str:
        """Format news article citation"""
        authors = source.get("authors", [])
        title = source.get("title", "Untitled")
        publisher = source.get("publisher", "")
        publication_date = source.get("publication_date", "")
        url = source.get("url", "")
        
        author_str = self._format_authors(authors) if authors else "Anonymous"
        date_str = self._format_date(publication_date)
        
        citation = f"{author_str} ({date_str}). {title}. {publisher}. {url}"
        
        return citation
    
    def _format_website(self, source: Dict) -> str:
        """Format general website citation"""
        title = source.get("title", "Untitled")
        publisher = source.get("publisher", "")
        url = source.get("url", "")
        access_date = source.get("access_date", datetime.now().date().isoformat())
        
        date_str = self._format_date(access_date)
        
        if publisher:
            citation = f"{publisher}. ({date_str}). {title}. Retrieved {date_str}, from {url}"
        else:
            citation = f"{title}. (n.d.). Retrieved {date_str}, from {url}"
        
        return citation
    
    def _format_authors(self, authors: List[str]) -> str:
        """Format author list for APA style"""
        if not authors:
            return "Anonymous"
        
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        else:
            return f"{authors[0]}, {', '.join(authors[1:-1])}, & {authors[-1]}"
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date for APA style"""
        if not date_str:
            return "n.d."
        
        try:
            # Try to parse and format date
            if isinstance(date_str, str):
                # Extract year if full date
                parts = date_str.split("-")
                if len(parts) >= 1:
                    return parts[0]
            return date_str
        except:
            return date_str if date_str else "n.d."
    
    def generate_in_text_citation(self, source: Dict, page_number: Optional[str] = None) -> str:
        """Generate in-text citation (Author, Year) or (Author, Year, p. X)"""
        authors = source.get("authors", [])
        publication_date = source.get("publication_date", "")
        
        year = self._format_date(publication_date)
        if authors:
            author = authors[0].split()[-1]  # Last name
            citation = f"({author}, {year})"
        else:
            citation = f"(Anonymous, {year})"
        
        if page_number:
            citation = citation.replace(")", f", {page_number})")
        
        return citation
    
    def format_reference_list(self, sources: List[Dict]) -> str:
        """Format list of sources as APA reference list"""
        # Sort alphabetically by first author's last name
        sorted_sources = sorted(sources, key=lambda x: (
            x.get("authors", ["Z"])[0].split()[-1] if x.get("authors") else "Z"
        ))
        
        references = []
        for source in sorted_sources:
            citation = self.execute(source)
            references.append(citation)
        
        return "\n\n".join(references)

