# ingest/anonymize.py
import regex as re
from typing import Tuple

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:(?:\+?1\s*[-.]?\s*)?(?:\(\d{3}\)|\d{3})\s*[-.]?\s*\d{3}\s*[-.]?\s*\d{4})")
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
NAME_HINT_RE = re.compile(r"\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+\b")

REPLACERS = [
    (EMAIL_RE, "<EMAIL>"),
    (PHONE_RE, "<PHONE>"),
    (CC_RE, "<CARD>"),
    (NAME_HINT_RE, "<NAME>")
]

def anonymize(text: str) -> Tuple[str, int]:
    replaced = text
    count = 0
    for pattern, token in REPLACERS:
        replaced, c = pattern.subn(token, replaced)
        count += c
    return replaced, count
