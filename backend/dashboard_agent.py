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
        """Generate summary cards for numeric columns (Smart & Generic)"""
        kpis = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 1. Total Records (Generic)
        kpis.append({"title": "Total Records", "value": f"{len(df):,}", "change": "Dataset Size"})
        
        # 2. Key Numeric Metrics
        for col in numeric_cols[:3]: 
            avg = df[col].mean()
            if avg > 1000:
                val = df[col].sum()
                title = f"Total {col}"
            else:
                val = avg
                title = f"Avg {col}"
                
            if val > 1_000_000_000: val_str = f"{val/1_000_000_000:.1f}B"
            elif val > 1_000_000: val_str = f"{val/1_000_000:.1f}M"
            elif val > 1_000: val_str = f"{val/1_000:.1f}K"
            elif val == int(val): val_str = f"{int(val)}"
            else: val_str = f"{val:.2f}"
                
            kpis.append({"title": title, "value": val_str, "change": f"{np.random.randint(-5, 10)}%"})
        return kpis[:4]

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
                target_idx = session.get("last_active_chart_idx", 0)
                if mentioned_cols:
                    for i, c in enumerate(charts):
                        if c.get("dataKey") in mentioned_cols or c.get("xAxis") in mentioned_cols:
                            target_idx = i
                            break
                            
                if 0 <= target_idx < len(charts):
                    current_chart = charts[target_idx]
                    
                    # Smart Conversion for Pie
                    if target_type == "pie" and current_chart["type"] != "pie":
                        # Attempt to re-generate from scratch with the same columns for better aggregation
                        cols_to_use = []
                        if current_chart.get("xAxis") and current_chart["xAxis"] != "index":
                            cols_to_use.append(current_chart["xAxis"])
                        if current_chart.get("dataKey"):
                            cols_to_use.append(current_chart["dataKey"])
                        
                        if cols_to_use:
                            new_p = self._create_smart_chart(df, cols_to_use, preferred_type="pie")
                            if new_p:
                                charts[target_idx] = new_p
                                return charts, f"I've converted '{current_chart['title']}' to a Pie chart with aggregated data."
                    
                    current_chart["type"] = target_type
                    session["last_active_chart_idx"] = target_idx
                    return charts, f"I've updated the '{current_chart['title']}' to a {target_type.title()} chart."
            
            return charts, "What type of chart should I change it to? (Bar, Pie, Line, Area)"
            
        # 2. Intent: CREATE / SHOW / ADD (New Chart)
        # Keywords: add, create, show, give me, new
        elif any(w in msg for w in ["add", "create", "show", "give me", "new", "another"]) or mentioned_cols:
            # Detect requested type
            req_type = None
            if "pie" in msg: req_type = "pie"
            elif "bar" in msg: req_type = "bar"
            elif "line" in msg: req_type = "line"
            elif "area" in msg: req_type = "area"

            if mentioned_cols:
                new_chart = self._create_smart_chart(df, mentioned_cols, preferred_type=req_type)
                if new_chart:
                    charts.append(new_chart)
                    session["last_active_chart_idx"] = len(charts) - 1
                    return charts, f"I've created a new {new_chart['type'].title()} chart for {', '.join(mentioned_cols)}."
                else:
                    return charts, f"I couldn't enable a chart for {', '.join(mentioned_cols)}. Try numeric columns."
            else:
                # Random chart but respect type
                new_chart = self._create_random_chart(df, preferred_type=req_type)
                if new_chart:
                    charts.append(new_chart)
                    session["last_active_chart_idx"] = len(charts) - 1
                    return charts, f"I've added a new {new_chart['title']} ({new_chart['type']})."

        # 3. Intent: REMOVE
        elif "remove" in msg or "delete" in msg:
            if charts:
                removed = charts.pop()
                session["last_active_chart_idx"] = max(0, len(charts) - 1)
                return charts, f"I removed the '{removed['title']}' chart."
            return charts, "No charts to remove."

        return charts, "I'm listening. You can ask me to 'Add a chart for Sales' or 'Change this to Pie'."

    def _create_smart_chart(self, df, cols, preferred_type=None):
        """Create a chart with sampled data to prevent UI lag"""
        if not cols: return None
        
        # Limit the amount of data we send to the frontend
        MAX_POINTS = 100
        
        if len(cols) == 1:
            col = cols[0]
            if pd.api.types.is_numeric_dtype(df[col]):
                # Sample for trend/area chart
                data_sampled = df[col].reset_index()
                if len(data_sampled) > MAX_POINTS:
                    data_sampled = data_sampled.iloc[::max(1, len(data_sampled)//MAX_POINTS)]
                
                ctype = preferred_type if preferred_type else "area"
                return {
                    "id": str(uuid.uuid4()), 
                    "type": ctype, 
                    "title": f"Distribution of {col}", 
                    "dataKey": col, 
                    "xAxis": "index", 
                    "data": data_sampled.head(MAX_POINTS).to_dict(orient='records')
                }
            else:
                counts = df[col].value_counts().head(10).reset_index()
                counts.columns = [col, "count"]
                ctype = preferred_type if preferred_type else "bar"
                return {
                    "id": str(uuid.uuid4()), 
                    "type": ctype, 
                    "title": f"Count of {col}", 
                    "dataKey": "count", 
                    "xAxis": col, 
                    "data": counts.to_dict(orient='records')
                }
        
        # 2+ cols: Try to find a categorical and a numeric column
        cat_cols = df[cols].select_dtypes(exclude=[np.number]).columns.tolist()
        num_cols = df[cols].select_dtypes(include=[np.number]).columns.tolist()
        
        cat_col = cat_cols[0] if cat_cols else cols[0]
        num_col = num_cols[0] if num_cols else (cols[1] if len(cols) > 1 else cols[0])
        
        ctype = preferred_type if preferred_type else "bar"

        # Group if categorical, otherwise sample
        if cat_col in cat_cols or ctype == "pie":
            data = df.groupby(cat_col)[num_col].mean().reset_index()
            data = data.nlargest(10, num_col)
        else:
            data = df[[cat_col, num_col]].dropna().iloc[:MAX_POINTS]
            
        return {
            "id": str(uuid.uuid4()), 
            "type": ctype, 
            "title": f"{num_col} by {cat_col}", 
            "dataKey": num_col, 
            "xAxis": cat_col, 
            "data": data.to_dict(orient='records')
        }

    def _generate_initial_charts(self, df):
        """Generate a diverse set of initial charts (max 4)"""
        charts = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        # 1. Main categorical breakdown
        if categorical_cols and numeric_cols:
            cat = categorical_cols[0]
            num = numeric_cols[0]
            data = df.groupby(cat)[num].sum().nlargest(6).reset_index().to_dict(orient='records')
            charts.append({"id": str(uuid.uuid4()), "type": "bar", "title": f"Total {num} by {cat}", "dataKey": num, "xAxis": cat, "data": data})

        # 2. Add some automated area charts for numeric trends
        for col in numeric_cols[:2]:
            # Sample for performance
            sample_df = df[col].reset_index()
            if len(sample_df) > 100:
                sample_df = sample_df.iloc[::max(1, len(sample_df)//100)]
            
            charts.append({
                "id": str(uuid.uuid4()), 
                "type": "area", 
                "title": f"{col} Overview", 
                "dataKey": col, 
                "xAxis": "index", 
                "data": sample_df.head(100).to_dict(orient='records')
            })
            
        # 3. Add a pie chart if there's a good categorical column
        if len(categorical_cols) > 1:
            cat = categorical_cols[1]
            counts = df[cat].value_counts().head(5).reset_index()
            counts.columns = [cat, "value"] # Pie likes "value"
            charts.append({"id": str(uuid.uuid4()), "type": "pie", "title": f"Top {cat} Split", "dataKey": "value", "xAxis": cat, "data": counts.to_dict(orient='records')})

        return charts[:4]

    def _create_random_chart(self, df, preferred_type=None):
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        if preferred_type == "pie" and categorical_cols and numeric_cols:
            cat = np.random.choice(categorical_cols)
            num = np.random.choice(numeric_cols)
            data = df.groupby(cat)[num].mean().nlargest(5).reset_index().to_dict(orient='records')
            return {"id": str(uuid.uuid4()), "type": "pie", "title": f"{num} Split", "dataKey": num, "xAxis": cat, "data": data}
            
        if len(numeric_cols) > 0:
            col = np.random.choice(numeric_cols)
            ctype = preferred_type if preferred_type else "area"
            # Sample!
            data = df[col].head(100).reset_index().to_dict(orient='records')
            return {"id": str(uuid.uuid4()), "type": ctype, "title": f"Random View: {col}", "dataKey": col, "xAxis": "index", "data": data}
        return None
