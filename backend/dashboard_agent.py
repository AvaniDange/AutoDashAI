import pandas as pd
import numpy as np
import uuid
import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.gemini_helpers import (
    get_gemini_client, call_gemini, call_gemini_json,
    call_gemini_fast, compute_data_hash, GEMINI_AVAILABLE,
)
from backend.visualization_engine import VisualizationEngine, profile_columns


class DashboardAgent:
    def __init__(self):
        self.sessions = {}
        self.viz_engine = VisualizationEngine()
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Initialize Gemini via shared helper
        self.client = get_gemini_client()
        self.gemini_enabled = self.client is not None
        if self.gemini_enabled:
            print("✅ Gemini (model cascade) enabled")
        else:
            print("⚠️ Gemini not configured — using local engine only")

    # ================= GEMINI HELPERS (via shared cascade) =================
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini with automatic model cascade and return cleaned text."""
        return call_gemini(prompt, client=self.client)

    def _call_gemini_json(self, prompt: str) -> dict:
        """Call Gemini with model cascade and parse JSON response."""
        return call_gemini_json(prompt, client=self.client)

    # ================= SESSION START =================
    def start_session(self, df: pd.DataFrame):
        session_id = str(uuid.uuid4())
        profiles = profile_columns(df)

        # --- Gemini Pre-Analysis + KPIs in PARALLEL for speed ---
        charts, kpis = self._parallel_pre_analysis(df, profiles)

        slicers = self._generate_slicers(df)
        pages = [{"id": "page1", "name": "Overview", "charts": charts, "kpis": kpis}]

        self.sessions[session_id] = {
            "df": df,
            "original_df": df.copy(),
            "active_page_idx": 0,
            "pages": pages,
            "slicers": slicers,
            "history": [],
            "last_active_chart_idx": 0 if charts else None,
            "theme": "light",
            "profiles": profiles,
            "data_hash": compute_data_hash(df.shape, df.columns.tolist()),
        }

        return session_id, charts, kpis, df.columns.tolist(), slicers, pages

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    # ================= PARALLEL PRE-ANALYSIS (Performance) =================
    def _parallel_pre_analysis(self, df, profiles):
        """
        Run Gemini chart pre-analysis and KPI generation concurrently.
        Cuts dashboard startup time by running both in parallel.
        """
        charts = []
        kpis = []

        if not self.gemini_enabled:
            return self.viz_engine.generate_dashboard(df)

        try:
            # Submit both tasks concurrently
            future_charts = self._executor.submit(self._gemini_pre_analysis, df, profiles)
            future_kpis = self._executor.submit(self.viz_engine._generate_smart_kpis, df, profiles)

            # Collect results
            gemini_charts, _ = future_charts.result(timeout=30)
            kpis = future_kpis.result(timeout=10)

            if gemini_charts:
                charts = gemini_charts
            else:
                charts, kpis = self.viz_engine.generate_dashboard(df)

        except Exception as e:
            print(f"⚠️ Parallel pre-analysis failed ({e}), falling back to serial")
            traceback.print_exc()
            charts, kpis = self.viz_engine.generate_dashboard(df)

        return charts, kpis

    # ================= GEMINI PRE-ANALYSIS =================
    def _gemini_pre_analysis(self, df, profiles):
        """
        Ask Gemini to analyze the dataset and suggest the best charts.
        Uses the FAST model (gemini-2.0-flash) for speed.
        Falls back to local engine if Gemini is unavailable.
        """
        if not self.gemini_enabled:
            return self.viz_engine.generate_dashboard(df)

        try:
            col_info = self._build_column_info(df, profiles)
            sample_rows = df.head(5).to_dict(orient="records")
            # Truncate sample for prompt size
            sample_str = json.dumps(sample_rows, default=str)[:2000]

            prompt = f"""You are an expert data analyst. Analyze this dataset and suggest the best 5 visualizations.

