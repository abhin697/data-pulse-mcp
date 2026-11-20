import random
from datetime import datetime, timedelta
from pathlib import Path
import duckdb

DB_PATH = Path("data/warehouse.duckdb")


def seed_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = duckdb.connect(str(DB_PATH))

    # 1. Create Dimension & Fact Tables
    conn.execute("""
        CREATE TABLE dim_customers (
            customer_id INTEGER PRIMARY KEY,
            email VARCHAR,
            segment VARCHAR,
            country VARCHAR,
            created_at TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE fact_orders (
            order_id INTEGER,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR,
            order_amount DOUBLE
        );
    """)

    # 2. Populate dim_customers (200 clean records)
    segments = ["Enterprise", "SMB", "Consumer"]
    countries = ["US", "IN", "UK", "DE", "CA"]
    base_date = datetime(2025, 1, 1)

    customers = [
        (
            cid,
            f"user_{cid}@example.com",
            random.choice(segments),
            random.choice(countries),
            base_date + timedelta(days=random.randint(0, 365)),
        )
        for cid in range(1, 201)
    ]
    conn.executemany("INSERT INTO dim_customers VALUES (?, ?, ?, ?, ?)", customers)

    # 3. Populate fact_orders (1,000 normal rows + deliberate anomalies)
    random.seed(42)
    orders = []
    start_order_date = datetime(2026, 1, 1).date()

    for oid in range(1001, 2001):
        day_offset = random.randint(0, 29)
        # Simulate an ingestion drop on day 28
        if day_offset == 28 and random.random() < 0.85:
            day_offset = 27

        order_date = start_order_date + timedelta(days=day_offset)

        # Bug 1: ~12% null customer_id (broken upstream join)
        customer_id = None if random.random() < 0.12 else random.randint(1, 200)

        # Bug 2: ~3% negative order_amount (unfiltered refund bug)
        amount = round(random.uniform(25.0, 450.0), 2)
        if random.random() < 0.03:
            amount = -amount

        status = random.choice(["COMPLETED", "COMPLETED", "SHIPPED", "CANCELLED"])
        orders.append((oid, customer_id, order_date, status, amount))

    # Bug 3: Duplicate primary keys (retry storm without idempotency)
    orders.extend(orders[:15])

    conn.executemany("INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?)", orders)
    conn.close()
    print(f"Seeded {DB_PATH} with {len(customers)} customers and {len(orders)} orders.")


if __name__ == "__main__":
    seed_database()