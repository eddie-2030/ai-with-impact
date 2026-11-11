"""Retrieve bounded search excerpts from Tavily or explicit offline fixtures."""

import ipaddress
import json
import os
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

from .base_tool import BaseTool

SEARCH_URL = "https://api.tavily.com/search"
MAX_RESULTS = 20
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_QUERY_LENGTH = 4000
_PLACEHOLDER_HOSTS = {"example.com", "example.net", "example.org", "localhost"}
_FIXTURES = (
    {
        "title": "Fixture: solar output measurements",
        "url": "https://research-fixture.invalid/solar-output",
        "snippet": "Synthetic example: the test panel produced more electricity at midday than at sunrise.",
    },
    {
        "title": "Fixture: measurement caveats",
        "url": "https://research-fixture.invalid/measurement-caveats",
        "snippet": "Synthetic example: panel angle and cloud cover varied during the demonstration.",
    },
)


class SearchUnavailable(RuntimeError):
    """Search failed with a public, safe error message."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _usable_text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _url_key(value: str) -> tuple | None:
    """Validate a citation URL and ignore fragments for deduplication."""
    if not value or len(value) > 2048 or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 or char in "\\<>\"'`" for char in value
    ):
        return None
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").rstrip(".")
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or parts.username is not None or not host or port == 0:
        return None
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            host = host.encode("idna").decode("ascii").lower().rstrip(".")
        except UnicodeError:
            return None
        if "." not in host or host.endswith((".invalid", ".test", ".example", ".localhost", ".local")):
            return None
        if any(host == blocked or host.endswith("." + blocked) for blocked in _PLACEHOLDER_HOSTS):
            return None
        labels = host.split(".")
        if any(
            not label or label.startswith("-") or label.endswith("-")
            or not label.replace("-", "").isalnum()
            for label in labels
        ):
            return None
    else:
        if not address.is_global or address.is_multicast:
            return None
        host = str(address)
    default_port = 443 if parts.scheme == "https" else 80
    return parts.scheme, host, port or default_port, parts.path or "/", parts.query


def _publication_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(value).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            return None


def _read_results(query: str, count: int, key: str) -> list:
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.post(
                SEARCH_URL,
                json={
                    "query": query,
                    "max_results": count,
                    "search_depth": "basic",
                    "include_published_date": True,
                },
                headers={"Authorization": f"Bearer {key}"},
                timeout=(3.05, 15),
                allow_redirects=False,
                stream=True,
            ) as response:
                if response.status_code in (401, 403):
                    raise SearchUnavailable("search_not_configured", "Check the Tavily API key and its permissions.")
                if response.status_code in (429, 432, 433):
                    raise SearchUnavailable("search_rate_limited", "Tavily has reached a rate or usage limit.")
                if response.status_code != 200:
                    raise SearchUnavailable("search_unavailable", "Tavily could not complete the search.")
                body = bytearray()
                for chunk in response.iter_content(chunk_size=16384):
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise SearchUnavailable("search_invalid_response", "Tavily returned an oversized response.")
                    body.extend(chunk)
    except requests.Timeout as error:
        raise SearchUnavailable("search_timeout", "Tavily search timed out. Try again.") from error
    except requests.RequestException as error:
        raise SearchUnavailable("search_unavailable", "Could not complete the Tavily search.") from error
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError) as error:
        raise SearchUnavailable("search_invalid_response", "Tavily returned an invalid search response.") from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise SearchUnavailable("search_invalid_response", "Tavily returned an invalid search response.")
    return results


class WebSearchTool(BaseTool):
    """Search for sources using the configured provider."""

    def __init__(self):
        super().__init__(name="web_search", description="Search for source URLs and excerpts")

    def execute(self, query: str, num_results: int = 10) -> list[dict]:
        if (
            not isinstance(query, str) or not query.strip() or len(query.strip()) > MAX_QUERY_LENGTH
            or type(num_results) is not int or num_results < 1
        ):
            raise SearchUnavailable("search_invalid_input", "Enter a nonblank search query of at most 4,000 characters and a positive result limit.")
        count = min(num_results, MAX_RESULTS)
        mode = os.getenv("RESEARCH_SEARCH_MODE", "tavily").strip().lower()
        if mode == "fixture":
            return [
                {**fixture, "provider": "fixture", "rank": rank, "publication_date": None}
                for rank, fixture in enumerate(_FIXTURES[:count], start=1)
            ]
        if mode != "tavily":
            raise SearchUnavailable("search_not_configured", "Set RESEARCH_SEARCH_MODE to tavily or fixture.")
        key = os.getenv("TAVILY_API_KEY", "").strip()
        if not key:
            raise SearchUnavailable("search_not_configured", "Set TAVILY_API_KEY to enable Tavily search.")

        raw_results = _read_results(query.strip(), count, key)
        if not raw_results:
            raise SearchUnavailable("search_no_results", "Tavily returned no sources for this query.")
        results = []
        seen = set()
        for rank, raw in enumerate(raw_results[:MAX_RESULTS], start=1):
            if not isinstance(raw, dict):
                continue
            url, title, snippet = (raw.get(field) for field in ("url", "title", "content"))
            if not all(_usable_text(value) for value in (url, title, snippet)):
                continue
            url = url.strip()
            url_key = _url_key(url)
            if url_key is None or url_key in seen:
                continue
            seen.add(url_key)
            item = {
                "url": url,
                "title": title.strip()[:500],
                "snippet": snippet.strip()[:5000],
                "rank": rank,
                "provider": "tavily",
                "publication_date": _publication_date(raw.get("published_date")),
            }
            score = raw.get("score")
            if type(score) in (int, float) and 0 <= score <= 1:
                item["score"] = score
            results.append(item)
            if len(results) == count:
                break
        if not results:
            raise SearchUnavailable("search_invalid_response", "Tavily returned no usable source URLs and excerpts.")
        return results
