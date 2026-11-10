import os
import numpy as np
from typing import Iterable, NoReturn
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


class ProviderUnavailable(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _raise_provider_error(error: OpenAIError) -> NoReturn:
    if isinstance(error, APITimeoutError):
        code, message = "provider_timeout", "The model provider timed out. Try again."
    elif isinstance(error, RateLimitError):
        code, message = "provider_rate_limited", "The model provider rate limit was reached. Try again later."
    elif isinstance(error, (AuthenticationError, PermissionDeniedError)):
        code, message = "provider_not_configured", "Check the API key and model permissions on the server."
    elif isinstance(error, APIConnectionError):
        code, message = "provider_unavailable", "Could not reach the model provider. Try again."
    else:
        code, message = "provider_unavailable", "The model provider could not complete the request."
    raise ProviderUnavailable(code, message) from error


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable(
            "provider_not_configured", "Set OPENAI_API_KEY on the server to enable model requests."
        )
    return OpenAI(api_key=key, timeout=15.0, max_retries=0)

def llm_complete(prompt: str, system: str = "You are a helpful assistant.") -> str:
    try:
        with _client() as client:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=0,
            )
        choices = resp.choices
        content = choices[0].message.content if isinstance(choices, list) and choices else None
    except OpenAIError as error:
        _raise_provider_error(error)
    except (AttributeError, IndexError, TypeError, ValueError):
        content = None
    if not isinstance(content, str) or not content.strip():
        raise ProviderUnavailable("provider_invalid_response", "The provider returned no usable text.")
    return content.strip()

def embed_texts(texts: Iterable[str]) -> np.ndarray:
    texts = list(texts)
    if not texts:
        return np.empty((0, 0), dtype=float)
    if any(not text.strip() for text in texts):
        raise ValueError("Embedding inputs must contain text.")

    invalid = "The provider returned unusable embedding vectors."
    try:
        with _client() as client:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL, input=texts, encoding_format="float"
            )
        rows = sorted(response.data, key=lambda row: row.index)
        if [row.index for row in rows] != list(range(len(texts))):
            raise ValueError("Unexpected embedding indices")
        vectors = np.asarray([row.embedding for row in rows], dtype=float)
        if vectors.ndim != 2:
            raise ValueError("Expected an embedding matrix")
    except OpenAIError as error:
        _raise_provider_error(error)
    except (AttributeError, OverflowError, TypeError, ValueError) as error:
        raise ProviderUnavailable("provider_invalid_response", invalid) from error
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms == 0):
        raise ProviderUnavailable("provider_invalid_response", invalid)
    return vectors / norms

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a)*np.linalg.norm(b))+1e-12))
