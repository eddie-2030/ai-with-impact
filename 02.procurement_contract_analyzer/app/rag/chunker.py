import regex as re
from typing import List, Tuple

def split_into_clauses(text: str) -> List[Tuple[str, str]]:
    """Split text into (title, body) clauses.
    Heuristics: headings by numbers, all-caps, or '###' marks.
    """
    lines = text.splitlines()
    clauses = []
    current_title = "Preamble"
    buf = []
    hdr_pat = re.compile(r'^(?:\d+(?:\.\d+)*\.?\s+|#{1,6}\s+|[A-Z][A-Z \-/]{3,})')
    for ln in lines:
        if hdr_pat.match(ln.strip()):
            if buf:
                clauses.append((current_title.strip(), "\n".join(buf).strip()))
                buf = []
            current_title = ln.strip().lstrip('#').strip()
        else:
            buf.append(ln)
    if buf:
        clauses.append((current_title.strip(), "\n".join(buf).strip()))
    # assign ids
    return [(f"clause_{i+1:03d}:{title}", body) for i, (title, body) in enumerate(clauses)]
