"""Generate sample_ecommerce.csv — a realistic e-commerce transactions dataset.

Run from the project root:
    python examples/generate_sample_data.py
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 500

REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Beauty"]
CHANNELS = ["Online", "In-Store", "Mobile App"]
PAYMENT_METHODS = ["Credit Card", "PayPal", "Debit Card", "Buy Now Pay Later"]
CUSTOMER_SEGMENTS = ["New", "Returning", "VIP", "At-Risk"]


def main() -> None:
    """Generate and save the sample e-commerce dataset."""
    rng = np.random.default_rng(SEED)
    random.seed(SEED)

    # Date range: one year of transactions
    start_date = date(2023, 1, 1)
    dates = [start_date + timedelta(days=int(d)) for d in rng.integers(0, 365, N_ROWS)]

    # Customer IDs
    customer_ids = [f"CUST-{i:04d}" for i in rng.integers(1, 201, N_ROWS)]

    # Region and category
    regions = [random.choice(REGIONS) for _ in range(N_ROWS)]
    categories = [random.choice(CATEGORIES) for _ in range(N_ROWS)]

    # Revenue: log-normal distribution (typical e-commerce)
    revenue = np.round(rng.lognormal(mean=5.5, sigma=0.8, size=N_ROWS), 2)
    revenue = np.clip(revenue, 9.99, 4999.99)

    # Quantity: mostly 1-3, occasional bulk
    quantity = rng.integers(1, 4, N_ROWS)
    bulk_indices = rng.choice(N_ROWS, size=20, replace=False)
    quantity[bulk_indices] = rng.integers(10, 50, size=20)

    # Discount percentage: 0–40%, occasionally higher
    discount_pct = np.round(rng.beta(2, 8, N_ROWS) * 50, 1)

    # Cost is 40–70% of revenue
    cost_ratio = rng.uniform(0.4, 0.7, N_ROWS)
    cost = np.round(revenue * cost_ratio, 2)

    # Profit = revenue * (1 - discount/100) - cost
    profit = np.round(revenue * (1 - discount_pct / 100) - cost, 2)

    # Channel and payment
    channels = [random.choice(CHANNELS) for _ in range(N_ROWS)]
    payments = [random.choice(PAYMENT_METHODS) for _ in range(N_ROWS)]

    # Customer segment
    segments = [random.choice(CUSTOMER_SEGMENTS) for _ in range(N_ROWS)]

    # Rating: 1–5 stars, with some missing
    ratings = rng.integers(1, 6, N_ROWS).astype(float)
    missing_rating_idx = rng.choice(N_ROWS, size=35, replace=False)
    ratings[missing_rating_idx] = np.nan

    # Days to ship: 1–7 days, some missing
    days_to_ship = rng.integers(1, 8, N_ROWS).astype(float)
    missing_ship_idx = rng.choice(N_ROWS, size=20, replace=False)
    days_to_ship[missing_ship_idx] = np.nan

    # Introduce a few duplicate rows for realism
    df = pd.DataFrame(
        {
            "order_date": dates,
            "customer_id": customer_ids,
            "region": regions,
            "category": categories,
            "channel": channels,
            "payment_method": payments,
            "customer_segment": segments,
            "quantity": quantity,
            "revenue": revenue,
            "discount_pct": discount_pct,
            "cost": cost,
            "profit": profit,
            "rating": ratings,
            "days_to_ship": days_to_ship,
        }
    )

    # Add 8 duplicate rows
    duplicates = df.sample(n=8, random_state=SEED)
    df = pd.concat([df, duplicates], ignore_index=True)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

    output_path = Path(__file__).parent / "sample_ecommerce.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {output_path}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Missing values: {df.isnull().sum().sum()}")
    print(f"  Duplicate rows: {df.duplicated().sum()}")
    print(f"  Date range: {df['order_date'].min()} – {df['order_date'].max()}")
    print(f"  Revenue range: ${df['revenue'].min():.2f} – ${df['revenue'].max():.2f}")


if __name__ == "__main__":
    main()