DATASET INFO:
- Rows: {len(df)}, Columns: {len(df.columns)}
- Columns:
{col_info}

SAMPLE DATA (first 5 rows):
{sample_str}

For each visualization, suggest the most insightful chart. Think like a BI analyst:
- What patterns, trends, or comparisons would be most valuable?
- Use appropriate chart types for the data semantics
- Use simple titles a teenager would understand

Reply ONLY with a JSON array of exactly 5 chart specs:
[
  {{
    "chart_type": "bar|line|area|pie|scatter",
    "x_column": "column_name",
    "y_column": "column_name",
    "aggregation": "sum|mean|count|median",
    "top_k": 10,
    "title": "Simple, clear title"
  }}
]

RULES:
- x_column and y_column MUST be exact column names from the dataset
- For time trends, use line or area charts
- For category comparisons, use bar or pie
- For relationships between numbers, use scatter
- Titles should be simple and clear (e.g., "Top Products by Sales", "Monthly Revenue Trend")
- Return ONLY the JSON array, nothing else
"""
            # Use FAST model for chart suggestions — speed matters more than depth here
            result = call_gemini_json(
                prompt,
                client=self.client,
                models=["gemini-3.1-flash-lite-preview"],  # Fast model only
                use_cache=True,
            )

            if not isinstance(result, list):
                raise ValueError("Gemini did not return a list")

            charts = []
            for spec in result[:6]:
                chart = self.viz_engine.build_chart_from_spec(df, spec)
                if chart:
                    # Override title with Gemini's simple title
                    if spec.get("title"):
                        chart["title"] = spec["title"]
                    charts.append(chart)

            if len(charts) < 2:
                raise ValueError(f"Only {len(charts)} charts built from Gemini specs")

            # KPIs: still use local engine (fast + reliable)
            _, kpis = self.viz_engine.generate_dashboard(df)
            print(f"✅ Gemini pre-analysis (fast): {len(charts)} charts generated")
            return charts, kpis

        except Exception as e:
            print(f"⚠️ Gemini pre-analysis failed ({e}), using local engine")
            traceback.print_exc()
            return self.viz_engine.generate_dashboard(df)

    # ================= CHAT PROCESSING =================
    def process_prompt(self, session_id, message, language="English"):
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "reply": "Session not found", "charts": None}

        # Add to history
        session["history"].append({"role": "user", "content": message})

        if self.gemini_enabled:
            try:
                result = self._process_with_gemini(session, message, language=language)
                session["history"].append({"role": "assistant", "content": result.get("reply", "")})
                return result
            except Exception as e:
                print(f"Gemini chat failed → fallback: {e}")
                traceback.print_exc()

        result = self._process_local_advanced(session, message)
        session["history"].append({"role": "assistant", "content": result.get("reply", "")})
        return result

    def _process_with_gemini(self, session, message, language="English"):
        profiles = session.get("profiles", [])
        slicers = session.get("slicers", [])
        df = session["df"]

        col_info = self._build_column_info(df, profiles)

        slicer_info = ", ".join([
            f"{s['column']} ({', '.join(s['options'][:5])})"
            for s in slicers[:5]
        ])

        current_charts = session["pages"][session["active_page_idx"]]["charts"]
        chart_summary = "\n".join([
            f"  Chart {i}: \"{c['title']}\" ({c['type']}, x={c.get('xAxis','')}, y={c.get('dataKey','')})"
            for i, c in enumerate(current_charts[:6])
        ])

        # Recent conversation context
        recent_history = session["history"][-6:]
        history_text = "\n".join([
            f"  {m['role'].upper()}: {m['content'][:100]}"
            for m in recent_history
        ])

        prompt = f"""## MANDATORY LANGUAGE RULE — READ THIS FIRST
You MUST write the "reply" field ENTIRELY in **{language}**. Not English. Not a mix. 100% pure **{language}**.
If the user selected {language}, you respond in {language} — even if the user typed in English.
Violating this rule is an automatic failure.

