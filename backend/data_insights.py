"""
Data Insight Generator — Gemini-powered actionable insights in simple language.

Computes statistical facts locally, then uses Gemini to convert them into
simple, actionable advice. Supports multilingual output (Hindi, Marathi, etc.)
"""
import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

# Gemini SDK
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Initialize Gemini client
_gemini_client = None

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None and GEMINI_AVAILABLE:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


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

    # 7. Chart diversity
    if charts:
        chart_types = list(set(c["type"] for c in charts))
        facts.append({
            "type": "chart_info",
            "chart_count": len(charts),
            "chart_types": chart_types,
        })

    return facts


def _gemini_humanize_insights(facts: List[dict], language: str = "English") -> List[Dict[str, str]]:
    """Use Gemini to convert statistical facts into simple, actionable insights."""
    client = _get_gemini_client()
    if not client:
        return _fallback_insights(facts)

    facts_json = json.dumps(facts, default=str)

    prompt = f"""You are a friendly data analyst explaining findings to a business owner who is not technical.

Here are statistical findings from their dataset:
{facts_json}

Convert each finding into a simple, actionable insight. Follow these rules:

1. Language: Write ALL insights in **{language}**
2. Use simple words a 15-year-old would understand
3. NO technical jargon (no "IQR", "skewness", "correlation coefficient", "standard deviation")
4. Give practical business advice with each insight
5. Use real numbers from the data
6. Be warm and encouraging

EXAMPLES of good insights (in English):
- Instead of "Distribution is right-skewed with skew=2.3" → "Most of your sales are small, but a few big orders bring in a LOT of money! 💰 Consider creating special deals for those big buyers."
- Instead of "Strong correlation (0.85) between X and Y" → "When X goes up, Y goes up too! They move together. If you can increase X, you'll likely see Y grow as well."
- Instead of "25% outliers detected" → "Some values are unusually high or low compared to the rest. These could be special cases worth investigating — they might be errors or hidden opportunities!"

Reply with a JSON array of objects. Each object has "title" and "description":
[
  {{"title": "short title", "description": "2-3 sentence insight with advice"}},
  ...
]

Return 4-6 insights. Reply ONLY with the JSON array in **{language}**.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        insights = json.loads(text)
        if isinstance(insights, list) and len(insights) > 0:
            return insights[:8]
    except Exception as e:
        print(f"DEBUG: Gemini insight generation failed: {e}")

    return _fallback_insights(facts)


def _fallback_insights(facts: List[dict]) -> List[Dict[str, str]]:
    """Simple local fallback when Gemini is unavailable."""
    insights = []
    for f in facts:
        if f["type"] == "overview":
            missing_msg = (
                "Your data is complete — no missing values!"
                if f["missing_pct"] == 0
                else f"About {f['missing_pct']}% of values are missing, but we can still work with what is available."
            )
            insights.append({
                "title": "Your Data at a Glance",
                "description": f"You have {f['rows']:,} records with {f['columns']} columns. {missing_msg}"
            })
        elif f["type"] == "outlier":
            insights.append({
                "title": f"Unusual Values in {f['column']}",
                "description": (
                    f"About {f['outlier_pct']}% of {f['column']} values are unusually high or low. "
                    f"These could be special cases worth checking — they might reveal errors or hidden opportunities!"
                )
            })
        elif f["type"] == "dominance":
            insights.append({
                "title": f"'{f['top_value']}' Leads the Pack",
                "description": (
                    f"In {f['column']}, '{f['top_value']}' accounts for {f['top_pct']}% of all data. "
                    f"That is a big share! Consider whether you want to diversify, or double down on what is working."
                )
            })
        elif f["type"] == "metric_summary":
            insights.append({
                "title": f"{f['column']} Summary",
                "description": (
                    f"{f['column']} ranges from {f['min']:,.2f} to {f['max']:,.2f}. "
                    f"The average is {f['mean']:,.2f} and the middle value is {f['median']:,.2f}. "
                    f"Total across all records: {f['total']:,.2f}."
                )
            })
        elif f["type"] == "correlation":
            pair = f["pairs"][0]
            direction = "go up together" if pair["value"] > 0 else "move in opposite directions"
            insights.append({
                "title": f"{pair['col1']} & {pair['col2']} are Connected",
                "description": (
                    f"When {pair['col1']} changes, {pair['col2']} tends to {direction}. "
                    f"This relationship could help you make predictions or find root causes."
                )
            })

    if not insights:
        insights.append({
            "title": "Data Loaded Successfully",
            "description": "Your data is ready for analysis. Try using the chat to explore specific aspects of your dataset!"
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
