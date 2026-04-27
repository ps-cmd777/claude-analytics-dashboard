"""Report generator — assembles a Markdown report from profile + analysis data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from services.profiler import DataProfile
from services.claude_client import AnalysisResult


def generate_report(
    filename: str,
    profile: DataProfile,
    analysis: AnalysisResult,
) -> str:
    """Assemble and return a complete Markdown report as a string.

    This is a simplified version of Project 1's ReportGenerator adapted for
    the web context — returns the string directly rather than writing to disk.
    """
    timestamp = _format_timestamp()

    sections = [
        _render_header(filename, profile, timestamp),
        _render_executive_summary(analysis),
        _render_key_findings(analysis),
        _render_data_quality_table(profile),
        _render_column_analyses(analysis),
        _render_anomalies(analysis),
        _render_recommendations(analysis),
        _render_methodology(profile, analysis),
        _render_footer(),
    ]

    return "\n\n---\n\n".join(s for s in sections if s.strip())


def report_filename(filename: str) -> str:
    """Generate a timestamped filename for the report download."""
    stem = _sanitize_filename(Path(filename).stem)
    timestamp = _format_timestamp()
    return f"report_{stem}_{timestamp}.md"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_header(filename: str, profile: DataProfile, timestamp: str) -> str:
    """Render the report title and dataset metadata block."""
    rows, cols = profile.shape
    lines = [
        f"# Data Analysis Report — `{filename}`",
        "",
        f"> Generated: {timestamp}  ",
        f"> Source file: `{filename}`  ",
        f"> Dataset: {rows:,} rows × {cols} columns  ",
        f"> Memory: {profile.memory_usage_mb} MB  ",
        f"> Missing values: {profile.total_missing_pct}%  ",
        f"> Duplicate rows: {profile.duplicate_rows}  ",
    ]
    if profile.date_columns:
        lines.append(f"> Date columns detected: {', '.join(profile.date_columns)}  ")
    lines += [
        "",
        "**Column summary**",
        f"- Numeric: {len(profile.numeric_columns)} column(s) — "
        + (", ".join(f"`{c}`" for c in profile.numeric_columns) or "none"),
        f"- Categorical: {len(profile.categorical_columns)} column(s) — "
        + (", ".join(f"`{c}`" for c in profile.categorical_columns) or "none"),
        f"- Date/Time: {len(profile.date_columns)} column(s) — "
        + (", ".join(f"`{c}`" for c in profile.date_columns) or "none"),
    ]
    return "\n".join(lines)


def _render_executive_summary(analysis: AnalysisResult) -> str:
    """Render the executive summary section."""
    return f"## 1. Executive Summary\n\n{analysis.executive_summary}"


def _render_key_findings(analysis: AnalysisResult) -> str:
    """Render the top 5 key findings as a numbered list."""
    if not analysis.key_findings:
        return "## 2. Key Findings\n\n_No key findings were returned._"
    items = "\n".join(
        f"{i+1}. {finding}" for i, finding in enumerate(analysis.key_findings[:5])
    )
    return f"## 2. Key Findings\n\n{items}"


def _render_data_quality_table(profile: DataProfile) -> str:
    """Render a Markdown table showing data quality metrics per column."""
    header = (
        "## 3. Data Quality Assessment\n\n"
        "| Column | Type | Missing # | Missing % | Unique | Outliers |\n"
        "|--------|------|----------:|----------:|-------:|---------:|"
    )
    rows = sorted(
        profile.column_profiles.values(),
        key=lambda cp: cp.missing_pct,
        reverse=True,
    )
    table_rows = []
    for cp in rows:
        outliers = cp.outlier_count if cp.outlier_count else "—"
        table_rows.append(
            f"| `{cp.name}` | {cp.dtype} | {cp.missing_count:,} "
            f"| {cp.missing_pct:.1f}% | {cp.unique_count:,} | {outliers} |"
        )
    return header + "\n" + "\n".join(table_rows)


def _render_column_analyses(analysis: AnalysisResult) -> str:
    """Render the column-by-column analysis section."""
    if not analysis.column_analyses:
        return "## 4. Column-by-Column Analysis\n\n_No column-level analysis available._"

    sections = ["## 4. Column-by-Column Analysis"]
    for ca in analysis.column_analyses:
        block = [
            f"### `{ca.column_name}`",
            "",
            f"**Summary:** {ca.summary}" if ca.summary else "",
            f"**Data Quality:** {ca.quality}" if ca.quality else "",
            f"**Patterns:** {ca.patterns}" if ca.patterns else "",
        ]
        sections.append("\n".join(line for line in block if line is not None))

    return "\n\n".join(sections)


def _render_anomalies(analysis: AnalysisResult) -> str:
    """Render detected anomalies and outliers."""
    if not analysis.anomalies:
        return "## 5. Anomalies & Outliers\n\n_No significant anomalies detected._"
    items = "\n".join(f"- {anomaly}" for anomaly in analysis.anomalies)
    return f"## 5. Anomalies & Outliers\n\n{items}"


def _render_recommendations(analysis: AnalysisResult) -> str:
    """Render actionable recommendations as a numbered list."""
    if not analysis.recommendations:
        return "## 6. Recommendations\n\n_No recommendations were returned._"
    items = "\n".join(
        f"{i+1}. {rec}" for i, rec in enumerate(analysis.recommendations)
    )
    return f"## 6. Recommendations\n\n{items}"


def _render_methodology(profile: DataProfile, analysis: AnalysisResult) -> str:
    """Render the methodology section."""
    auto_method = (
        f"**Profiling:** Pandas v2+ was used to compute column-level statistics "
        f"for all {profile.shape[1]} columns, including missing value counts, "
        f"cardinality, numeric distributions, and categorical value frequencies. "
        f"Outliers were identified using the IQR method.\n\n"
        f"**AI Analysis:** The data profile was sent to the Claude API using the "
        f"tool-use pattern. Claude called specialized profiler tools to retrieve "
        f"column statistics, correlation data, outlier summaries, and missing value "
        f"details before generating the narrative analysis above."
    )
    claude_method = analysis.methodology_notes or ""
    combined = auto_method
    if claude_method:
        combined += f"\n\n{claude_method}"
    return f"## 7. Methodology\n\n{combined}"


def _render_footer() -> str:
    """Render the report footer."""
    return (
        "_Report generated by [claude-analytics-dashboard]"
        "(https://github.com/shushan/claude-analytics-dashboard) "
        "— Built with [Claude Code](https://claude.ai/code)_"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_timestamp() -> str:
    """Return a UTC timestamp string."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _sanitize_filename(name: str) -> str:
    """Replace unsafe filename characters with underscores."""
    return re.sub(r"[^\w\-]", "_", name)
