# DataPulse MCP — Data Quality & Warehouse Assistant

An open-source **Model Context Protocol (MCP)** server built with **FastMCP** and **DuckDB** that enables AI assistants (Claude Desktop, Cursor, VS Code) to safely inspect warehouse schemas, profile data quality, and run governed analytical queries.

## Architecture

```mermaid
flowchart LR
    A[MCP Host<br/>Claude Desktop / Cursor] <-->|JSON-RPC 2.0 over stdio| B[DataPulse FastMCP Server]
    B --> C{SQL Guardrails<br/>Read-Only & LIMIT Cap}
    C -->|Validated SELECT/WITH| D[(DuckDB Warehouse)]
    B -.->|Resource: catalog://tables| A
    B -.->|Prompt: audit_pipeline_health| A
```

## Key Features

* **Schema Discovery (`catalog://tables` Resource):** Exposes live `information_schema` metadata so LLMs write accurate SQL without hallucinating column names.
* **Governed SQL Execution (`run_analytical_query` Tool):** Enforces strict read-only validation (blocking `DROP`, `DELETE`, `UPDATE`, `INSERT`, `COPY`) and automatically injects `LIMIT 100` to protect LLM context windows.
* **Automated Data Profiling (`profile_table_quality` Tool):** Computes row counts, null percentages, and cardinality across every column in a table.
* **Reusable Audit Workflow (`audit_pipeline_health` Prompt):** Standardized root-cause analysis template that checks for null spikes, duplicate primary keys, negative values, and ingestion drops.

## Quickstart

### 1. Clone & Seed the Demo Warehouse
```bash
git clone [https://github.com/](https://github.com/)<your-username>/data-pulse-mcp.git
cd data-pulse-mcp
python -m venv .venv && source .venv/bin/activate
pip install fastmcp duckdb pandas pytest

# Generate local DuckDB warehouse with seeded data quality anomalies
python data/seed_warehouse.py
```

### 2. Run Unit Tests
```bash
PYTHONPATH=src:. pytest -v
```

### 3. Connect to Claude Desktop or Cursor
Add the following entry to your `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "data-pulse": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "--with",
        "duckdb",
        "--with",
        "pandas",
        "fastmcp",
        "run",
        "src/data_pulse_mcp/server.py"
      ]
    }
  }
}
```

## Example Prompts to Try
* *"Run the `audit_pipeline_health` workflow on `fact_orders` and rank any anomalies by severity."*
* *"Which customer segments have the highest revenue, excluding negative refund rows?"*
* *"Check whether there are orphaned `customer_id` records in `fact_orders` missing from `dim_customers`."*