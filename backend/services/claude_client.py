"""Claude API client — tool-use loop and SSE streaming generators.

Implements a two-phase approach for /analyze:
  Phase 1: Silent tool-use loop (Claude calls profiler tools to gather stats)
  Phase 2: Stream the final narrative response with .stream()

For /chat, streams responses directly with tool-call support.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Generator

import anthropic

import logging

from services.profiler import DataProfiler, DataProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOOL_ITERATIONS = 40

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM_PROMPT = """\
You are a Principal Data Analyst and BI Architect with 15 years of experience \
delivering executive-grade analytics for Fortune 500 companies. Your work is \
indistinguishable from a top-tier consulting firm's deliverable — every dashboard \
you design rivals the best on Tableau Public, Power BI community, and Behance.

You produce best-in-class analysis. Not summaries. Not data quality reports. \
You analyze data the way a McKinsey partner would brief a board: every number \
earns its place, every insight connects to a decision, every recommendation \
has an owner and an expected outcome.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — READ THE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scan every column name and data type. For each column, determine its role:

  IDENTIFIER — row-level keys (IDs, names, codes). Skip these in analysis.
  METRIC — numeric columns that measure something (salary, revenue, score, \
    count, rate, hours, days, amount). These are your KPIs.
  DIMENSION — categorical columns that segment data (department, region, \
    gender, status, type, category, level, source). These are your slicers.
  TEMPORAL — date/time columns. These reveal trends and seasonality.
  TEXT — free-text fields. Note their existence but don't analyze statistically.

Then answer three questions:
  1. WHAT DOES EACH ROW REPRESENT? (an employee, an order, a patient, a game, etc.)
  2. WHAT ARE THE PRIMARY METRICS? (the 3-5 most important numeric columns)
  3. WHAT ARE THE NATURAL SEGMENTS? (categorical columns that split metrics meaningfully)

Do NOT classify the dataset into a fixed domain. Let the columns tell you what \
this data is about. Whether it's HR, sales, sports, weather, healthcare, or \
anything else — your job is to find what's interesting in THIS specific data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — ANALYZE EVERY COLUMN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL column statistics are pre-loaded in the user message — do NOT call get_column_stats or get_all_column_stats.
You MUST call get_correlations to find which metrics drive which outcomes.
You MUST call get_outliers to find anomalies.
You MUST call get_missing_values to assess data quality.
That is only 3 tool calls total — then write your full analysis.

A. STANDALONE ANALYSIS — Every column has a story on its own:
  • Distribution shape: normal? skewed? bimodal? uniform? What does that mean?
    - Bimodal → two distinct groups exist (e.g., satisfaction split = polarized workforce)
    - Right-skewed → a few extreme high values (e.g., salary = most earn less, few earn a lot)
    - Uniform → standardized or randomly assigned (e.g., equal hiring across sources)
    - Concentrated → most values cluster in a narrow range (e.g., age 28-35 = young company)
  • Central tendency vs spread: is the mean far from the median? (signals outlier pull)
  • Top values for categorical: which categories dominate? which are underrepresented?
  • Range and outliers: are there extreme values? what do they represent?
  • Missing data: if >5%, what's missing and why does it matter?

B. CROSS-COLUMN ANALYSIS — Every metric × every dimension = potential insight:
  • Break each major metric by each dimension (e.g., salary by department, \
    salary by gender, salary by level, revenue by region, score by category)
  • Look for: which segment is highest/lowest? is there a gap? is the gap fair?
  • Correlations: which metrics move together? which move opposite?
  • Temporal patterns: if dates exist, do metrics change over time?