You are "Vidhur" — an intelligent BI dashboard assistant. You help users explore their data by creating and modifying visualizations.

DATASET ({len(df)} rows, {len(df.columns)} columns):
{col_info}

CURRENT CHARTS:
{chart_summary}

AVAILABLE FILTERS: {slicer_info if slicer_info else 'None'}

RECENT CONVERSATION:
{history_text}

USER REQUEST: {message}

Understand the user's intent and respond with a JSON object.

AVAILABLE ACTIONS:
1. "create_chart" — Create a new chart or replace charts based on user request
2. "change_chart" — Change the type of an existing chart (e.g., "make it a pie chart")
3. "filter" — Filter data by a column value
4. "reset_filter" — Remove all filters, restore original data
5. "theme" — Switch dark/light mode
6. "answer" — Answer a question about the data without changing charts

RESPONSE FORMAT (reply ONLY with this JSON):
{{
  "action": "create_chart|change_chart|filter|reset_filter|theme|answer",
  "reply": "Your friendly response — MUST BE ENTIRELY IN {language}",
  "detected_language": "{language}",
  "charts": [
    {{
      "chart_type": "bar|line|area|pie|scatter|table",
      "x_column": "exact_column_name",
      "y_column": "exact_column_name",
      "aggregation": "sum|mean|count|median",
      "top_k": 10,
      "title": "Simple clear title"
    }}
  ],
  "chart_index": 0,
  "new_chart_type": "bar|pie|line|area|scatter",
  "filter_column": "",
  "filter_value": "",
  "theme": "dark|light"
}}

RULES:
- For "create_chart": fill the "charts" array with 1-4 chart specs. These REPLACE current charts.
- For "change_chart": set "chart_index" and "new_chart_type" to modify one existing chart.
- For "filter": set "filter_column" and "filter_value". Charts will auto-regenerate.
- For "answer": just set "reply" with your answer. No chart changes needed.
- Column names MUST exactly match the dataset columns.
- Titles should be simple and friendly (understandable by a 15-year-old).
- Reply text should be warm, helpful, and conversational.

