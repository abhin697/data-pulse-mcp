import json
from pathlib import Path
import duckdb
from fastmcp import FastMCP
from data_pulse_mcp.guardrails import validate_and_cap_sql

mcp = FastMCP("DataPulse Warehouse Assistant")
DB_PATH = str(Path(__file__).resolve().parents[2] / "data" / "warehouse.duckdb")


def get_conn():
    return duckdb.connect(DB_PATH, read_only=True)


# 1. RESOURCE: Expose warehouse catalog automatically
@mcp.resource("catalog://tables")
def list_warehouse_tables() -> str:
    """Returns all tables, columns, and data types in the analytical warehouse."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
        """).fetchall()
    return json.dumps(
        [{"table": r[0], "column": r[1], "type": r[2], "nullable": r[3]} for r in rows],
        indent=2,
    )


# 2. TOOL: Safe, governed SQL execution
@mcp.tool()
def run_analytical_query(sql: str) -> str:
    """Execute a read-only DuckDB SQL query to analyze metrics or investigate anomalies."""
    safe_sql = validate_and_cap_sql(sql, max_rows=100)
    with get_conn() as conn:
        df = conn.execute(safe_sql).fetchdf()
    return df.to_json(orient="records", date_format="iso")


# 3. TOOL: Automated Data Quality Profiler
@mcp.tool()
def profile_table_quality(table_name: str) -> str:
    """Profile row count, null percentages, and distinct counts for every column in a table."""
    if not table_name.isidentifier():
        raise ValueError("Invalid table name.")
    with get_conn() as conn:
        total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        cols = conn.execute(f"DESCRIBE {table_name}").fetchall()
        report = {"table": table_name, "total_rows": total_rows, "columns": []}
        for col_name, col_type, *_ in cols:
            nulls, distincts = conn.execute(
                f"SELECT COUNT(*) - COUNT({col_name}), COUNT(DISTINCT {col_name}) FROM {table_name}"
            ).fetchone()
            report["columns"].append({
                "column": col_name,
                "type": col_type,
                "null_count": nulls,
                "null_pct": round((nulls / total_rows) * 100, 2) if total_rows else 0,
                "distinct_count": distincts,
            })
    return json.dumps(report, indent=2)


# 4. PROMPT: Reusable Data Engineering Audit Workflow
@mcp.prompt()
def audit_pipeline_health(table_name: str) -> str:
    """Standardized prompt template for auditing data freshness, nulls, and anomalies."""
    return (
        f"Perform a comprehensive data quality audit on '{table_name}'. "
        "1. Read the 'catalog://tables' resource to understand the schema. "
        f"2. Call 'profile_table_quality' on '{table_name}'. "
        "3. Run targeted SQL queries via 'run_analytical_query' to check for duplicate primary keys, "
        "negative monetary values, or sudden drops in daily row volume. "
        "4. Summarize findings with severity levels (CRITICAL, WARNING, PASS)."
    )


if __name__ == "__main__":
    mcp.run()  # Defaults to stdio transport