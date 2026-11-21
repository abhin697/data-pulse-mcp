import re

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|COPY|"
    r"INSTALL|LOAD|PRAGMA|EXPORT|IMPORT|CALL|READ_CSV|READ_PARQUET|READ_JSON|READ_TEXT)\b",
    re.IGNORECASE,
)

def validate_and_cap_sql(query: str, max_rows: int = 100) -> str:
    """Ensures queries are strictly read-only, single-statement, and row-capped."""
    cleaned = query.strip().rstrip(";")
    if ";" in cleaned:
        raise ValueError("Security Policy: Multiple stacked SQL statements are not allowed.")
    if FORBIDDEN_KEYWORDS.search(cleaned):
        raise ValueError("Security Policy: Only read-only SELECT/WITH queries are allowed.")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Query must start with SELECT or WITH.")
    if not re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {max_rows}"
    return cleaned