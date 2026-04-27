"""
Generate realistic HR dataset for Company X — ~850 employees.

Fields cover every major HR analytics dimension:
demographics, compensation, performance, attrition, engagement, recruitment.
"""

import random
import csv
from datetime import date, timedelta

random.seed(42)

# ── Company structure ────────────────────────────────────────────────────────

DEPARTMENTS = {
    "Engineering":      {"size": 180, "base_salary": 105000, "salary_spread": 40000},
    "Sales":            {"size": 140, "base_salary":  72000, "salary_spread": 35000},
    "Marketing":        {"size":  80, "base_salary":  78000, "salary_spread": 28000},
    "Human Resources":  {"size":  55, "base_salary":  70000, "salary_spread": 22000},
    "Finance":          {"size":  70, "base_salary":  88000, "salary_spread": 30000},
    "Operations":       {"size": 110, "base_salary":  68000, "salary_spread": 25000},
    "Customer Success": {"size":  90, "base_salary":  65000, "salary_spread": 20000},
    "Legal":            {"size":  35, "base_salary":  95000, "salary_spread": 35000},
    "Product":          {"size":  60, "base_salary":  98000, "salary_spread": 32000},
    "Data & Analytics": {"size":  45, "base_salary": 102000, "salary_spread": 38000},
}

JOB_LEVELS = ["Junior", "Mid-Level", "Senior", "Lead", "Manager", "Director", "VP"]
LEVEL_MULTIPLIER = {
    "Junior": 0.70, "Mid-Level": 0.90, "Senior": 1.10,
    "Lead": 1.25, "Manager": 1.40, "Director": 1.75, "VP": 2.20,
}
LEVEL_WEIGHTS = [18, 28, 24, 12, 10, 6, 2]

LOCATIONS = ["New York", "San Francisco", "Austin", "Chicago", "Boston",
             "Seattle", "Remote", "London", "Toronto"]
LOCATION_WEIGHTS = [22, 18, 12, 10, 8, 8, 12, 5, 5]

EDUCATION = ["High School", "Associate's", "Bachelor's", "Master's", "PhD"]
EDU_WEIGHTS = [5, 8, 48, 32, 7]

RECRUITMENT_SOURCE = ["LinkedIn", "Employee Referral", "Company Website",
                      "Recruiter", "Job Board", "University Recruiting", "Acquisition"]
RECRUIT_WEIGHTS = [28, 22, 15, 18, 8, 6, 3]

TERMINATION_REASONS = [
    "Better opportunity", "Compensation", "Work-life balance",
    "Relocation", "Career change", "Performance", "Layoff",
    "Personal reasons", "Retirement",
]

WORK_MODE = ["On-site", "Hybrid", "Remote"]
WORK_WEIGHTS = [38, 42, 20]

PERFORMANCE_RATINGS = [1, 2, 3, 4, 5]
PERF_WEIGHTS = [4, 10, 38, 33, 15]   # realistic bell curve skewed right

GENDER = ["Male", "Female", "Non-binary"]
GENDER_WEIGHTS = [52, 44, 4]

ETHNICITY = ["White", "Asian", "Hispanic/Latino", "Black/African American",
             "Two or more races", "Prefer not to say"]
ETHNICITY_WEIGHTS = [52, 18, 12, 10, 5, 3]

# ── Helpers ──────────────────────────────────────────────────────────────────

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def weighted_choice(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]

def fmt_date(d) -> str:
    return d.strftime("%Y-%m-%d") if d else ""

# ── Generate employees ───────────────────────────────────────────────────────

TODAY = date(2024, 12, 31)
COMPANY_FOUNDED = date(2010, 1, 1)

rows = []
emp_id = 1000