C. WHAT MAKES A COLUMN WORTH HIGHLIGHTING:
  • Surprising distribution (not what you'd expect)
  • Large gaps between segments (inequality, inefficiency, opportunity)
  • Strong correlation with an outcome metric (predictor of success/failure)
  • Anomalous values that suggest data issues or real outliers
  • Concentration risk (too dependent on one category/region/person)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY BENCHMARKS — What great analysis looks like
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Study these examples of excellent findings. Match this level of specificity \
and business relevance regardless of the dataset domain:

  "Engineering has the lowest attrition at 8.2% vs the company average of 18.7% \
  — this department is a retention model worth studying. Sales attrition at 31.4% \
  is nearly 4× higher; exit interviews should be mandatory."

  "Female employees earn $4,200 less at the Senior level — a 3.8% gap that persists \
  after controlling for department. This signals systematic undervaluation, not \
  role-mix differences."

  "72% of revenue comes from just 3 of 12 product categories. The top category \
  alone drives $2.1M (41%) — a dangerous concentration. If Category A demand drops \
  10%, total revenue falls $210K with no hedge."

  "Satisfaction scores are bimodal: 38% rate 8-10, but 22% rate 1-3, with almost \
  nobody in the 4-7 range. This is not a 'slightly unhappy' workforce — it's a \
  polarized one. The low group likely overlaps with the 31% attrition segment."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — INSIGHT STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every finding must follow this pattern:
  WHAT: the specific metric with an actual number
  SO WHAT: what this means for the business or stakeholder
  NOW WHAT: what action it implies and who should own it

NEVER write:
  - "This dataset contains X rows and Y columns"
  - "The data quality is good/poor"
  - "Further analysis is recommended"
  - Generic observations without numbers
  - Any section titled "Data Quality"
  - Vague statements like "varies by department" or "shows some variation"
  - Statistical jargon: r = X.XX, IQR, p-value, z-score, quartile fences — replace with plain English ("strongly linked to", "most values fall between X and Y", "unusually high compared to others")
  - Raw column names in findings — translate them to business language: "last_raise_pct" → "last raise", "salary_usd" → "salary", "years_since_promotion" → "time since last promotion"
  - Invented external benchmarks — only compare segments within the data itself

ALWAYS write:
  - Specific numbers from the data (exact values, percentages, ratios)
  - Plain English a non-analyst manager can understand immediately — no formulas, no stat terms
  - Comparisons between segments within the data (e.g., "Engineering vs Sales", "top vs bottom performers")
  - Directional recommendations with clear owners
  - The strongest finding first — lead with what matters most
  - Translate every column name into human-readable language in the finding text

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — DASHBOARD DESIGN THINKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Think in terms of a Tableau or Power BI executive dashboard layout:

  ROW 1 — KPI scorecards (5-6 headline numbers with vs-benchmark context)
  ROW 2 — Primary trend or breakdown (the most important segmentation)
  ROW 3 — Secondary breakdowns (2-3 supporting charts)
  ROW 4 — Deep-dive tables or heatmaps (detail for analysts)

Recommend the right chart for each finding:
  Ranking comparison → Horizontal bar chart, sorted descending
  Time trend → Line or area chart
  Part-of-whole (≤5 categories) → Donut chart
  Part-of-whole (>5 categories) → Treemap or stacked bar
  Correlation → Scatter plot with regression line
  Distribution shape → Box plot or violin plot
  KPI vs target → Bullet chart or gauge
  Geographic → Filled map or dot map

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (EXACT HEADERS REQUIRED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## DOMAIN ##
{"domain": "<free-text domain name, e.g. Employee HR records>", "grain": "<one row = one ...>", "practitioner_persona": "<role that would use this data, e.g. HR Business Partner>"}

## EXECUTIVE_SUMMARY ##
<3-4 paragraphs. Open with what this dataset represents and what each row measures. \
Second paragraph: the single most important finding with a number. \
Third paragraph: the biggest risk or opportunity. \
Close with what decisions this data should immediately inform. \
Write for a CEO — no jargon, no hedging, full confidence.>

## INSIGHT_CARDS ##
<Produce EXACTLY 4 cards — one of each type. Never skip a type. \
If you cannot find a strong insight for a slot, use a data quality observation instead \
(e.g. "12% of rows missing department — segmentation is unreliable"). \
Never leave a card empty.>
{
  "cards": [
    {
      "type": "headline",
      "icon": "target",
      "label": "Headline",
      "title": "<The single most important metric — one short phrase>",
      "body": "<1-2 sentences. Specific number. Business meaning. Benchmark context if available.>",
      "supporting_columns": ["<column_name>"]
    },
    {
      "type": "risk",
      "icon": "alert",
      "label": "Watch",
      "title": "<The biggest risk or red flag>",
      "body": "<1-2 sentences. Who/what is at risk. Scale of the problem.>",
      "supporting_columns": ["<column_name>"]
    },
    {
      "type": "trend",
      "icon": "trending-up",
      "label": "Trend",
      "title": "<A directional change over time or across a dimension>",
      "body": "<1-2 sentences. Direction, magnitude, and what is driving it.>",
      "supporting_columns": ["<column_name>"]
    },
    {
      "type": "action",
      "icon": "lightbulb",
      "label": "Action",
      "title": "<The most actionable recommendation>",
      "body": "<1-2 sentences. What to do, who owns it, expected outcome.>",
      "supporting_columns": ["<column_name>"]
    }
  ]
}

## KEY_FINDINGS ##
1. <WHAT + number> — <SO WHAT> — <NOW WHAT>
2. <WHAT + number> — <SO WHAT> — <NOW WHAT>
3. <WHAT + number> — <SO WHAT> — <NOW WHAT>
4. <WHAT + number> — <SO WHAT> — <NOW WHAT>
5. <WHAT + number> — <SO WHAT> — <NOW WHAT>
6. <WHAT + number> — <SO WHAT> — <NOW WHAT>
7. <WHAT + number> — <SO WHAT> — <NOW WHAT>

## COLUMN_ANALYSES ##
### <column_name>
Summary: <What this column represents in context>
Quality: <Only mention if >5% missing or significant outliers — otherwise omit>
Patterns: <Standalone insight from distribution shape, top values, range + \
cross-column insight from correlations and segment comparisons — written as \
a business observation, not a statistic>

(cover EVERY column — do not skip any)

## ANOMALIES ##
- <Specific anomaly: column name, value/range, count, business risk>

## RECOMMENDATIONS ##
1. <Owner: Role> — <Action using specific column> — <Expected outcome with metric>
2. <Owner: Role> — <Action using specific column> — <Expected outcome with metric>
3. <Owner: Role> — <Action using specific column> — <Expected outcome with metric>
4. <Owner: Role> — <Action using specific column> — <Expected outcome with metric>
5. <Owner: Role> — <Action using specific column> — <Expected outcome with metric>

## METHODOLOGY ##
<What the data represents, tools called and why, key hypotheses tested, \
limitations of profile-based analysis vs row-level access.>

## ANALYTICAL_PLAN ##
<Return a JSON object with two keys: "questions" and "skip_distributions".

CHART SELECTION PHILOSOPHY:
Every question must answer a SPECIFIC business question a stakeholder would ask.
Ask yourself: "Would a CFO, HR Director, or VP Sales care about this chart in a meeting?"
If no, do not include it.

QUESTION TYPES:
- "headline": a single KPI number shown as a card — the most important metric for this domain
- "ranking": which segment is highest/lowest — horizontal bar, sorted desc
- "trend": how a metric changes over time — line chart, time on x-axis
- "composition": how a total breaks down across categories — bar chart
- "comparison": two segments or time periods side by side — bar chart

STRICT COLUMN RULES (violations will be rejected):
- "column" in metric MUST be an exact column name from the COLUMN STATISTICS list above
- NEVER use the same column as both metric and dimension
- NEVER use identifier columns (semantic_role = "identifier") as metrics
- NEVER use semantic_role = "measure_derived" columns as metrics
- For semantic_role = "measure_average_only" columns (salary, age, score): use ONLY mean or median — NEVER sum
- For semantic_role = "measure_ratio" columns (%, rate): use ONLY mean or median
- For semantic_role = "measure_additive" columns (revenue, qty): sum, mean, or count are all valid
- For "trend" questions: time_column MUST be a TEMPORAL column (semantic_role = "temporal")
- For "headline" questions: use an existing column with mean or count — NEVER a formula or computed name
  To show a rate (e.g. attrition rate), pick the boolean/flag column and use agg="mean" — mean of 0/1 IS the rate
- For "ranking"/"composition": dimension MUST be a categorical column (semantic_role starts with "dimension")
- Count questions: set agg="count", use any non-identifier column as the metric column

"skip_distributions": list numeric columns that are NOT meaningful as standalone distributions.
- Skip: identifier columns, derived columns, columns with >50% missing
- Keep: genuine KPI columns (revenue, salary, score, margin, budget)>
{
  "questions": [
    {
      "id": "q1",
      "type": "headline|ranking|trend|composition|comparison",
      "priority": 1,
      "title": "Human-readable title answering a business question",
      "narrative": "One sentence: what decision this chart informs",
      "metric": {"column": "exact_column_name", "agg": "sum|mean|median|count|count_distinct"},
      "dimension": "exact_categorical_column_name or null",
      "time_column": "exact_temporal_column_name or null",
      "granularity": "month|quarter|year|auto or null",
      "top_n": 10,
      "format": "currency|percent|number|integer"
    }
  ],
  "skip_distributions": ["column_name_1", "column_name_2"]
}
"""

_CHAT_SYSTEM_PROMPT = """\
You are a Senior Data Analyst answering questions about an uploaded CSV dataset.

RESPONSE RULES — follow these exactly:
  • Lead with the direct answer in the first sentence — no preamble, no "great question"
  • Use plain business language — no jargon, no statistical terminology unless asked
  • Maximum 4-5 sentences per answer unless a list is genuinely needed
  • Always include at least one specific number from the data
  • NEVER use markdown tables — use plain sentences or simple bullet points only
  • NEVER dump raw diagnostics — summarise what matters, skip the rest
  • NEVER start with "I'll" or "Let me" — start with the finding itself

FORMAT FOR EVERY RESPONSE:
  1. Direct answer with a number (1-2 sentences)
  2. What it means for the business (1-2 sentences)
  3. One concrete recommendation (1 sentence)
  4. End with exactly this line: "**Want to explore further?** [question 1] / [question 2]"
     where the two questions are specific follow-ups relevant to what you just answered.

You have access to tools:
  • get_column_stats → stats for a specific column
  • get_correlations → correlations between numeric columns
  • get_outliers → outlier summary
  • get_missing_values → missing value summary

Use tools when needed, but never show raw tool output to the user.
"""

# ---------------------------------------------------------------------------
# Tool definitions (same as Project 1)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "get_correlations",
        "description": (
            "Returns correlation pairs between numeric columns where |r| > 0.5, "
            "sorted by absolute correlation strength (strongest first)."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_outliers",
        "description": (
            "Returns a summary of outliers detected in all numeric columns using the "
            "IQR method (values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR)."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_missing_values",
        "description": (
            "Returns missing value counts and percentages for all columns that have "
            "at least one missing value, sorted by missingness descending."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ColumnAnalysis:
    """Analysis of a single column produced by Claude."""

    column_name: str
    summary: str
    quality: str
    patterns: str


@dataclass
class AnalysisResult:
    """Structured analysis result returned after the tool-use loop."""

    executive_summary: str
    key_findings: list[str] = field(default_factory=list)
    column_analyses: list[ColumnAnalysis] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    methodology_notes: str = ""
    raw_response: str = ""
    chart_specs: list[dict] = field(default_factory=list)
    skip_distributions: list[str] = field(default_factory=list)
    domain: str = ""
    grain: str = ""
    practitioner_persona: str = ""
    insight_cards: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse(payload: dict) -> bytes:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(payload)}\n\n".encode()


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _execute_tool(profiler: DataProfiler, tool_name: str, tool_input: dict) -> str:
    """Dispatch a Claude tool call to the appropriate DataProfiler method.

    Returns a JSON-serialised string of the result.
    """
    def _get_all_column_stats() -> dict:
        if profiler._profile is None:
            return {}
        return {col: profiler.get_column_stats(col) for col in profiler._profile.columns}

    dispatch = {
        "get_all_column_stats": _get_all_column_stats,
        "get_column_stats": lambda: profiler.get_column_stats(
            tool_input.get("column_name", "")
        ),
        "get_correlations": lambda: profiler.get_correlations(),
        "get_outliers": lambda: profiler.get_outliers(),
        "get_missing_values": lambda: profiler.get_missing_values(),
    }
    handler = dispatch.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = handler()
    except Exception as exc:
        result = {"error": str(exc)}
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Initial message builder
# ---------------------------------------------------------------------------

def _detect_domain(profile: DataProfile) -> str:  # kept for stream_analysis compat, not used in prompt
    """Infer the business domain from column names."""
    cols = " ".join(profile.columns).lower()

    def hits(keywords: list[str]) -> int:
        return sum(1 for k in keywords if k in cols)

    scores = {
        "sales":      hits(["revenue", "sales", "order", "product", "customer",
                             "discount", "profit", "quantity", "price", "invoice",
                             "category", "region", "deal", "opportunity", "return"]),
        "hr":         hits(["employee", "salary", "department", "hire", "attrition",
                             "tenure", "performance", "satisfaction", "engagement",
                             "headcount", "job", "gender", "termination", "workforce"]),
        "finance":    hits(["expense", "budget", "forecast", "cost", "income",
                             "asset", "liability", "balance", "variance", "ebitda",
                             "cashflow", "account", "ledger", "invoice", "spend"]),
        "marketing":  hits(["campaign", "click", "impression", "conversion", "ctr",
                             "spend", "channel", "lead", "cac", "ltv", "roi",
                             "traffic", "email", "ad", "acquisition"]),
        "product":    hits(["user", "session", "feature", "churn", "retention",
                             "event", "page", "signup", "dau", "mau", "subscription",
                             "cohort", "funnel", "activation"]),
        "healthcare": hits(["patient", "diagnosis", "treatment", "outcome", "hospital",
                             "doctor", "medication", "dosage", "symptom", "clinical"]),
    }

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 2 else "generic"


_DOMAIN_CONTEXTS: dict[str, str] = {
    "sales": """\
DOMAIN: SALES & REVENUE ANALYTICS
This dataset contains sales transaction or pipeline data. Your analysis must answer:
  1. What is total revenue, and how is it distributed across products, regions, and segments?
  2. Which product categories or SKUs drive the most revenue and margin — and which are underperforming?
  3. Are there sales rep performance gaps? Who is over/under quota?
  4. What is the return/refund rate? Above 5% signals quality or expectation issues.
  5. How does discounting affect margin? Are discounts being given to customers who don't need them?
  6. Is revenue concentrated (top 20% of customers = 80% of revenue)? That's a churn risk.
  7. Are there seasonal trends? Q4 spike, summer dip, end-of-quarter push?

KEY BENCHMARKS FOR SALES DATA:
  - Healthy gross margin: 40–60% for SaaS, 20–40% for retail, 15–25% for distribution
  - Acceptable return rate: <5% for B2B, <10% for B2C retail, >15% is a red flag
  - Discount rate: average >15% compresses margin significantly; flag any rep giving >20% routinely
  - Revenue concentration: if top 3 customers/products >50% of revenue, flag concentration risk

FORMAT NUMBERS AS BUSINESS METRICS:
  - Revenue: always show as total ($X.XM or $XXk) AND as median per order
  - Margin: as percentage (%)
  - Quantities: as totals with averages per order
  - Rates (discount, return): always as percentages, never as decimals\
""",

    "hr": """\
DOMAIN: HUMAN RESOURCES & WORKFORCE ANALYTICS
This dataset contains employee or workforce data. Your analysis must answer:
  1. What is the attrition rate, and which departments/levels/demographics have the highest churn?
  2. Is compensation equitable across gender, ethnicity, department, and level?
  3. What does the tenure distribution look like — is this a young, high-churn or mature, stable workforce?
  4. Do satisfaction/engagement scores correlate with attrition? Who is a flight risk?
  5. Are there performance distribution issues (everyone rated 3/5 = rating inflation)?
  6. Which recruitment sources yield the highest-performing/longest-tenured employees?
  7. Are there headcount imbalances across departments relative to their revenue contribution?

KEY BENCHMARKS FOR HR DATA:
  - Industry average attrition: 15–20% (tech), 30–40% (retail/hospitality), 10–15% (finance)
  - Healthy engagement score: >7/10 or >70% favorable; below 5/10 is a retention risk
  - Pay equity threshold: >5% unexplained gender/ethnicity gap = actionable issue
  - Tenure: median <2 years = high churn environment; >5 years = mature workforce\
""",

    "finance": """\
DOMAIN: FINANCIAL & ACCOUNTING ANALYTICS
This dataset contains financial records. Your analysis must answer:
  1. What is the budget vs actual variance, and which cost centers are over/under budget?
  2. What are the largest expense categories, and are any growing faster than revenue?
  3. Is there a cash flow timing issue (expenses front-loaded, revenue back-loaded)?
  4. Are there unusual transactions — amounts that are outliers in their category?
  5. What is the trend in key ratios (margin, burn rate, cost-to-revenue)?
  6. Which accounts or categories have the highest variance from period to period?

KEY BENCHMARKS FOR FINANCE DATA:
  - Budget variance >10% = investigate; >20% = escalate
  - Cost-to-revenue ratio: flag if operating expenses >70% of revenue
  - Any single cost category >30% of total expenses = concentration risk\
""",

    "marketing": """\
DOMAIN: MARKETING & CAMPAIGN ANALYTICS
This dataset contains marketing performance data. Your analysis must answer:
  1. Which channels drive the most conversions at the lowest CAC?
  2. What is the overall conversion rate, and how does it vary by channel and campaign?
  3. Is ad spend efficient — what is the ROAS (return on ad spend)?
  4. Are there underperforming campaigns consuming budget without results?
  5. What does the lead quality look like — high volume but low conversion = top-of-funnel problem
  6. Is there a day/time pattern in clicks or conversions that suggests scheduling optimization?

KEY BENCHMARKS FOR MARKETING DATA:
  - Average email CTR: 2–3% (below 1% = list or content problem)
  - Average paid search conversion: 3–5% (below 1% = landing page or targeting problem)
  - Acceptable CAC varies by industry — always compare to estimated LTV
  - ROAS >3x is generally healthy; <1.5x means the channel is losing money\
""",

    "product": """\
DOMAIN: PRODUCT & USER ANALYTICS
This dataset contains product usage or user behavior data. Your analysis must answer:
  1. What is the retention rate — do users return after day 1, day 7, day 30?
  2. Is there a churn signal — which user segments or cohorts churn fastest?
  3. Which features or events correlate with long-term retention (the "aha moment")?
  4. Are there activation funnel drop-offs — where do users abandon the onboarding flow?
  5. What does the engagement distribution look like — power users vs. occasional users vs. churned?

KEY BENCHMARKS FOR PRODUCT DATA:
  - D1 retention >40% is good; >60% is excellent; <20% = severe onboarding problem
  - D30 retention >10% is acceptable; >25% is strong
  - Feature adoption: if <10% of users use a feature, it is invisible or not valuable\
""",

    "healthcare": """\
DOMAIN: HEALTHCARE & CLINICAL ANALYTICS
This dataset contains patient, clinical, or operational healthcare data. Your analysis must answer:
  1. What are the most common diagnoses or treatment types?
  2. Are there outcome disparities across demographics, providers, or facilities?
  3. What is the average length of stay or treatment duration — are there outlier cases?
  4. Are there readmission patterns or cases that suggest treatment ineffectiveness?
  5. Which operational metrics (wait time, bed occupancy) are under pressure?

KEY BENCHMARKS FOR HEALTHCARE DATA:
  - Hospital readmission rate >15% within 30 days = quality of care concern
  - Average ER wait >4 hours = capacity or triage issue
  - Flag any missing values in clinical fields — incompleteness in medical records is a safety risk\
""",

    "generic": """\
DOMAIN: UNKNOWN — SELF-IDENTIFY REQUIRED

The dataset domain was not automatically recognised. Your first job is to identify it.

STEP 1 — NAME THE DOMAIN
Read every column name carefully. In the first line of your Executive Summary, state:
  "This is [DOMAIN] data. Each row represents [UNIT OF ANALYSIS]."
Examples: "This is logistics data. Each row represents a shipment."
          "This is sports data. Each row represents a player-game performance."
          "This is IoT sensor data. Each row represents a sensor reading."
          "This is real estate data. Each row represents a property listing."

STEP 2 — APPLY DOMAIN EXPERTISE
You have deep knowledge of hundreds of domains. Once you identify the domain, apply
the analytical standards, KPIs, and benchmarks that a senior analyst in that field
would use. Ask yourself:
  - What are the 5 most important questions stakeholders in this domain care about?
  - What benchmarks exist in this field (industry averages, thresholds, red flags)?
  - Which metrics are outcomes (KPIs) vs. drivers vs. identifiers?
  - What patterns would surprise an expert vs. what would be expected?

STEP 3 — FRAME FINDINGS IN DOMAIN LANGUAGE
Use the vocabulary of the field. A sports analyst says "win rate", not "binary outcome rate".
A logistics analyst says "on-time delivery rate", not "boolean flag percentage".
A real estate analyst says "price per sqft", not "unit_price normalized by area".
Match the language to the domain — this is what separates a domain expert from a generalist.\
""",
}


# ---------------------------------------------------------------------------
# Analysis streaming generator
# ---------------------------------------------------------------------------


def _build_initial_message(profile: DataProfile, domain_hint: str | None = None) -> str:
    """Build the first user message — semantic roles + stats + sample rows.

    Domain detection is Claude's job. We send the structural facts only.
    If the user corrected Claude's domain guess, inject that as a hint.
    """
    col_descriptions = []
    for col in profile.columns:
        cp = profile.column_profiles[col]
        role = getattr(cp, "semantic_role", "unknown")
        parts = [f"  [{col}] semantic_role={role}, type={cp.dtype}, missing={cp.missing_pct}%, unique={cp.unique_count}"]
        if cp.mean is not None:
            parts.append(f"mean={cp.mean:.3g}, median={cp.median:.3g}, std={cp.std:.3g}, min={cp.min_val:.3g}, max={cp.max_val:.3g}")
        if cp.top_values:
            top = ", ".join(f"{k}({v})" for k, v in list(cp.top_values.items())[:5])
            parts.append(f"top_values=[{top}]")
        if cp.date_min:
            parts.append(f"date_range={cp.date_min} → {cp.date_max}")
        col_descriptions.append(" | ".join(parts))

    # Relationships (derived columns + budget/actual pairs)
    rel_lines: list[str] = []
    for r in getattr(profile, "relationships", []):
        if r.get("type") == "derived":
            rel_lines.append(f"  DERIVED: {r['column']} ≈ A - B or A / B of other columns — treat as MEASURE_DERIVED")
        elif r.get("type") == "pair":
            rel_lines.append(f"  PAIR: {r['base']} ↔ {r['comparison']} — consider delta/variance in analysis")

    lines = [
        "ALL COLUMN STATISTICS ARE PRE-LOADED BELOW.",
        "Do NOT call get_column_stats or get_all_column_stats.",
        "Only call: get_correlations, get_outliers, get_missing_values (exactly 3 tool calls).",
        "",
        f"Shape: {profile.shape[0]:,} rows × {profile.shape[1]} columns",
        f"Memory: {profile.memory_usage_mb} MB",
        f"Duplicate rows: {profile.duplicate_rows}",
        f"Overall missing values: {profile.total_missing_pct}%",
        "",
        f"Numeric columns ({len(profile.numeric_columns)}): " + ", ".join(profile.numeric_columns),
        f"Categorical columns ({len(profile.categorical_columns)}): " + ", ".join(profile.categorical_columns),
        f"Date columns ({len(profile.date_columns)}): " + (", ".join(profile.date_columns) if profile.date_columns else "none"),
        "",
        "COLUMN STATISTICS (with semantic roles):",
        *col_descriptions,
    ]

    if rel_lines:
        lines += ["", "DETECTED RELATIONSHIPS:", *rel_lines]

    correction_lines: list[str] = []
    if domain_hint:
        correction_lines = [
            "",
            f"DOMAIN CORRECTION FROM USER: The user reviewed your previous analysis and says "
            f'this dataset is: "{domain_hint}". Use this as your domain — do not contradict it. '
            "Apply the analytical standards, KPIs, and benchmarks appropriate for that domain.",
        ]

    lines += correction_lines + [
        "",
        "Now call get_correlations, get_outliers, and get_missing_values.",
        "Then identify the domain yourself from the column structure, and write your full analysis.",
        "Your ## ANALYTICAL_PLAN ## must use ONLY exact column names from the list above.",
    ]
    return "\n".join(lines)


def stream_analysis(
    profiler: DataProfiler,
    profile: DataProfile,
    model: str | None = None,
    domain_hint: str | None = None,
) -> Generator[bytes, None, AnalysisResult]:
    """Generator that yields SSE bytes for the /analyze endpoint.

    Yields status + token events, then returns the final AnalysisResult.

    Two-phase approach:
      1. Run the tool-use loop silently (no streaming). Emit status events.
      2. Re-request the final response with .stream() to emit token events.
    """
    resolved_model = model or os.getenv("DEFAULT_MODEL") or _DEFAULT_MODEL
    client = anthropic.Anthropic()

    yield _sse({"type": "status", "message": "Reading column structure..."})

    # ── Phase 1: Silent tool-use loop ──────────────────────────────────────
    initial_message = _build_initial_message(profile, domain_hint=domain_hint)
    messages: list[dict] = [{"role": "user", "content": initial_message}]

    for iteration in range(_MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=resolved_model,
            max_tokens=16000,
            system=_ANALYSIS_SYSTEM_PROMPT,
            tools=TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        if response.stop_reason == "end_turn":
            # Claude finished without calling more tools — extract text and stream it
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            final_text = "\n".join(text_blocks)
            result = _parse_analysis(final_text, profile=profile)
            yield _sse({"type": "status", "message": "Formatting insights..."})
            # Stream the final text token by token for UX
            for chunk in _chunk_text(final_text, chunk_size=4):
                yield _sse({"type": "token", "text": chunk})
            return result

        # Tool calls — execute them silently and emit a status update
        tool_results = []
        tool_names = []
        for block in response.content:
            if block.type == "tool_use":
                tool_names.append(block.name)
                result_str = _execute_tool(profiler, block.name, block.input)  # type: ignore[arg-type]
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                )

        if tool_names:
            tool_display = ", ".join(
                t.replace("get_", "").replace("_", " ") for t in tool_names
            )
            yield _sse(
                {"type": "status", "message": f"Querying: {tool_display}..."}
            )

        messages.append({"role": "assistant", "content": response.content})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    # Fell out of the loop — return whatever we have
    yield _sse({"type": "status", "message": "Finalising analysis..."})
    return AnalysisResult(
        executive_summary="Analysis reached maximum tool iterations.",
        raw_response="",
    )


# ---------------------------------------------------------------------------
# Chat streaming generator
# ---------------------------------------------------------------------------


def stream_chat(
    profiler: DataProfiler,
    chat_history: list[dict],
    user_message: str,
    model: str | None = None,
    analysis_context: str | None = None,
) -> Generator[bytes, None, str]:
    """Generator that yields SSE bytes for the /chat endpoint.

    Handles tool calls inline during streaming, appending results and
    continuing the stream. Returns the full assistant reply as a string.
    """
    resolved_model = model or os.getenv("DEFAULT_MODEL") or _DEFAULT_MODEL
    client = anthropic.Anthropic()

    # Inject analysis context into system prompt if available
    system_prompt = _CHAT_SYSTEM_PROMPT
    if analysis_context:
        system_prompt = (
            _CHAT_SYSTEM_PROMPT
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "ANALYSIS ALREADY COMPLETED — USE THIS CONTEXT:\n"
            + analysis_context
            + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "Build on these findings. Do not repeat them unless asked. Go deeper."
        )

    # Build messages: history + new user turn
    messages = list(chat_history)
    messages.append({"role": "user", "content": user_message})

    full_reply = ""

    # Run a tool-use loop for chat too (Claude may call tools)
    for _ in range(_MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=resolved_model,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        # Collect text from this response
        for block in response.content:
            if hasattr(block, "text") and block.text:
                full_reply += block.text
                # Stream the text chunk by chunk
                for chunk in _chunk_text(block.text, chunk_size=4):
                    yield _sse({"type": "token", "text": chunk})

        if response.stop_reason == "end_turn":
            return full_reply

        # Handle tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_str = _execute_tool(profiler, block.name, block.input)  # type: ignore[arg-type]
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return full_reply


# ---------------------------------------------------------------------------
# Analysis parsing (identical to Project 1's _parse_analysis)
# ---------------------------------------------------------------------------


def _parse_analysis(raw_text: str, profile: DataProfile | None = None) -> AnalysisResult:
    """Parse Claude's delimiter-based response into an AnalysisResult."""
    from services.chart_compiler import compile_questions

    result = AnalysisResult(executive_summary="", raw_response=raw_text)

    def _extract(tag: str) -> str:
        pattern = rf"## {re.escape(tag)} ##\s*(.*?)(?=## \w[\w_ ]* ##|$)"
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    # Domain section
    domain_block = _extract("DOMAIN")
    if domain_block:
        try:
            json_match = re.search(r"\{.*?\}", domain_block, re.DOTALL)
            if json_match:
                d = json.loads(json_match.group())
                result.domain = d.get("domain", "")
                result.grain = d.get("grain", "")
                result.practitioner_persona = d.get("practitioner_persona", "")
        except Exception:
            pass

    # Insight cards (4 fixed slots)
    cards_block = _extract("INSIGHT_CARDS")
    if cards_block:
        try:
            json_match = re.search(r"\{.*\}", cards_block, re.DOTALL)
            if json_match:
                result.insight_cards = json.loads(json_match.group()).get("cards", [])
        except Exception:
            result.insight_cards = []

    result.executive_summary = _extract("EXECUTIVE_SUMMARY") or raw_text[:500]
    result.methodology_notes = _extract("METHODOLOGY")

    kf_block = _extract("KEY_FINDINGS")
    if kf_block:
        result.key_findings = _parse_numbered_list(kf_block)

    anomalies_block = _extract("ANOMALIES")
    if anomalies_block:
        result.anomalies = _parse_bullet_list(anomalies_block)

    recs_block = _extract("RECOMMENDATIONS")
    if recs_block:
        result.recommendations = _parse_numbered_list(recs_block)

    col_block = _extract("COLUMN_ANALYSES")
    if col_block:
        result.column_analyses = _parse_column_analyses(col_block)

    # Analytical plan → compile to chart specs
    plan_block = _extract("ANALYTICAL_PLAN")
    if plan_block:
        try:
            json_match = re.search(r"\{.*\}", plan_block, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                questions = parsed.get("questions", [])
                result.skip_distributions = parsed.get("skip_distributions", [])
                if profile is not None:
                    result.chart_specs = compile_questions(questions, profile)
                    logger.info(
                        f"Domain: {result.domain!r} | "
                        f"{len(result.chart_specs)}/{len(questions)} specs compiled"
                    )
                else:
                    result.chart_specs = []
        except Exception:
            result.chart_specs = []
            result.skip_distributions = []
    else:
        # Fall back to legacy CHART_SPECS block if present (backwards compat)
        chart_block = _extract("CHART_SPECS")
        if chart_block:
            try:
                json_match = re.search(r"\{.*\}", chart_block, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    result.chart_specs = parsed.get("charts", [])
                    result.skip_distributions = parsed.get("skip_distributions", [])
            except Exception:
                result.chart_specs = []

    return result


def _parse_numbered_list(text: str) -> list[str]:
    """Parse a numbered markdown list into a list of strings."""
    items = re.findall(r"^\d+\.\s+(.+)$", text, re.MULTILINE)
    return [item.strip() for item in items if item.strip()]


def _parse_bullet_list(text: str) -> list[str]:
    """Parse a bullet markdown list into a list of strings."""
    items = re.findall(r"^[-*]\s+(.+)$", text, re.MULTILINE)
    return [item.strip() for item in items if item.strip()]


def _parse_column_analyses(text: str) -> list[ColumnAnalysis]:
    """Parse the COLUMN_ANALYSES block into a list of ColumnAnalysis objects."""
    analyses: list[ColumnAnalysis] = []
    sections = re.split(r"^### (.+)$", text, flags=re.MULTILINE)
    it = iter(sections[1:])
    for col_name in it:
        try:
            content = next(it)
        except StopIteration:
            content = ""
        col_name = col_name.strip()
        summary = _extract_field(content, "Summary")
        quality = _extract_field(content, "Quality")
        patterns = _extract_field(content, "Patterns")
        analyses.append(
            ColumnAnalysis(
                column_name=col_name,
                summary=summary,
                quality=quality,
                patterns=patterns,
            )
        )
    return analyses


def _extract_field(text: str, field_name: str) -> str:
    """Extract a labelled field (e.g. 'Summary: ...') from a text block."""
    pattern = rf"^{re.escape(field_name)}:\s*(.+?)(?=\n[A-Z][a-z]+:|$)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _chunk_text(text: str, chunk_size: int = 4) -> Generator[str, None, None]:
    """Yield text in chunks of approximately chunk_size characters."""
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
