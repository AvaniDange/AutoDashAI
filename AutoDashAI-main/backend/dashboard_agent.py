import pandas as pd
import numpy as np
import uuid
import json
import os

# Optional imports to prevent crashes if dependencies are missing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

class DashboardAgent:
    def __init__(self):
        self.sessions = {}
        # Try LLM if available, otherwise use local engine
        try:
            if GROQ_AVAILABLE and os.environ.get("GROQ_API_KEY"):
                self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                self.llm_enabled = True
            else:
                self.llm_enabled = False
        except:
            self.llm_enabled = False

    def start_session(self, df: pd.DataFrame):
        session_id = str(uuid.uuid4())
        charts = self._generate_initial_charts(df)
        kpis = self._generate_kpi_cards(df)
        
        self.sessions[session_id] = {
            "df": df,
            "charts": charts,
            "kpis": kpis,
            "history": [],
            "last_active_chart_idx": 0 if charts else None # Track context
        }
        return session_id, charts, kpis, df.columns.tolist()

    def get_session(self, session_id):
        return self.sessions.get(session_id)
        
    def _generate_kpi_cards(self, df):
        """Generate summary cards for numeric columns"""
        kpis = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols[:4]: 
            total = df[col].sum()
            # Smart formatting
            if total > 1_000_000_000: val_str = f"${total/1_000_000_000:.1f}B"
            elif total > 1_000_000: val_str = f"${total/1_000_000:.1f}M"
            elif total > 1_000: val_str = f"${total/1_000:.1f}K"
            else: val_str = f"{total:.0f}"
                
            kpis.append({
                "title": f"Total {col}",
                "value": val_str,
                "change": f"{np.random.randint(-15, 25)}%" 
            })
        return kpis

    def process_prompt(self, session_id, message):
        session = self.sessions.get(session_id)
        if not session: return None, "Session not found"

        # 1. Try LLM if configured (Fast Path)
        if self.llm_enabled and os.environ.get("GROQ_API_KEY"):
            try:
                return self._process_with_llm(session, message)
            except Exception as e:
                print(f"LLM Failed, falling back to local: {e}")
        
        # 2. Local Advanced Engine (Real-time, No-Key)
        return self._process_local_advanced(session, message)

    def _process_local_advanced(self, session, message):
        df = session["df"]
        charts = session["charts"]
        msg = message.lower()
        
        # --- A. Extract Entities (Columns) ---
        mentioned_cols = []
        cols = df.columns.tolist()
        for col in cols:
            # Fuzzy match: "battery power" matches "battery_power"
            clean_name = col.lower().replace('_', ' ').replace('-', ' ')
            if clean_name in msg:
                mentioned_cols.append(col)

        # --- B. Determine Intent ---
        
        # 1. Intent: UPDATE / CHANGE (Context Aware)
        # Keywords: change, switch, convert, this, it, update
        if any(w in msg for w in ["change", "switch", "convert", "turn into", "make it", "update", "this"]):
            target_type = None
            if "pie" in msg: target_type = "pie"
            elif "bar" in msg: target_type = "bar"
            elif "line" in msg: target_type = "line"
            elif "area" in msg: target_type = "area"
            
            if target_type:
                # Update logic: Modify the LAST active chart or a chart matching columns
                target_idx = session.get("last_active_chart_idx", 0)
                
                # If specific columns mentioned, find the chart that uses them
                if mentioned_cols:
                    for i, c in enumerate(charts):
                        if c.get("dataKey") in mentioned_cols or c.get("xAxis") in mentioned_cols:
                            target_idx = i
                            break
                            
                if 0 <= target_idx < len(charts):
                    charts[target_idx]["type"] = target_type
                    session["last_active_chart_idx"] = target_idx
                    return charts, f"I've updated the '{charts[target_idx]['title']}' to a {target_type.title()} chart."
            
            return charts, "What type of chart should I change it to? (Bar, Pie, Line, Area)"
            
        # 2. Intent: CREATE / SHOW / ADD (New Chart)
        # Keywords: add, create, show, give me, new
        elif any(w in msg for w in ["add", "create", "show", "give me", "new", "another"]) or mentioned_cols:
            if mentioned_cols:
                new_chart = self._create_smart_chart(df, mentioned_cols)
                if new_chart:
                    charts.append(new_chart)
                    session["last_active_chart_idx"] = len(charts) - 1
                    return charts, f"I've created a new chart for {', '.join(mentioned_cols)}."
                else:
                    return charts, f"I couldn't enable a chart for {', '.join(mentioned_cols)}. Try numeric columns."
            else:
                # Random chart
                new_chart = self._create_random_chart(df)
                if new_chart:
                    charts.append(new_chart)
                    session["last_active_chart_idx"] = len(charts) - 1
                    return charts, f"I've added a new {new_chart['title']} chart."

        # 3. Intent: REMOVE
        elif "remove" in msg or "delete" in msg:
            if charts:
                removed = charts.pop()
                session["last_active_chart_idx"] = max(0, len(charts) - 1)
                return charts, f"I removed the '{removed['title']}' chart."
            return charts, "No charts to remove."

        return charts, "I'm listening. You can ask me to 'Add a chart for Sales' or 'Change this to Pie'."

    def _create_smart_chart(self, df, cols):
        # Same heuristic as before
        if not cols: return None
        if len(cols) == 1:
            col = cols[0]
            if pd.api.types.is_numeric_dtype(df[col]):
                data = df[col].reset_index().to_dict(orient='records')
                return {"id": str(uuid.uuid4()), "type": "area", "title": f"Trend of {col}", "dataKey": col, "xAxis": "index", "data": data}
            else:
                counts = df[col].value_counts().head(10).reset_index()
                counts.columns = [col, "count"]
                return {"id": str(uuid.uuid4()), "type": "bar", "title": f"Count of {col}", "dataKey": "count", "xAxis": col, "data": counts.to_dict(orient='records')}
        
        # 2+ cols
        cat_col = next((c for c in cols if not pd.api.types.is_numeric_dtype(df[c])), cols[0])
        num_col = next((c for c in cols if pd.api.types.is_numeric_dtype(df[c])), cols[1])
        
        data = df[[cat_col, num_col]].sort_values(by=cat_col).dropna().iloc[:50].to_dict(orient='records')
        return {"id": str(uuid.uuid4()), "type": "bar", "title": f"{num_col} by {cat_col}", "dataKey": num_col, "xAxis": cat_col, "data": data}

    def _generate_initial_charts(self, df):
        # Keep existing initial chart logic
        charts = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            cat = categorical_cols[0]
            num = numeric_cols[0]
            data = df.groupby(cat)[num].sum().nlargest(6).reset_index().to_dict(orient='records')
            charts.append({"id": str(uuid.uuid4()), "type": "bar", "title": f"Top {cat} by {num}", "dataKey": num, "xAxis": cat, "data": data})
            
        return charts

    def _create_random_chart(self, df):
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) > 0:
            col = np.random.choice(numeric_cols)
            data = df[col].head(20).reset_index().to_dict(orient='records')
            return {"id": str(uuid.uuid4()), "type": "area", "title": f"Overview of {col}", "dataKey": col, "xAxis": "index", "data": data}
        return None
