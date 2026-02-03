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

# Gemini for multilingual LLM support
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Run: pip install google-generativeai")

class DashboardAgent:
    def __init__(self):
        self.sessions = {}
        self.gemini_enabled = False
        
        # Initialize Gemini for multilingual support
        try:
            if GEMINI_AVAILABLE and os.environ.get("GEMINI_API_KEY"):
                genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                self.gemini_enabled = True
                print("Dashboard Agent: Gemini AI enabled for multilingual support")
            else:
                print("Dashboard Agent: Gemini not configured, using local engine")
        except Exception as e:
            print(f"Gemini initialization failed: {e}")
            self.gemini_enabled = False

    def start_session(self, df: pd.DataFrame):
        session_id = str(uuid.uuid4())
        charts = self._generate_initial_charts(df)
        kpis = self._generate_kpi_cards(df)
        slicers = self._generate_slicers(df)
        
        # Initial Page 1
        pages = [
            {"id": "page1", "name": "Overview", "charts": charts, "kpis": kpis}
        ]
        
        self.sessions[session_id] = {
            "df": df,
            "original_df": df.copy(), # Keep for resetting filters
            "active_page_idx": 0,
            "pages": pages,
            "slicers": slicers,
            "history": [],
            "last_active_chart_idx": 0 if charts else None,
            "theme": "light" # Default theme
        }
        return session_id, charts, kpis, df.columns.tolist(), slicers, pages

    def _generate_slicers(self, df):
        """Identify columns suitable for global filtering (Broad detection)"""
        slicers = []
        all_cols = df.columns.tolist()
        print(f"DEBUG: Generating slicers for {len(all_cols)} columns...")
        
        for col in all_cols:
            # Skip floating point metrics (usually too many unique values)
            if pd.api.types.is_float_dtype(df[col]):
                continue
                
            unique_vals = [str(v) for v in df[col].dropna().unique().tolist()]
            count = len(unique_vals)
            
            # Relaxed cardinality to 100 for large datasets
            if 1 < count <= 100:
                print(f"DEBUG: Slicer found: {col} ({count} options)")
                slicers.append({
                    "column": col,
                    "options": sorted(unique_vals[:50]), # Limit dropdown UI size
                    "active": None 
                })
            else:
                print(f"DEBUG: Skipping {col} as slicer (Cardinality: {count})")
                
            if len(slicers) >= 12: break # Show up to 12 filters
            
        print(f"DEBUG: Total slicers generated: {len(slicers)}")
        return slicers

    def get_session(self, session_id):
        return self.sessions.get(session_id)
        
    def _generate_kpi_cards(self, df):
        """Generate high-impact summary cards with integrated analytical measures"""
        kpis = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        date_col = self._find_date_column(df)
        
        # Filter out columns that look like IDs (e.g., ORDERNUMBER, ID, UUID)
        real_metrics = [
            col for col in numeric_cols 
            if not any(k in col.upper() for k in ["ID", "NUMBER", "CODE", "PHONE", "ZIP", "INDEX"])
        ]
        
        # 1. Primary Growth Metric (MoM if dates exist)
        if date_col and real_metrics:
            primary_num = real_metrics[0]
            measures = self._calculate_advanced_measures(df, date_col, primary_num)
            if measures:
                kpis.append({"title": f"{primary_num} (MTD)", "value": f"{measures['mtd']:,.0f}", "change": f"{measures['mom_growth']:+.1f}%"})
                kpis.append({"title": f"{primary_num} (YTD)", "value": f"{measures['ytd']:,.0f}", "change": "Year-to-Date"})

        # 2. Key Numeric Averages / Totals
        for col in real_metrics[:2]:
            if len(kpis) >= 4: break
            avg = df[col].mean()
            val_str = self._format_value(avg)
            kpis.append({"title": f"Avg {col}", "value": val_str, "change": "Metric"})
            
        # 3. Fallback: Total Records if grid not full
        if len(kpis) < 4:
            kpis.append({"title": "Total Records", "value": f"{len(df):,}", "change": "Dataset Size"})
            
        return kpis[:4]

    def _format_value(self, val):
        if val > 1_000_000_000: return f"{val/1_000_000_000:.1f}B"
        if val > 1_000_000: return f"{val/1_000_000:.1f}M"
        if val > 1_000: return f"{val/1_000:.1f}K"
        return f"{val:.1f}" if val != int(val) else f"{int(val)}"

    def _find_date_column(self, df):
        """Identify the most likely date/time column for analysis"""
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['date', 'time', 'year', 'month', 'timestamp', 'dt']):
                # Try to convert to datetime to verify
                try:
                    pd.to_datetime(df[col].iloc[:5], errors='raise')
                    return col
                except:
                    continue
        return None

    def _calculate_advanced_measures(self, df, date_col, num_col):
        """Calculate professional BI metrics: MTD, YTD, MoM%"""
        try:
            temp_df = df[[date_col, num_col]].copy()
            temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
            temp_df = temp_df.dropna(subset=[date_col])
            
            if temp_df.empty: return None
            
            latest_date = temp_df[date_col].max()
            current_month = latest_date.month
            current_year = latest_date.year
            
            mtd = temp_df[(temp_df[date_col].dt.month == current_month) & (temp_df[date_col].dt.year == current_year)][num_col].sum()
            ytd = temp_df[temp_df[date_col].dt.year == current_year][num_col].sum()
            
            # Prev Month
            prev_m_date = latest_date - pd.DateOffset(months=1)
            prev_mtd = temp_df[(temp_df[date_col].dt.month == prev_m_date.month) & (temp_df[date_col].dt.year == prev_m_date.year)][num_col].sum()
            
            mom_growth = ((mtd - prev_mtd) / prev_mtd * 100) if prev_mtd != 0 else 0
            
            return {"mtd": mtd, "ytd": ytd, "mom_growth": mom_growth}
        except:
            return None

    def process_prompt(self, session_id, message):
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "reply": "Session not found", "charts": None}

        # 1. Try Gemini for multilingual support
        if self.gemini_enabled:
            try:
                return self._process_with_gemini(session, message)
            except Exception as e:
                print(f"Gemini Failed, falling back to local: {e}")
        
        # 2. Local Advanced Engine (fallback)
        return self._process_local_advanced(session, message)

    def _process_with_gemini(self, session, message):
        """Process user message using Gemini AI for multilingual support.
        
        Supports all languages including regional Indian languages like:
        - Marathi (मराठी)
        - Gujarati (ગુજરાતી)
        - Hindi (हिंदी)
        - Tamil (தமிழ்)
        - Telugu (తెలుగు)
        - Bengali (বাংলা)
        - And many more...
        """
        df = session["df"]
        cols = session["original_df"].columns.tolist()
        slicers = session.get("slicers", [])
        
        # Build context about available data
        slicer_info = ", ".join([f"{s['column']} (options: {', '.join(s['options'][:5])})" for s in slicers[:5]])
        
        system_prompt = f"""You are a multilingual BI Dashboard Assistant. You help users interact with their data dashboard.

IMPORTANT: Always respond in the SAME LANGUAGE as the user's message. If they write in Marathi, respond in Marathi. If they write in Gujarati, respond in Gujarati. If they write in English, respond in English.

Available columns in the dataset: {', '.join(cols[:20])}
Available filters: {slicer_info if slicer_info else 'None'}

You can help users with:
1. Changing chart types (bar, pie, line, area, scatter, table)
2. Applying filters to the data
3. Switching between dark/light themes
4. Understanding their data

Based on the user's request, respond with a JSON object containing:
{{
    "action": "filter" | "change_chart" | "theme" | "info" | "none",
    "chart_type": "bar" | "pie" | "line" | "area" | "scatter" | "table" (only if action is change_chart),
    "filter_column": "column_name" (only if action is filter),
    "filter_value": "value" (only if action is filter),
    "theme": "dark" | "light" (only if action is theme),
    "reply": "Your helpful response in the user's language"
}}

Respond ONLY with the JSON object, no other text."""

        try:
            response = self.gemini_model.generate_content(
                f"{system_prompt}\n\nUser message: {message}"
            )
            
            response_text = response.text.strip()
            # Clean up markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            action = result.get("action", "none")
            reply = result.get("reply", "I'm here to help!")
            
            # Execute the requested action
            if action == "theme":
                theme = result.get("theme", "light")
                session["theme"] = theme
                
            elif action == "change_chart":
                chart_type = result.get("chart_type", "bar")
                charts = session["pages"][session["active_page_idx"]]["charts"]
                target_idx = session.get("last_active_chart_idx", 0)
                if 0 <= target_idx < len(charts):
                    charts[target_idx]["type"] = chart_type
                    
            elif action == "filter":
                filter_col = result.get("filter_column")
                filter_val = result.get("filter_value")
                if filter_col and filter_val:
                    # Apply filter
                    try:
                        session["df"] = session["original_df"][session["original_df"][filter_col].astype(str) == str(filter_val)]
                        for s in session["slicers"]:
                            if s["column"] == filter_col:
                                s["active"] = filter_val
                        # Regenerate charts with filtered data
                        active_idx = session["active_page_idx"]
                        session["pages"][active_idx]["charts"] = self._generate_initial_charts(session["df"])
                        session["pages"][active_idx]["kpis"] = self._generate_kpi_cards(session["df"])
                    except Exception as e:
                        print(f"Filter error: {e}")
            
            return self._wrap_response(session, reply)
            
        except json.JSONDecodeError as e:
            print(f"Gemini JSON parse error: {e}")
            # If JSON parsing fails, try to extract a simple response
            try:
                response = self.gemini_model.generate_content(
                    f"You are a helpful multilingual assistant. Respond to this message in the same language it was written: {message}"
                )
                return self._wrap_response(session, response.text.strip())
            except:
                raise
        except Exception as e:
            print(f"Gemini processing error: {e}")
            raise



    def _process_local_advanced(self, session, message):
        df = session["df"]
        msg = message.lower()
        
        # --- A. Global Commands (Theme, Pages, Filters) ---
        if "dark mode" in msg or ("theme" in msg and "dark" in msg):
            session["theme"] = "dark"
            return self._wrap_response(session, "I've switched the dashboard to a premium Dark Mode. Do you like this look?")

        if "light mode" in msg or ("theme" in msg and "light" in msg):
            session["theme"] = "light"
            return self._wrap_response(session, "Switched back to a crisp Light Mode for better clarity.")

        # Page Switching
        for i, page in enumerate(session["pages"]):
            if page["name"].lower() in msg or f"page {i+1}" in msg:
                session["active_page_idx"] = i
                return self._wrap_response(session, f"Navigating to the '{page['name']}' page.")

        # --- B. Entity Extraction ---
        mentioned_cols = []
        cols = session["original_df"].columns.tolist()
        for col in cols:
            clean_name = col.lower().replace('_', ' ').replace('-', ' ')
            if clean_name in msg: mentioned_cols.append(col)

        # Filters / Slicing
        # "Filter by USA", "Show only Planes"
        if any(w in msg for w in ["filter", "only show", "where"]):
            for s in session["slicers"]:
                for opt in s["options"]:
                    if str(opt).lower() in msg:
                        # Apply Filter
                        session["df"] = session["original_df"][session["original_df"][s["column"]] == opt]
                        s["active"] = opt
                        # Re-generate current page for filtered context
                        active_idx = session["active_page_idx"]
                        session["pages"][active_idx]["charts"] = self._generate_initial_charts(session["df"])
                        session["pages"][active_idx]["kpis"] = self._generate_kpi_cards(session["df"])
                        return self._wrap_response(session, f"I've filtered all reports to show context for '{opt}'.")

        # Reset filters
        if "all data" in msg or "reset filter" in msg or "show everything" in msg:
            session["df"] = session["original_df"].copy()
            for s in session["slicers"]: s["active"] = None
            active_idx = session["active_page_idx"]
            session["pages"][active_idx]["charts"] = self._generate_initial_charts(session["df"])
            session["pages"][active_idx]["kpis"] = self._generate_kpi_cards(session["df"])
            return self._wrap_response(session, "Cleared all global filters. Showing the full dataset again.")

        # --- C. Visual Modifications (Standard Chart Logic) ---
        charts = session["pages"][session["active_page_idx"]]["charts"]
        
        # Intent: UPDATE
        if any(w in msg for w in ["change", "switch", "convert", "turn into", "make it", "update", "this"]):
            target_type = None
            if "pie" in msg or "donut" in msg: target_type = "pie"
            elif "bar" in msg: target_type = "bar"
            elif "line" in msg: target_type = "line"
            elif "area" in msg: target_type = "area"
            elif "scatter" in msg: target_type = "scatter"
            elif "table" in msg: target_type = "table"
            
            if target_type:
                target_idx = session.get("last_active_chart_idx", 0)
                if 0 <= target_idx < len(charts):
                    current_chart = charts[target_idx]
                    current_chart["type"] = target_type
                    return self._wrap_response(session, f"Updated '{current_chart['title']}' to a {target_type.title()} view.")
            
        # Intent: CREATE
        elif any(w in msg for w in ["add", "create", "show", "give me", "new", "another"]) or mentioned_cols:
            req_type = "bar"
            if "pie" in msg: req_type = "pie"
            elif "table" in msg: req_type = "table"
            elif "scatter" in msg: req_type = "scatter"
            
            new_chart = self._create_smart_chart(session["df"], mentioned_cols or [cols[0]], preferred_type=req_type)
            if new_chart:
                charts.append(new_chart)
                session["last_active_chart_idx"] = len(charts) - 1
                return self._wrap_response(session, f"Added a professional {req_type} visual for {', '.join(mentioned_cols or ['data'])}.")

        return self._wrap_response(session, "I'm standing by to help you pivot data, add visuals, or apply global filters.")

    def _wrap_response(self, session, reply):
        """Standard wrapper to sync session state with frontend expectations"""
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
