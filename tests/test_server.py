import json
import pytest
from data_pulse_mcp.guardrails import validate_and_cap_sql
from data_pulse_mcp.server import (
    list_warehouse_tables,
    profile_table_quality,
    run_analytical_query,
)
from data.seed_warehouse import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_warehouse():
    seed_database()


# --- Guardrail Unit Tests ---

def test_appends_limit_when_missing():
    sql = "SELECT * FROM fact_orders"
    secured = validate_and_cap_sql(sql, max_rows=50)
    assert secured == "SELECT * FROM fact_orders LIMIT 50"


def test_preserves_existing_limit():
    sql = "SELECT * FROM fact_orders LIMIT 10"
    secured = validate_and_cap_sql(sql, max_rows=50)
    assert secured == "SELECT * FROM fact_orders LIMIT 10"


@pytest.mark.parametrize(
    "malicious_sql",
    [
        "DROP TABLE fact_orders",
        "DELETE FROM fact_orders WHERE order_id = 1001",
        "UPDATE fact_orders SET order_amount = 0",
        "INSERT INTO dim_customers VALUES (999, 'a@b.com', 'SMB', 'US', NOW())",
        "SELECT * FROM fact_orders; DROP TABLE dim_customers;",
    ],
)
def test_blocks_mutating_queries(malicious_sql):
    with pytest.raises(ValueError, match="Security Policy"):
        validate_and_cap_sql(malicious_sql)


# --- MCP Resource & Tool Tests ---

def test_catalog_resource_returns_schema():
    catalog = json.loads(list_warehouse_tables())
    tables = {item["table"] for item in catalog}
    assert "fact_orders" in tables
    assert "dim_customers" in tables


def test_profile_tool_detects_seeded_nulls():
    report = json.loads(profile_table_quality("fact_orders"))
    assert report["total_rows"] == 1015
    customer_col = next(c for c in report["columns"] if c["column"] == "customer_id")
    assert customer_col["null_count"] > 0
    assert customer_col["null_pct"] > 5.0


def test_analytical_query_tool_executes_select():
    raw = run_analytical_query(
        "SELECT COUNT(*) AS neg_count FROM fact_orders WHERE order_amount < 0"
    )
    rows = json.loads(raw)
    assert rows[0]["neg_count"] > 0