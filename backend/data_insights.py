"""
Data Insight Generator — Gemini-powered actionable insights in simple language.

Computes statistical facts locally, then uses Gemini to convert them into
simple, actionable advice. Supports multilingual output (Hindi, Marathi, etc.)
"""
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

from backend.gemini_helpers import get_gemini_client, call_gemini, compute_data_hash


def _compute_statistical_facts(df: pd.DataFrame, charts: List[dict]) -> List[dict]:
    """Compute raw statistical facts from the data (no Gemini needed)."""
    facts = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

    # 1. Dataset Overview
    missing_pct = (df.isnull().sum().sum() / max(len(df) * len(df.columns), 1)) * 100
    facts.append({
        "type": "overview",
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_count": len(numeric_cols),
        "categorical_count": len(categorical_cols),
        "missing_pct": round(missing_pct, 1),
    })

    # 2. Outlier Detection (IQR)
    for col in numeric_cols[:3]:
        series = df[col].dropna()
        if len(series) < 10:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        outlier_pct = round(outlier_count / len(series) * 100, 1)
        if outlier_pct > 1:
            facts.append({
                "type": "outlier",
                "column": col,
                "outlier_count": outlier_count,
                "outlier_pct": outlier_pct,
                "normal_range": f"{q1:,.2f} to {q3:,.2f}",
            })
            break

    # 3. Skewness
    for col in numeric_cols[:3]:
        series = df[col].dropna()
        if len(series) < 20:
            continue
        skew = series.skew()
        if abs(skew) > 1.0:
            facts.append({
                "type": "skewness",
                "column": col,
                "skew_value": round(float(skew), 2),
                "direction": "right" if skew > 0 else "left",
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
            })
            break

    # 4. Correlations
    if len(numeric_cols) >= 2:
        try:
            corr = df[numeric_cols[:15]].corr()
            pairs = []
            for i in range(len(corr.columns)):
                for j in range(i+1, len(corr.columns)):
                    v = corr.iloc[i, j]
                    if not np.isnan(v) and abs(v) > 0.5:
                        pairs.append({
                            "col1": corr.columns[i],
                            "col2": corr.columns[j],
                            "value": round(float(v), 2)
                        })
            pairs.sort(key=lambda x: abs(x["value"]), reverse=True)
            if pairs:
                facts.append({
                    "type": "correlation",
                    "pairs": pairs[:3],
                })
        except Exception:
            pass

    # 5. Category Dominance
    for col in categorical_cols[:2]:
        vc = df[col].value_counts()
        if len(vc) < 2:
            continue
        top_val = str(vc.index[0])
        top_pct = round(vc.iloc[0] / len(df) * 100, 1)
        if top_pct > 25:
            facts.append({
                "type": "dominance",
                "column": col,
                "top_value": top_val,
                "top_pct": top_pct,
                "total_categories": len(vc),
            })
            break

    # 6. Key Metric Summary
    for col in numeric_cols[:2]:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        facts.append({
            "type": "metric_summary",
            "column": col,
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "total": round(float(series.sum()), 2),
        })

    # 7. Pareto / Concentration Analysis (80-20 rule)
    for col in numeric_cols[:2]:
        series = df[col].dropna().sort_values(ascending=False)
        if len(series) < 10:
            continue
        total = series.sum()
        if total == 0:
            continue
        cumsum = series.cumsum()
        top_20_idx = int(len(series) * 0.2)
        if top_20_idx < 1:
            top_20_idx = 1
        top_20_share = round(float(cumsum.iloc[top_20_idx - 1] / total * 100), 1)
        if top_20_share > 50:  # Only report if concentration is notable
            facts.append({
                "type": "concentration",
                "column": col,
                "top_20_pct_share": top_20_share,
                "total_records": len(series),
            })
            break

    # 8. Growth / Trend Detection (if temporal column exists)
    temporal_cols = [c for c in df.columns if df[c].dtype == 'datetime64[ns]']
    if not temporal_cols:
        # Try to detect date columns
        for c in df.columns:
            if df[c].dtype == 'object':
                try:
                    parsed = pd.to_datetime(df[c], errors='coerce')
                    if parsed.notna().sum() > len(df) * 0.5:
                        temporal_cols.append(c)
                        break
                except Exception:
                    pass

    if temporal_cols and numeric_cols:
        try:
            date_col = temporal_cols[0]
            metric_col = numeric_cols[0]
            temp_df = df[[date_col, metric_col]].copy()
            temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
            temp_df = temp_df.dropna()
            if len(temp_df) > 10:
                temp_df = temp_df.sort_values(date_col)
                # Split into first half and second half
                mid = len(temp_df) // 2
                first_half_avg = temp_df[metric_col].iloc[:mid].mean()
                second_half_avg = temp_df[metric_col].iloc[mid:].mean()
                if first_half_avg > 0:
                    growth_pct = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1)
                    direction = "growing" if growth_pct > 0 else "declining"
                    facts.append({
                        "type": "trend",
                        "date_column": date_col,
                        "metric_column": metric_col,
                        "growth_pct": growth_pct,
                        "direction": direction,
                        "first_half_avg": round(float(first_half_avg), 2),
                        "second_half_avg": round(float(second_half_avg), 2),
                    })
        except Exception:
            pass

    # 9. Chart diversity
    if charts:
        chart_types = sorted(set(c["type"] for c in charts))
        facts.append({
            "type": "chart_info",
            "chart_count": len(charts),
            "chart_types": chart_types,
        })

    # Sort facts by type for deterministic ordering (same data → same order always)
    type_order = [
        "overview", "outlier", "skewness", "correlation",
        "dominance", "metric_summary", "concentration", "trend", "chart_info"
    ]
    facts.sort(key=lambda f: (
        type_order.index(f["type"]) if f["type"] in type_order else 99,
        f.get("column", ""),
    ))

    return facts


