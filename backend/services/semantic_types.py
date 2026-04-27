from enum import Enum


class SemanticRole(str, Enum):
    IDENTIFIER           = "identifier"           # primary keys — never aggregate
    TEMPORAL             = "temporal"             # dates/timestamps — group by time
    MEASURE_ADDITIVE     = "measure_additive"     # revenue, qty — SUM is meaningful
    MEASURE_AVERAGE_ONLY = "measure_average_only" # salary, age — MEAN only, NEVER sum
    MEASURE_RATIO        = "measure_ratio"        # %, rate — weighted mean only
    MEASURE_DERIVED      = "measure_derived"      # variance = actual - budget — NEVER in KPIs
    DIMENSION_LOW        = "dimension_low"        # 2–15 unique values — good for groupby
    DIMENSION_MEDIUM     = "dimension_medium"     # 16–50 unique — OK with top-N
    DIMENSION_HIGH       = "dimension_high"       # 50+ unique — filter only
    BOOLEAN              = "boolean"              # True/False — mean = rate
    TEXT_FREE            = "text_free"            # free-form notes — skip
    CONSTANT             = "constant"             # single value — skip
    EMPTY                = "empty"               # >95% missing — skip
