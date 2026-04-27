"""Generate a realistic corporate finance / budget dataset for demo purposes."""

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Operations", "HR", "Finance", "Product", "Legal"]
CATEGORIES  = ["Salaries", "Software & Tools", "Travel & Entertainment", "Marketing Spend",
               "Office & Facilities", "Professional Services", "Training & Development", "Equipment"]
VENDORS     = ["Salesforce", "AWS", "Google Workspace", "Zoom", "HubSpot", "Stripe", "Slack",
               "Adobe", "Workday", "Netsuite", "Greenhouse", "Jira/Confluence", "DocuSign", "Okta"]
QUARTERS    = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]
MONTHS      = pd.date_range("2024-01-01", "2024-12-31", freq="MS")

rows = []
for _ in range(520):
    dept       = rng.choice(DEPARTMENTS)
    category   = rng.choice(CATEGORIES)
    vendor     = rng.choice(VENDORS) if rng.random() > 0.3 else None
    month      = pd.Timestamp(rng.choice(MONTHS))
    quarter    = f"Q{((month.month - 1) // 3) + 1} {month.year}"

    # Budget: higher for Salaries, lower for Training
    base = {"Salaries": 120_000, "Software & Tools": 15_000, "Travel & Entertainment": 8_000,
            "Marketing Spend": 25_000, "Office & Facilities": 12_000,
            "Professional Services": 20_000, "Training & Development": 5_000, "Equipment": 18_000}
    budget = base[category] * rng.uniform(0.7, 1.3)

    # Actual spend — realistic: departments tend to overspend by 5-8%
    dept_bias = {"Engineering": 0.12, "Sales": 0.18, "Marketing": 0.09,
                 "Operations": -0.04, "HR": 0.03, "Finance": -0.06,
                 "Product": 0.14, "Legal": 0.07}
    bias = dept_bias.get(dept, 0.05)
    variance_pct = rng.normal(bias, 0.10)
    actual = budget * (1 + variance_pct)

    # Inject outliers (~4% of rows)
    if rng.random() < 0.04:
        actual *= rng.uniform(1.8, 2.8)

    # Missing values (~3%)
    if rng.random() < 0.03:
        vendor = None
    if rng.random() < 0.03:
        actual = None

    rows.append({
        "transaction_date": month.strftime("%Y-%m-%d"),
        "quarter":          quarter,
        "department":       dept,
        "cost_category":    category,
        "vendor":           vendor,
        "budget_usd":       round(budget, 2) if budget else None,
        "actual_spend_usd": round(actual, 2) if actual else None,
        "variance_pct":     round((actual - budget) / budget * 100, 1) if actual else None,
        "approved_by":      rng.choice(["CFO", "VP Finance", "Department Head", "CEO"]),
        "payment_method":   rng.choice(["Corporate Card", "Wire Transfer", "Invoice", "PO"]),
    })

df = pd.DataFrame(rows)
out = "examples/corporate_finance_2024.csv"
df.to_csv(out, index=False)
print(f"Saved {len(df)} rows → {out}")
print(df.dtypes)
print(df.head(3))
