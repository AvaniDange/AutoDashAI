"""
Insight Agent - Analyzes dashboard images, documents, and data files
using Gemini Vision API for rich AI-powered insights.
Falls back to local OCR when Gemini is unavailable.
"""
import io
import re
import json
import pandas as pd
import numpy as np
from typing import List, Dict

from backend.gemini_helpers import get_gemini_client, call_gemini, call_gemini_multimodal

# OCR fallback
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract/Pillow not installed. OCR fallback unavailable.")


class InsightAgent:
    def __init__(self):
        if get_gemini_client():
            print("Insight Agent: Gemini Vision mode initialized (model cascade)")
        else:
            print("Insight Agent: Local OCR fallback mode initialized")

    # ------------------------------------------------------------------ #
    #  PUBLIC: Analyze a dashboard image / chart screenshot / PDF page    #
    # ------------------------------------------------------------------ #
    def analyze_dashboard_image(
        self, file_bytes: bytes, mime_type: str, filename: str, language: str = "English"
    ) -> List[Dict[str, str]]:
        """Analyze a visual file (image or PDF) and return insights."""
        client = get_gemini_client()

        # Try Gemini Vision first
        if client:
            try:
                return self._gemini_vision_insights(client, file_bytes, mime_type, filename, language)
            except Exception as e:
                print(f"Gemini Vision failed, falling back to OCR: {e}")

        # Fallback to local OCR
        return self._ocr_insights(file_bytes, mime_type, filename)

    # ------------------------------------------------------------------ #
    #  PUBLIC: Analyze a data file (Excel / CSV)                          #
    # ------------------------------------------------------------------ #
    def analyze_data_file(
        self, file_bytes: bytes, mime_type: str, filename: str, language: str = "English"
    ) -> List[Dict[str, str]]:
        """Analyze an Excel or CSV file and return data-driven insights."""
        try:
            # Parse data
            if mime_type in (
                "text/csv",
                "application/csv",
            ) or filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes), engine="python", on_bad_lines="skip")
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))

            # Compute statistical facts
            facts = self._compute_stats(df)

            # Humanize with Gemini
            client = get_gemini_client()
            if client:
                try:
                    return self._gemini_humanize(client, facts, language)
                except Exception as e:
                    print(f"Gemini humanize failed: {e}")

            return self._local_humanize(facts)

        except Exception as e:
            print(f"Data file analysis error: {e}")
            return [
                {
                    "title": "File Processing Issue",
                    "description": f"We couldn't fully parse '{filename}'. Please make sure it is a valid CSV or Excel file with data.",
                    "why_it_matters": "Without properly parsed data, we cannot generate meaningful insights.",
                    "action_steps": "Try re-uploading the file or converting it to CSV format first."
                }
            ]

    # ------------------------------------------------------------------ #
    #  PRIVATE: Gemini Vision analysis                                    #
    # ------------------------------------------------------------------ #
    def _gemini_vision_insights(
        self, client, file_bytes: bytes, mime_type: str, filename: str, language: str = "English"
    ) -> List[Dict[str, str]]:
        prompt = f"""## MANDATORY LANGUAGE RULE — READ THIS FIRST
You MUST write the ENTIRE output in **{language}**. Every single word of every field (title, description, why_it_matters, action_steps) MUST be in **{language}**.
Do NOT write in English. Do NOT mix languages. If you output even one English sentence, you have FAILED.
If {language} is Hindi → use Devanagari script entirely.
If {language} is Marathi → use Devanagari script entirely.
If {language} is Tamil → use Tamil script entirely.
If {language} is Gujarati → use Gujarati script entirely.
If {language} is Telugu → use Telugu script entirely.
If {language} is Kannada → use Kannada script entirely.
If {language} is Bengali → use Bengali script entirely.
If {language} is Punjabi → use Gurmukhi script entirely.
If {language} is Malayalam → use Malayalam script entirely.
If {language} is Odia → use Odia script entirely.
If {language} is Assamese → use Assamese script entirely.

You are "Vidhur" — a senior business intelligence advisor analyzing a dashboard, chart, or visualization.

Analyze this image and provide 5-6 DEEP, PROFOUND business insights.

Rules:
1. Use simple language a non-technical CEO would understand — NO jargon
2. Don't just describe what you see — explain what it MEANS for the business
3. Give specific, actionable advice for each finding
4. Reference specific visual elements, numbers, or trends you see
5. Use business analogies to make complex patterns relatable
6. Be warm, confident, and encouraging
7. Each insight must have 4 parts (ALL written natively in **{language}**):
   - "title": Compelling headline (5-8 words)
   - "description": Core finding explained simply (2-3 sentences)
   - "why_it_matters": Business impact (1-2 sentences)
   - "action_steps": Specific next steps (1-2 practical recommendations)

Reply with ONLY a JSON array. EVERY value MUST be in {language}:
[
  {{"title": "...", "description": "...", "why_it_matters": "...", "action_steps": "..."}},
  ...
]

## FINAL CHECK: Before responding, verify that ZERO English words appear in your output (unless no {language} equivalent exists for a technical term). Output language: {language}."""

        from google.genai import types

        contents = [
            types.Content(
                parts=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    types.Part.from_text(text=prompt),
                ]
            )
        ]

        text = call_gemini_multimodal(contents, client=client, temperature=0.0)

        insights = json.loads(text)
        if isinstance(insights, list) and len(insights) > 0:
            return insights[:8]

        return self._generic_insights()

    # ------------------------------------------------------------------ #
    #  PRIVATE: OCR fallback                                              #
    # ------------------------------------------------------------------ #
    def _ocr_insights(
        self, file_bytes: bytes, mime_type: str, filename: str
    ) -> List[Dict[str, str]]:
        extracted_text = ""
        if OCR_AVAILABLE:
            try:
                image = Image.open(io.BytesIO(file_bytes))
                extracted_text = pytesseract.image_to_string(image)
            except Exception as e:
                print(f"OCR failed: {e}")

        return self._analyze_text(extracted_text, filename)

    # ------------------------------------------------------------------ #
    #  PRIVATE: Stats for data files                                      #
    # ------------------------------------------------------------------ #
    def _compute_stats(self, df: pd.DataFrame) -> List[dict]:
        facts = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

        # Dataset overview
        missing_pct = (df.isnull().sum().sum() / max(len(df) * len(df.columns), 1)) * 100
        facts.append({
            "type": "overview",
            "rows": len(df),
            "columns": len(df.columns),
            "numeric_count": len(numeric_cols),
            "categorical_count": len(categorical_cols),
            "missing_pct": round(missing_pct, 1),
        })

        # Outlier detection
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
                })
                break

        # Correlations
        if len(numeric_cols) >= 2:
            try:
                corr = df[numeric_cols[:15]].corr()
                pairs = []
                for i in range(len(corr.columns)):
                    for j in range(i + 1, len(corr.columns)):
                        v = corr.iloc[i, j]
                        if not np.isnan(v) and abs(v) > 0.5:
                            pairs.append({
                                "col1": corr.columns[i],
                                "col2": corr.columns[j],
                                "value": round(float(v), 2),
                            })
                pairs.sort(key=lambda x: abs(x["value"]), reverse=True)
                if pairs:
                    facts.append({"type": "correlation", "pairs": pairs[:3]})
            except Exception:
                pass

        # Category dominance
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

        # Metric summaries
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

        return facts

    # ------------------------------------------------------------------ #
    #  PRIVATE: Gemini humanize stats                                     #
    # ------------------------------------------------------------------ #
    def _gemini_humanize(self, client, facts: List[dict], language: str = "English") -> List[Dict[str, str]]:
        facts_json = json.dumps(facts, default=str)
        prompt = f"""## MANDATORY LANGUAGE RULE — READ THIS FIRST
You MUST write the ENTIRE output in **{language}**. Every single word of every field (title, description, why_it_matters, action_steps) MUST be in **{language}**.
Do NOT write in English. Do NOT mix languages. If you output even one English sentence, you have FAILED.
If {language} is Hindi → use Devanagari script entirely.
If {language} is Marathi → use Devanagari script entirely.
If {language} is Tamil → use Tamil script entirely.
If {language} is Gujarati → use Gujarati script entirely.
If {language} is Telugu → use Telugu script entirely.
If {language} is Kannada → use Kannada script entirely.
If {language} is Bengali → use Bengali script entirely.
If {language} is Punjabi → use Gurmukhi script entirely.
If {language} is Malayalam → use Malayalam script entirely.
If {language} is Odia → use Odia script entirely.
If {language} is Assamese → use Assamese script entirely.

You are "Vidhur" — a senior business intelligence advisor explaining data findings to a CEO with NO technical background.

Here are statistical findings from their dataset:
{facts_json}

Convert each finding into a DEEP, PROFOUND business insight. Rules:
1. Zero jargon — use plain business language
2. Explain the business IMPACT, not just the statistic
3. Use analogies and real-world examples
4. Be warm, confident, and encouraging
5. Each insight must have 4 parts (ALL written natively in **{language}**):
   - "title": Compelling headline
   - "description": Core finding in simple language (2-3 sentences)
   - "why_it_matters": Business relevance (1-2 sentences)
   - "action_steps": Specific, practical next steps

Reply with ONLY a JSON array. EVERY value MUST be in {language}:
[{{"title": "...", "description": "...", "why_it_matters": "...", "action_steps": "..."}}]

Return 5-6 insights.

## FINAL CHECK: Before responding, verify that ZERO English words appear in your output (unless no {language} equivalent exists for a technical term). Output language: {language}."""

        # temperature=0 ensures deterministic output: identical data → identical insights
        text = call_gemini(prompt, client=client, temperature=0.0)

        insights = json.loads(text)
        if isinstance(insights, list) and len(insights) > 0:
            return insights[:8]

        return self._local_humanize(facts)

    # ------------------------------------------------------------------ #
    #  PRIVATE: Local humanize fallback                                   #
    # ------------------------------------------------------------------ #
    def _local_humanize(self, facts: List[dict]) -> List[Dict[str, str]]:
        insights = []
        for f in facts:
            if f["type"] == "overview":
                msg = (
                    "Your data is complete — no missing values!"
                    if f["missing_pct"] == 0
                    else f"About {f['missing_pct']}% of values are missing."
                )
                insights.append({
                    "title": "📋 Your Data at a Glance",
                    "description": f"You have {f['rows']:,} records with {f['columns']} columns. {msg}",
                    "why_it_matters": "Understanding your data completeness helps gauge analysis reliability.",
                    "action_steps": "Review any columns with significant missing values."
                })
            elif f["type"] == "outlier":
                insights.append({
                    "title": f"⚡ Unusual Values in {f['column']}",
                    "description": (
                        f"About {f['outlier_pct']}% of {f['column']} values are unusually high or low. "
                        f"These could be special cases worth checking!"
                    ),
                    "why_it_matters": "Outliers may represent data errors or exceptional business opportunities.",
                    "action_steps": "Manually review the extreme values to determine if they're errors or genuine."
                })
            elif f["type"] == "dominance":
                insights.append({
                    "title": f"👑 '{f['top_value']}' Leads the Pack",
                    "description": (
                        f"In {f['column']}, '{f['top_value']}' accounts for {f['top_pct']}% of all data."
                    ),
                    "why_it_matters": "Concentration in one category can be a risk or an opportunity depending on your goals.",
                    "action_steps": "Evaluate whether this concentration is desirable or if diversification would reduce risk."
                })
            elif f["type"] == "metric_summary":
                insights.append({
                    "title": f"📊 {f['column']} Overview",
                    "description": (
                        f"{f['column']} ranges from {f['min']:,.2f} to {f['max']:,.2f}. "
                        f"Average: {f['mean']:,.2f}, Total: {f['total']:,.2f}."
                    ),
                    "why_it_matters": "Understanding the range and average helps set realistic benchmarks.",
                    "action_steps": "Set performance targets based on these numbers."
                })
            elif f["type"] == "correlation":
                pair = f["pairs"][0]
                direction = "go up together" if pair["value"] > 0 else "move in opposite directions"
                insights.append({
                    "title": f"🔗 {pair['col1']} & {pair['col2']} are Connected",
                    "description": f"When {pair['col1']} changes, {pair['col2']} tends to {direction}.",
                    "why_it_matters": "Connected metrics help identify cause-and-effect in your business.",
                    "action_steps": f"To influence {pair['col2']}, focus efforts on {pair['col1']}."
                })

        if not insights:
            insights.append({
                "title": "✅ Data Loaded Successfully",
                "description": "Your data is ready for analysis!",
                "why_it_matters": "Clean data is the foundation for good business decisions.",
                "action_steps": "Ask Vidhur to explore trends, compare categories, or highlight KPIs."
            })
        return insights[:8]

    # ------------------------------------------------------------------ #
    #  PRIVATE: Text pattern analysis (OCR fallback)                      #
    # ------------------------------------------------------------------ #
    def _analyze_text(self, text: str, filename: str) -> List[Dict[str, str]]:
        insights = []
        text_lower = text.lower()

        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', text)
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)

        if 'revenue' in text_lower or 'sales' in text_lower:
            if percentages:
                insights.append({
                    "title": "Revenue Performance",
                    "description": f"The dashboard shows revenue metrics with changes around {percentages[0]}. Monitor these trends for growth opportunities."
                })
            else:
                insights.append({
                    "title": "Sales Metrics Detected",
                    "description": "Revenue and sales data is displayed. Track month-over-month changes to identify growth patterns."
                })

        if 'customer' in text_lower or 'user' in text_lower:
            insights.append({
                "title": "Customer Engagement",
                "description": "Customer or user metrics are present. Focus on retention rates and lifetime value."
            })

        if any(word in text_lower for word in ['increase', 'growth', 'up', 'rise']):
            insights.append({
                "title": "Positive Trend Identified",
                "description": "Upward trends detected. Analyze contributing factors and replicate successful strategies."
            })
        elif any(word in text_lower for word in ['decrease', 'decline', 'down', 'drop']):
            insights.append({
                "title": "Performance Alert",
                "description": "Declining metrics detected. Investigate root causes and implement corrective actions."
            })

        if any(word in text_lower for word in ['month', 'quarter', 'year', 'daily', 'weekly']):
            insights.append({
                "title": "Time-Series Analysis",
                "description": "Temporal data present. Use this for forecasting and resource allocation."
            })

        if len(numbers) >= 3:
            insights.append({
                "title": "Key Metrics Overview",
                "description": f"The dashboard displays {len(numbers)} numerical indicators. Establish KPI benchmarks to track performance."
            })

        if not insights:
            insights = self._generic_insights()

        return insights[:6]

    def _generic_insights(self) -> List[Dict[str, str]]:
        return [
            {
                "title": "📊 Visual Data Representation",
                "description": "The dashboard uses visual elements to communicate data. Ensure charts are clearly labeled for easy interpretation.",
                "why_it_matters": "Clear visuals help everyone on your team make better decisions faster.",
                "action_steps": "Add labels and legends to any charts that aren't immediately clear."
            },
            {
                "title": "🎯 Key Performance Indicators",
                "description": "Identify the most critical KPIs and set up alerts for significant changes.",
                "why_it_matters": "Tracking the right metrics prevents costly surprises and reveals growth opportunities.",
                "action_steps": "Pick 3-5 KPIs that matter most to your goals and monitor them weekly."
            },
            {
                "title": "📈 Actionable Metrics",
                "description": "Focus on metrics that directly inform business decisions. Avoid vanity metrics.",
                "why_it_matters": "Actionable metrics drive real change; vanity metrics only give false confidence.",
                "action_steps": "For each metric on your dashboard, ask: 'Can I make a decision based on this?'"
            },
            {
                "title": "🔍 Comparative Analysis",
                "description": "Compare current performance against historical data and industry benchmarks.",
                "why_it_matters": "Context is everything — a number alone means nothing without comparison.",
                "action_steps": "Add year-over-year or month-over-month comparisons to your key charts."
            },
        ]


# Global instance
insight_agent = InsightAgent()
