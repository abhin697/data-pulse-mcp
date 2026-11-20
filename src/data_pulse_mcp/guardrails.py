import re

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|COPY)\b",
    re.IGNORECASE,
)

def validate_and_cap_sql(query: str, max_rows: int = 100) -> str:
    """Ensures queries are strictly read-only and capped to protect LLM context."""
    cleaned = query.strip().rstrip(";")
    if FORBIDDEN_KEYWORDS.search(cleaned):
        raise ValueError("Security Policy: Only read-only SELECT/WITH queries are allowed.")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Query must start with SELECT or WITH.")
    if not re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {max_rows}"
    return cleaned