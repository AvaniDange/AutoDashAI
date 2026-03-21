import pandas as pd
import numpy as np
import uuid
import json
import os
import traceback

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Gemini SDK
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Install with: pip install google-genai")

from backend.visualization_engine import VisualizationEngine, profile_columns


class DashboardAgent:
    def __init__(self):
        self.sessions = {}
        self.gemini_enabled = False
        self.viz_engine = VisualizationEngine()

        # Initialize Gemini
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if GEMINI_AVAILABLE and api_key:
                self.client = genai.Client(api_key=api_key)
                self.gemini_enabled = True
                print("✅ Gemini (google-genai) enabled")
            else:
                print("⚠️ Gemini not configured — using local engine only")
        except Exception as e:
            print(f"❌ Gemini init error: {e}")

    # ================= GEMINI HELPERS =================
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and return cleaned text."""
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        text = response.text.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return text

    def _call_gemini_json(self, prompt: str) -> dict:
        """Call Gemini and parse JSON response."""
        text = self._call_gemini(prompt)
        return json.loads(text)

    # ================= SESSION START =================
    def start_session(self, df: pd.DataFrame):
        session_id = str(uuid.uuid4())
        profiles = profile_columns(df)

        # --- Gemini Pre-Analysis: let AI suggest optimal charts ---
        charts, kpis = self._gemini_pre_analysis(df, profiles)

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
        }

        return session_id, charts, kpis, df.columns.tolist(), slicers, pages

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    # ================= GEMINI PRE-ANALYSIS =================
    def _gemini_pre_analysis(self, df, profiles):
        """
        Ask Gemini to analyze the dataset and suggest the best charts.
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
            result = self._call_gemini_json(prompt)

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
            print(f"✅ Gemini pre-analysis: {len(charts)} charts generated")
            return charts, kpis

        except Exception as e:
            print(f"⚠️ Gemini pre-analysis failed ({e}), using local engine")
            traceback.print_exc()
            return self.viz_engine.generate_dashboard(df)

    # ================= CHAT PROCESSING =================
    def process_prompt(self, session_id, message):
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "reply": "Session not found", "charts": None}

        # Add to history
        session["history"].append({"role": "user", "content": message})

        if self.gemini_enabled:
            try:
                result = self._process_with_gemini(session, message)
                session["history"].append({"role": "assistant", "content": result.get("reply", "")})
                return result
            except Exception as e:
                print(f"Gemini chat failed → fallback: {e}")
                traceback.print_exc()

        result = self._process_local_advanced(session, message)
        session["history"].append({"role": "assistant", "content": result.get("reply", "")})
        return result

    def _process_with_gemini(self, session, message):
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

        prompt = f"""You are an intelligent BI dashboard assistant. You help users explore their data by creating and modifying visualizations.

DATASET ({len(df)} rows, {len(df.columns)} columns):
{col_info}

CURRENT CHARTS:
{chart_summary}

AVAILABLE FILTERS: {slicer_info if slicer_info else 'None'}

RECENT CONVERSATION:
{history_text}

USER REQUEST: {message}

Understand the user's intent and respond with a JSON object. You MUST respond in the SAME LANGUAGE as the user.

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
  "reply": "Your friendly response to the user (SAME LANGUAGE as user)",
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
- Always reply in the SAME language the user used.
"""
        result = self._call_gemini_json(prompt)

        action = result.get("action", "answer")
        reply = result.get("reply", "Done! 👍")

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

        return self._wrap_response(session, reply)

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
    def _wrap_response(self, session, reply):
        active_page = session["pages"][session["active_page_idx"]]
        return {
            "charts": active_page["charts"],
            "kpis": active_page["kpis"],
            "slicers": session["slicers"],
            "pages": session["pages"],
            "theme": session["theme"],
            "active_page_idx": session["active_page_idx"],
            "reply": reply,
            "success": True
        }

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