for dept_name, cfg in DEPARTMENTS.items():
    for _ in range(cfg["size"]):
        emp_id += 1

        # Demographics
        gender     = weighted_choice(GENDER, GENDER_WEIGHTS)
        age        = random.randint(22, 62)
        ethnicity  = weighted_choice(ETHNICITY, ETHNICITY_WEIGHTS)
        education  = weighted_choice(EDUCATION, EDU_WEIGHTS)

        # Career
        level      = weighted_choice(JOB_LEVELS, LEVEL_WEIGHTS)
        location   = weighted_choice(LOCATIONS, LOCATION_WEIGHTS)
        work_mode  = weighted_choice(WORK_MODE, WORK_WEIGHTS)
        source     = weighted_choice(RECRUITMENT_SOURCE, RECRUIT_WEIGHTS)

        # Hire date — longer tenures for senior levels
        max_tenure_yrs = {"Junior": 3, "Mid-Level": 6, "Senior": 10,
                          "Lead": 12, "Manager": 14, "Director": 16, "VP": 18}.get(level, 8)
        earliest_hire = max(COMPANY_FOUNDED, TODAY - timedelta(days=max_tenure_yrs * 365))
        hire_date     = rand_date(earliest_hire, TODAY - timedelta(days=90))
        tenure_years  = round((TODAY - hire_date).days / 365.25, 1)

        # Compensation — level + dept + small random noise + gender pay gap simulation
        base      = cfg["base_salary"] * LEVEL_MULTIPLIER[level]
        noise     = random.gauss(0, cfg["salary_spread"] * 0.15)
        gap_adj   = -2500 if gender == "Female" and random.random() < 0.35 else 0  # realistic gap
        salary    = max(32000, round(base + noise + gap_adj, -2))

        # Performance
        perf_rating   = weighted_choice(PERFORMANCE_RATINGS, PERF_WEIGHTS)
        # Performance correlated with salary growth
        salary_growth = round(random.uniform(0.5, 3.0) + perf_rating * 0.4, 1)  # % YoY raise

        # Engagement & wellbeing
        satisfaction      = round(random.gauss(6.8, 1.8), 1)
        satisfaction      = max(1.0, min(10.0, satisfaction))
        engagement_score  = round(random.gauss(6.5, 1.9), 1)
        engagement_score  = max(1.0, min(10.0, engagement_score))
        # Low performers tend to be less engaged
        if perf_rating <= 2:
            satisfaction    = round(max(1.0, satisfaction - random.uniform(0.5, 2.0)), 1)
            engagement_score = round(max(1.0, engagement_score - random.uniform(0.5, 2.0)), 1)

        # Attrition — probability influenced by satisfaction, tenure, pay
        base_attrition = 0.14
        if satisfaction < 5:    base_attrition += 0.18
        if tenure_years < 1:    base_attrition += 0.12
        if tenure_years > 10:   base_attrition -= 0.06
        if perf_rating == 5:    base_attrition -= 0.05
        if dept_name == "Sales": base_attrition += 0.06
        attrition = random.random() < base_attrition

        if attrition:
            term_date   = rand_date(hire_date + timedelta(days=90), TODAY)
            term_reason = weighted_choice(
                TERMINATION_REASONS,
                [22, 18, 14, 8, 10, 6, 10, 7, 5],
            )
            emp_status  = "Terminated"
        else:
            term_date   = None
            term_reason = ""
            emp_status  = "Active"

        # Promotion
        promoted = tenure_years > 1.5 and perf_rating >= 4 and random.random() < 0.35
        last_promotion = rand_date(hire_date, TODAY - timedelta(days=30)) if promoted else None

        # Time & leave
        overtime_hrs_monthly = max(0, round(random.gauss(4, 6), 1))
        leave_days_taken     = random.randint(0, 25)
        training_hrs         = random.randint(0, 80)

        rows.append({
            "employee_id":            f"EMP{emp_id}",
            "department":             dept_name,
            "job_title":              f"{level} {dept_name.split()[0]} Specialist" if level not in ("Manager","Director","VP") else f"{level}, {dept_name}",
            "job_level":              level,
            "gender":                 gender,
            "age":                    age,
            "ethnicity":              ethnicity,
            "education_level":        education,
            "location":               location,
            "work_mode":              work_mode,
            "hire_date":              fmt_date(hire_date),
            "tenure_years":           tenure_years,
            "employment_status":      emp_status,
            "termination_date":       fmt_date(term_date),
            "termination_reason":     term_reason,
            "salary_usd":             salary,
            "last_raise_pct":         salary_growth,
            "performance_rating":     perf_rating,
            "satisfaction_score":     satisfaction,
            "engagement_score":       engagement_score,
            "training_hours_ytd":     training_hrs,
            "overtime_hrs_monthly":   overtime_hrs_monthly,
            "leave_days_taken":       leave_days_taken,
            "last_promotion_date":    fmt_date(last_promotion),
            "years_since_promotion":  round((TODAY - last_promotion).days / 365.25, 1) if last_promotion else None,
            "recruitment_source":     source,
            "manager_id":             f"EMP{random.randint(1001, emp_id - 1)}" if emp_id > 1001 else "EMP1001",
        })

# ── Introduce realistic missingness ─────────────────────────────────────────

for row in rows:
    if random.random() < 0.04:   row["years_since_promotion"] = None
    if random.random() < 0.02:   row["ethnicity"] = None
    if random.random() < 0.03:   row["last_raise_pct"] = None
    if random.random() < 0.015:  row["satisfaction_score"] = None
    if random.random() < 0.015:  row["engagement_score"] = None

# Shuffle so departments are interleaved
random.shuffle(rows)

# ── Write CSV ────────────────────────────────────────────────────────────────

output_path = "/Users/shushan/Desktop/claude-analytics-dashboard/examples/company_x_employees.csv"
fieldnames  = list(rows[0].keys())

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
active = sum(1 for r in rows if r["employment_status"] == "Active")
attrition_rate = round((total - active) / total * 100, 1)
print(f"Generated {total} employees")
print(f"Active: {active}  |  Terminated: {total - active}  |  Attrition rate: {attrition_rate}%")
print(f"Departments: {len(DEPARTMENTS)}")
print(f"Saved to: {output_path}")
