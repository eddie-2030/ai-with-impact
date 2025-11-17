import re
def pii_guard(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b\d{3,}\b", "[REDACTED_NUM]", text)
    return text
