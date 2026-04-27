"""Generate a synthetic employee analytics dataset for demos.

Run:  python examples/generate_showcase.py
Output: examples/showcase_data.csv  (1 000 rows, seed=42)

Deliberate signal: Sales department has ~1.5 pt lower satisfaction and
~10 pp higher attrition than the company average — the kind of finding
a good dashboard should surface automatically.
"""

import random
import math
import csv
import os
from datetime import date, timedelta

SEED = 42
random.seed(SEED)

# ── Domain config ──────────────────────────────────────────────────────────

DEPARTMENTS = {
    "Engineering": 0.22,
    "Sales":       0.20,
    "Marketing":   0.15,
    "Support":     0.18,
    "Finance":     0.13,
    "HR":          0.12,
}

JOB_LEVELS = ["L1", "L2", "L3", "L4", "L5"]
LEVEL_WEIGHTS = [0.28, 0.30, 0.22, 0.13, 0.07]

GENDERS = ["Male", "Female", "Non-binary"]
GENDER_WEIGHTS = [0.48, 0.46, 0.06]

LOCATIONS = ["New York", "San Francisco", "Austin", "Chicago", "Remote"]
LOCATION_WEIGHTS = [0.22, 0.20, 0.18, 0.15, 0.25]

WORK_MODES = ["Remote", "Hybrid", "On-site"]
WORK_MODE_WEIGHTS = [0.40, 0.38, 0.22]

# Base salary range by level (annual, USD)
LEVEL_SALARY = {
    "L1": (45_000, 65_000),
    "L2": (62_000, 85_000),
    "L3": (82_000, 110_000),
    "L4": (108_000, 145_000),
    "L5": (140_000, 180_000),
}

# ── Helpers ────────────────────────────────────────────────────────────────

def weighted_choice(choices, weights):
    r = random.random()
    cumulative = 0.0
    for choice, weight in zip(choices, weights):
        cumulative += weight
        if r < cumulative:
            return choice
    return choices[-1]


def random_date(start_year=2018, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


# ── Row generator ──────────────────────────────────────────────────────────

def generate_row(idx):
    employee_id = f"EMP-{idx:04d}"
    dept = weighted_choice(list(DEPARTMENTS.keys()), list(DEPARTMENTS.values()))
    level = weighted_choice(JOB_LEVELS, LEVEL_WEIGHTS)
    gender = weighted_choice(GENDERS, GENDER_WEIGHTS)
    location = weighted_choice(LOCATIONS, LOCATION_WEIGHTS)
    work_mode = weighted_choice(WORK_MODES, WORK_MODE_WEIGHTS)
    hire_date = random_date()

    # Salary: base range for level + small dept premium for Engineering
    lo, hi = LEVEL_SALARY[level]
    salary = random.randint(lo, hi)
    if dept == "Engineering":
        salary = int(salary * random.uniform(1.05, 1.15))
    salary = clamp(salary, 40_000, 200_000)

    # Training hours: 0–120, ~3% missing
    if random.random() < 0.03:
        training_hours = ""
    else:
        base = random.gauss(45, 22)
        training_hours = round(clamp(base, 0, 120), 1)

    # Performance rating: 1.0–5.0
    perf_mu = {"L1": 3.1, "L2": 3.3, "L3": 3.5, "L4": 3.7, "L5": 3.9}[level]
    perf = round(clamp(random.gauss(perf_mu, 0.6), 1.0, 5.0), 1)

    # Satisfaction: 1–10; Sales deliberately lower (~1.5 pt gap)
    if dept == "Sales":
        sat_mu = 5.2
    else:
        sat_mu = 6.7
    if random.random() < 0.02:  # ~2% missing
        satisfaction = ""
    else:
        satisfaction = round(clamp(random.gauss(sat_mu, 1.4), 1.0, 10.0), 1)

    # Overtime %: 0–45; Sales and Support run hotter
    if dept in ("Sales", "Support"):
        ot_mu, ot_sd = 22, 10
    else:
        ot_mu, ot_sd = 12, 8
    overtime_pct = round(clamp(random.gauss(ot_mu, ot_sd), 0, 45), 1)
    # A handful of outliers (>40%)
    if random.random() < 0.012:
        overtime_pct = round(random.uniform(40, 45), 1)

    # Churn: higher for Sales/L1, lower for L4/L5
    base_churn = 0.15
    if dept == "Sales":
        base_churn += 0.10
    if level == "L1":
        base_churn += 0.05
    if level in ("L4", "L5"):
        base_churn -= 0.06
    if isinstance(satisfaction, float) and satisfaction < 4.0:
        base_churn += 0.08
    is_churned = random.random() < clamp(base_churn, 0.02, 0.45)

    return {
        "employee_id":      employee_id,
        "hire_date":        hire_date.isoformat(),
        "department":       dept,
        "job_level":        level,
        "gender":           gender,
        "location":         location,
        "work_mode":        work_mode,
        "annual_salary":    salary,
        "training_hours_ytd": training_hours,
        "performance_rating": perf,
        "satisfaction_score": satisfaction,
        "overtime_pct":     overtime_pct,
        "is_churned":       int(is_churned),
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    out_path = os.path.join(os.path.dirname(__file__), "showcase_data.csv")
    rows = [generate_row(i + 1) for i in range(1000)]

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    churned = sum(r["is_churned"] for r in rows)
    missing_training = sum(1 for r in rows if r["training_hours_ytd"] == "")
    missing_sat = sum(1 for r in rows if r["satisfaction_score"] == "")

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"  Churn rate:              {churned/len(rows):.1%}")
    print(f"  Missing training_hours:  {missing_training} rows ({missing_training/len(rows):.1%})")
    print(f"  Missing satisfaction:    {missing_sat} rows ({missing_sat/len(rows):.1%})")


if __name__ == "__main__":
    main()