def _gemini_humanize_insights(facts: List[dict], language: str = "English") -> List[Dict[str, str]]:
    """Use Gemini to convert statistical facts into deep, business-friendly insights."""
    client = get_gemini_client()
    if not client:
        return _fallback_insights(facts)

    facts_json = json.dumps(facts, default=str)

    prompt = f"""You are "Vidhur" — a senior business intelligence advisor presenting findings to a CEO/business owner with NO technical background.

Your analysis should feel like a trusted advisor giving a boardroom briefing — profound, clear, and actionable.

Here are statistical findings from their dataset:
{facts_json}

Convert each finding into a DEEP, PROFOUND business insight. Follow these rules strictly:

1. **Language**: CRITICAL - Write the ENTIRE OUTPUT in **{language}**. All titles, descriptions, and advice MUST be translated to {language}.
2. **Zero jargon**: NO "IQR", "skewness", "correlation", "standard deviation", "quartile", "regression". Instead use plain business language.
3. **Deep analysis**: Don't just state facts — EXPLAIN what they mean for the business. Think like a McKinsey consultant:
   - What's the business IMPACT?
   - What's the ROOT CAUSE likely to be?
   - What's the RISK if ignored?
   - What's the OPPORTUNITY if acted on?
4. **Use analogies**: Compare findings to everyday business situations (e.g. "This is like a store where 80% of profit comes from just 20% of customers")
5. **Use real numbers** from the data — be specific
6. **Be warm, encouraging, and confident** — like a trusted mentor
7. **Each insight must have 4 parts** (all MUST be in **{language}**):
   - "title": A compelling, clear headline (5-8 words)
   - "description": The core finding explained simply (2-3 sentences)
   - "why_it_matters": Why this is important for the business (1-2 sentences)
   - "action_steps": Specific, practical next steps to take (1-2 bullet points as a string)

EXAMPLES of the depth expected (Note: Even though examples are in English, your output MUST be in {language}):
- SHALLOW: "Sales are growing" ❌
- DEEP: "Your revenue grew 23% in the second half compared to the first half — that's faster than most businesses in this category! 📈 This momentum suggests your recent strategy is working. Double down on whatever changed midway — was it a new product launch, marketing push, or seasonal effect?" ✅

- SHALLOW: "Some values are outliers" ❌
- DEEP: "About 8% of your transactions are unusually large — worth ₹50,000+ each while most are under ₹5,000. These 'whale' customers are your hidden goldmine! 🐋 A dedicated relationship manager for this 8% could boost revenue by 15-20% with minimal extra cost." ✅

Reply with a JSON array:
[
  {{
    "title": "compelling headline",
    "description": "core finding in simple language",
    "why_it_matters": "business impact explanation",
    "action_steps": "specific next steps"
  }}
]

Return exactly 5-6 insights. Reply ONLY with the JSON array in **{language}**."""

    try:
        # temperature=0 ensures deterministic output: same data → same insights every time
        text = call_gemini(prompt, client=client, temperature=0.0)
        insights = json.loads(text)
        if isinstance(insights, list) and len(insights) > 0:
            return insights[:8]
    except Exception as e:
        print(f"DEBUG: Gemini insight generation failed: {e}")

    return _fallback_insights(facts)