## FINAL LANGUAGE CHECK
Before returning your response, verify: Is the "reply" field written ENTIRELY in **{language}**?
If {language} is Hindi, the reply must be in Hindi (Devanagari script).
If {language} is Marathi, the reply must be in Marathi (Devanagari script).
If {language} is Tamil, the reply must be in Tamil script.
Do NOT mix English words into the reply unless no {language} equivalent exists.
"""
        result = self._call_gemini_json(prompt)

        action = result.get("action", "answer")
        reply = result.get("reply", "Done! 👍")
        detected_language = result.get("detected_language", language)

        # ===== ACTION HANDLING =====
        if action == "create_chart":
            chart_specs = result.get("charts", [])
            if chart_specs:
                new_charts = []
                for spec in chart_specs[:6]:
                    chart = self.viz_engine.build_chart_from_spec(df, spec)
                    if chart:
                        if spec.get("title"):
                            chart["title"] = spec["title"]
                        new_charts.append(chart)
                if new_charts:
                    page = session["pages"][session["active_page_idx"]]
                    page["charts"] = new_charts

        elif action == "change_chart":
            charts = session["pages"][session["active_page_idx"]]["charts"]
            idx = result.get("chart_index", 0)
            new_type = result.get("new_chart_type", "bar")
            if 0 <= idx < len(charts):
                old_chart = charts[idx]
                # Rebuild with new type, same data columns
                spec = {
                    "chart_type": new_type,
                    "x_column": old_chart.get("xAxis", ""),
                    "y_column": old_chart.get("dataKey", ""),
                    "title": old_chart.get("title", ""),
                    "aggregation": "sum",
                    "top_k": 10,
                }
                new_chart = self.viz_engine.build_chart_from_spec(df, spec)
                if new_chart:
                    charts[idx] = new_chart

        elif action == "filter":
            col = result.get("filter_column")
            val = result.get("filter_value")
            if col and val and col in session["original_df"].columns:
                filtered = session["original_df"][
                    session["original_df"][col].astype(str).str.contains(str(val), case=False, na=False)
                ]
                if not filtered.empty:
                    session["df"] = filtered
                    session["profiles"] = profile_columns(filtered)
                    new_charts, new_kpis = self.viz_engine.generate_dashboard(filtered)
                    page = session["pages"][session["active_page_idx"]]
                    page["charts"] = new_charts
                    page["kpis"] = new_kpis

        elif action == "reset_filter":
            session["df"] = session["original_df"].copy()
            session["profiles"] = profile_columns(session["df"])
            new_charts, new_kpis = self.viz_engine.generate_dashboard(session["df"])
            page = session["pages"][session["active_page_idx"]]
            page["charts"] = new_charts
            page["kpis"] = new_kpis

        elif action == "theme":
            session["theme"] = result.get("theme", "light")

        # "answer" action: just reply, no changes

        return self._wrap_response(session, reply, detected_language=detected_language)

    # ================= LOCAL FALLBACK =================
    def _process_local_advanced(self, session, message):
        msg = message.lower()

        if "dark" in msg:
            session["theme"] = "dark"
            return self._wrap_response(session, "Dark mode enabled 🌙")

        if "light" in msg:
            session["theme"] = "light"
            return self._wrap_response(session, "Light mode enabled ☀️")

        if "reset" in msg or "original" in msg:
            session["df"] = session["original_df"].copy()
            session["profiles"] = profile_columns(session["df"])
            new_charts, new_kpis = self.viz_engine.generate_dashboard(session["df"])
            page = session["pages"][session["active_page_idx"]]
            page["charts"] = new_charts
            page["kpis"] = new_kpis
            return self._wrap_response(session, "Dashboard reset to original data ✅")

        return self._wrap_response(session, "I can help you explore your data! Try asking me to 'show sales by region', 'change chart to pie', or 'filter for 2023'. 💡")

    # ================= HELPERS =================
    def _wrap_response(self, session, reply, detected_language=None):
        active_page = session["pages"][session["active_page_idx"]]
        response = {
            "charts": active_page["charts"],
            "kpis": active_page["kpis"],
            "slicers": session["slicers"],
            "pages": session["pages"],
            "theme": session["theme"],
            "active_page_idx": session["active_page_idx"],
            "reply": reply,
            "success": True
        }
        if detected_language:
            response["detected_language"] = detected_language
        return response

    def _build_column_info(self, df, profiles):
        """Build a concise column summary for Gemini prompts."""
        lines = []
        for p in profiles[:30]:
            extras = []
            if p.role == "numeric":
                s = df[p.name].dropna()
                if len(s) > 0:
                    extras.append(f"min={s.min():.2f}, max={s.max():.2f}, mean={s.mean():.2f}")
            elif p.role == "categorical":
                top_vals = df[p.name].value_counts().head(3).index.tolist()
                extras.append(f"top values: {', '.join(str(v) for v in top_vals)}")
            elif p.role == "temporal":
                s = pd.to_datetime(df[p.name], errors="coerce").dropna()
                if len(s) > 0:
                    extras.append(f"range: {s.min().strftime('%Y-%m-%d')} to {s.max().strftime('%Y-%m-%d')}")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            lines.append(f"  - {p.name} ({p.role}, {p.nunique} unique){extra_str}")
        return "\n".join(lines)

    def _generate_slicers(self, df):
        slicers = []
        for col in df.columns:
            unique_vals = df[col].dropna().astype(str).unique().tolist()
            if 1 < len(unique_vals) <= 50:
                slicers.append({
                    "column": col,
                    "options": sorted(unique_vals[:20]),
                    "active": None
                })
        return slicers[:10]