def _fallback_insights(facts: List[dict]) -> List[Dict[str, str]]:
    """Local fallback when Gemini is unavailable — enhanced with structured output."""
    insights = []
    for f in facts:
        if f["type"] == "overview":
            missing_msg = (
                "Your data is complete — no missing values!"
                if f["missing_pct"] == 0
                else f"About {f['missing_pct']}% of values are missing, but we can still work with what is available."
            )
            insights.append({
                "title": "📋 Your Data at a Glance",
                "description": f"You have {f['rows']:,} records with {f['columns']} columns. {missing_msg}",
                "why_it_matters": "Understanding your data size and completeness helps you know how reliable the analysis will be.",
                "action_steps": "Review columns with missing values and decide if they need to be filled or removed."
            })
        elif f["type"] == "outlier":
            insights.append({
                "title": f"⚡ Unusual Values in {f['column']}",
                "description": (
                    f"About {f['outlier_pct']}% of {f['column']} values are unusually high or low. "
                    f"Think of it like a classroom where most students score 60-80, but a few score 15 or 99."
                ),
                "why_it_matters": "These unusual values could be errors in data entry, or they could represent your best (or worst) performers — both worth investigating.",
                "action_steps": "Check the top 5 highest and lowest values manually. Are they real? If yes, study what makes them different."
            })
        elif f["type"] == "dominance":
            insights.append({
                "title": f"👑 '{f['top_value']}' Dominates {f['column']}",
                "description": (
                    f"In {f['column']}, '{f['top_value']}' accounts for {f['top_pct']}% of all data — "
                    f"that's a huge share out of {f['total_categories']} categories."
                ),
                "why_it_matters": "High dependency on one category is risky. If it underperforms, your overall numbers drop significantly.",
                "action_steps": "Evaluate if this concentration is intentional. Consider diversifying if you're over-reliant on one segment."
            })
        elif f["type"] == "metric_summary":
            insights.append({
                "title": f"📊 {f['column']} Performance Overview",
                "description": (
                    f"{f['column']} ranges from {f['min']:,.2f} to {f['max']:,.2f}. "
                    f"The average is {f['mean']:,.2f} and the midpoint is {f['median']:,.2f}. Total: {f['total']:,.2f}."
                ),
                "why_it_matters": "The gap between average and midpoint tells you if your data is balanced or if a few big values are pulling the average up.",
                "action_steps": "Set performance benchmarks based on the average. Investigate values significantly below the midpoint."
            })
        elif f["type"] == "correlation":
            pair = f["pairs"][0]
            direction = "go up together" if pair["value"] > 0 else "move in opposite directions"
            insights.append({
                "title": f"🔗 {pair['col1']} & {pair['col2']} Move Together",
                "description": (
                    f"When {pair['col1']} changes, {pair['col2']} tends to {direction}. "
                    f"This is like how temperature and ice cream sales are connected — one drives the other."
                ),
                "why_it_matters": "Understanding these connections helps you find what drives your key business metrics.",
                "action_steps": f"If you want to improve {pair['col2']}, try influencing {pair['col1']} first and track the results."
            })
        elif f["type"] == "concentration":
            insights.append({
                "title": f"🎯 The 80/20 Rule in {f['column']}",
                "description": (
                    f"The top 20% of your records account for {f['top_20_pct_share']}% of total {f['column']}. "
                    f"This is the classic Pareto principle in action!"
                ),
                "why_it_matters": "Your biggest results come from a small portion of your data. Focusing on this top slice gives you the most impact per effort.",
                "action_steps": "Identify what makes the top 20% different. Replicate those conditions across the rest."
            })
        elif f["type"] == "trend":
            emoji = "📈" if f["direction"] == "growing" else "📉"
            insights.append({
                "title": f"{emoji} {f['metric_column']} is {f['direction'].title()}",
                "description": (
                    f"{f['metric_column']} changed by {f['growth_pct']}% — from an average of {f['first_half_avg']:,.2f} "
                    f"in the first half to {f['second_half_avg']:,.2f} in the second half."
                ),
                "why_it_matters": f"A {'positive' if f['growth_pct'] > 0 else 'negative'} trend means your strategy is {'working' if f['growth_pct'] > 0 else 'needs adjustment'}. Act now while the trend is clear.",
                "action_steps": f"{'Double down on recent changes that drove growth.' if f['growth_pct'] > 0 else 'Investigate what changed midway and course-correct immediately.'}"
            })

    if not insights:
        insights.append({
            "title": "✅ Data Loaded Successfully",
            "description": "Your data is ready for analysis. Try using the chat to explore specific aspects of your dataset!",
            "why_it_matters": "Having clean, loaded data is the first step to making informed business decisions.",
            "action_steps": "Ask Vidhur to show trends, compare categories, or highlight key performance indicators."
        })

    return insights[:8]


def generate_data_insights(
    df: pd.DataFrame,
    charts: List[dict],
    language: str = "English"
) -> List[Dict[str, str]]:
    """
    Generate simple, actionable insights from the dataset.

    Args:
        df: The dataset
        charts: Current chart configurations
        language: Target language for insights (English, Hindi, Marathi, Gujarati, etc.)

    Returns:
        List of {"title": ..., "description": ...} dicts
    """
    facts = _compute_statistical_facts(df, charts)
    return _gemini_humanize_insights(facts, language=language)
