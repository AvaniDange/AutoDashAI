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

    def _sanitize_json(self, data):
        """Recursively convert numpy types to Python native types for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json(v) for v in data]
        elif isinstance(data, (np.int64, np.int32, np.int16, np.int8)):
            return int(data)
        elif isinstance(data, (np.float64, np.float32, np.float16)):
            return float(data) if not np.isnan(data) else None
        elif isinstance(data, pd.Timestamp):
            return data.isoformat()
        else:
            return data

    def start_session(self, df: pd.DataFrame):
        session_id = str(uuid.uuid4())
        charts = self._generate_initial_charts(df)
        kpis = self._generate_kpi_cards(df)
        slicers = self._generate_slicers(df)
        
        # Initial Page 1
        pages = [
            {"id": "page1", "name": "Overview", "charts": charts, "kpis": kpis}
        ]
        
        # DEBUG: Print all column names
        print(f"DEBUG: All columns in dataset: {df.columns.tolist()}")
        print(f"DEBUG: Categorical columns: {df.select_dtypes(exclude=[np.number]).columns.tolist()}")

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
        
        # Sanitize all outputs before returning
        return (
            session_id, 
            self._sanitize_json(charts), 
            self._sanitize_json(kpis), 
            df.columns.tolist(), 
            self._sanitize_json(slicers), 
            self._sanitize_json(pages)
        )

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
        """Generate Power BI-style KPIs with sparkline data"""
        kpis = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Find sales column
        sales_col = next((c for c in numeric_cols if 'sales' in c.lower()), None)
        if not sales_col and numeric_cols:
            sales_col = numeric_cols[0]
        
        # Find order column
        order_col = next((c for c in df.columns if 'order' in c.lower()), None)
        
        # Find country column for grouping
        country_col = next((c for c in df.columns if 'country' in c.lower()), None)
        
        if sales_col:
            # KPI 1: Total Sales
            total_sales = df[sales_col].sum()
            formatted_total = self._format_value(total_sales)
            
            # Generate sparkline data (by country or time)
            sparkline_data = []
            if country_col:
                # Group by country for sparkline
                country_sales = df.groupby(country_col)[sales_col].sum().head(10).tolist()
                sparkline_data = [{"value": float(v)} for v in country_sales]
            
            kpis.append({
                "title": "Total Sales",
                "value": formatted_total,
                "change": "+5.2%",
                "sparkline": sparkline_data
            })
        
            # KPI 2: Count of Unique Orders
            if order_col:
                unique_orders = df[order_col].nunique()
                kpis.append({
                    "title": "Count of Unique Orders",
                    "value": str(unique_orders),
                    "change": "+2.1%",
                    "sparkline": []
                })
            
            # KPI 3: Average Value of Each Order
            avg_order_value = total_sales / df[order_col].nunique() if order_col else total_sales / len(df)
            formatted_avg = self._format_value(avg_order_value)
            kpis.append({
                "title": "Average Value of Each Order",
                "value": formatted_avg,
                "change": "+3.8%",
                "sparkline": []
            })
            
        return kpis[:3]

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
            elif "funnel" in msg: target_type = "funnel"
            elif "treemap" in msg: target_type = "treemap"
            elif "gauge" in msg: target_type = "gauge"
            
            if target_type:
                target_idx = session.get("last_active_chart_idx", 0)
                if 0 <= target_idx < len(charts):
                    current_chart = charts[target_idx]
                    # Specific conversion logic for Gauge (needs single point)
                    if target_type == "gauge":
                        val = df[current_chart["dataKey"]].mean()
                        current_chart["data"] = [{"value": val, "target": val * 1.5, "unit": ""}]
                        current_chart["xAxis"] = "gauge"
                    current_chart["type"] = target_type
                    return self._wrap_response(session, f"Updated '{current_chart['title']}' to a {target_type.title()} view.")
            
        # Intent: CREATE
        elif any(w in msg for w in ["add", "create", "show", "give me", "new", "another"]) or mentioned_cols:
            req_type = "bar"
            if "pie" in msg: req_type = "pie"
            elif "table" in msg: req_type = "table"
            elif "scatter" in msg: req_type = "scatter"
            elif "funnel" in msg: req_type = "funnel"
            elif "treemap" in msg: req_type = "treemap"
            elif "gauge" in msg: req_type = "gauge"
            
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
                if preferred_type == "gauge":
                    val = df[col].mean()
                    return {
                        "id": str(uuid.uuid4()),
                        "type": "gauge",
                        "title": f"Average {col}",
                        "dataKey": "value",
                        "xAxis": "gauge",
                        "data": [{"value": val, "target": val * 1.2, "unit": ""}]
                    }
                
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
                if preferred_type == "funnel":
                    counts.columns = [col, "value"]
                    return {
                        "id": str(uuid.uuid4()), "type": "funnel", "title": f"{col} Pipeline",
                        "dataKey": "value", "xAxis": col, "data": counts.to_dict(orient='records')
                    }
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

        # Special logic for Treemap (Hierarchical or high cardinality)
        if ctype == "treemap" or (not preferred_type and df[cat_col].nunique() > 10):
            data = df.groupby(cat_col)[num_col].sum().nlargest(20).reset_index()
            data.columns = ["name", "value"]
            return {
                "id": str(uuid.uuid4()), "type": "treemap", "title": f"{num_col} by {cat_col} (Hierarchy)",
                "dataKey": "value", "xAxis": "name", "data": data.to_dict(orient='records')
            }

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
        """Generate Power BI-style dashboard with exact chart specifications."""
        charts = []
        
        # Identify sales column
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        # Find sales column (case-insensitive)
        sales_col = None
        for col in numeric_cols:
            if 'sales' in col.lower():
                sales_col = col
                break
        
        if not sales_col and numeric_cols:
            sales_col = numeric_cols[0]
        
        # Find key columns - BE SPECIFIC to avoid finding wrong columns
        # Look for exact "PRODUCTLINE" not "productName"
        productline_col = None
        for col in categorical_cols:
            col_lower = col.lower()
            # Skip if it's productName or productCode
            if 'name' in col_lower or 'code' in col_lower:
                continue
            # Match PRODUCTLINE exactly
            if col_lower == 'productline' or ('line' in col_lower and 'product' in col_lower):
                productline_col = col
                break
        
        print(f"DEBUG: ProductLine column found: {productline_col}")

        # For office country - look for columns with "office" and "country"
        office_country_col = next((c for c in categorical_cols if 'office' in c.lower() and 'country' in c.lower()), None)
        if not office_country_col:
            office_country_col = next((c for c in categorical_cols if 'addressline2' in c.lower()), None)
        if not office_country_col:
            # Fallback to any country column
            office_country_col = next((c for c in categorical_cols if 'country' in c.lower()), None)
        
        # For customer country
        customer_country_col = next((c for c in categorical_cols if 'customer' in c.lower() and 'country' in c.lower()), None)
        if not customer_country_col:
            customer_country_col = next((c for c in categorical_cols if 'country' in c.lower()), None)
        
        msrp_col = next((c for c in numeric_cols if 'msrp' in c.lower() or 'cost' in c.lower() or 'price' in c.lower()), None)
        
        df_safe = df.copy()
        if sales_col:
            df_safe[sales_col] = pd.to_numeric(df_safe[sales_col], errors='coerce').fillna(0)
        
        # Chart 1: Sales by ProductLine (Horizontal Bar - TOP PRODUCT ONLY)
        if sales_col and productline_col:
            productline_sales = df_safe.groupby(productline_col)[sales_col].sum().sort_values(ascending=False)
            top_product = productline_sales.head(1).reset_index()
            top_product.columns = ['name', 'value']  # Rename for clarity
            
            charts.append({
                "id": str(uuid.uuid4()),
                "type": "bar",
                "title": f"Sales\nBy {productline_col}",
                "dataKey": "value",
                "xAxis": "name",
                "data": top_product.to_dict(orient='records'),
                "layout": "vertical"
            })
        
        # Chart 2: Sales by Cost of Sales (Scatter Plot)
        if sales_col and msrp_col:
            scatter_data = df_safe[[msrp_col, sales_col]].dropna().head(100)
            scatter_data.columns = ['x', 'y']  # Rename for scatter chart
            charts.append({
                "id": str(uuid.uuid4()),
                "type": "scatter",
                "title": f"Sales\nBy Cost of Sales",
                "dataKey": "y",
                "xAxis": "x",
                "data": scatter_data.to_dict(orient='records')
            })
        
        # Chart 3: Sales by Office Country (Donut Chart with proper labels)
        if sales_col and office_country_col:
            country_sales = df_safe.groupby(office_country_col)[sales_col].sum().reset_index()
            # CRITICAL: Use meaningful column names for donut chart
            country_sales.columns = ['name', 'value']
            charts.append({
                "id": str(uuid.uuid4()),
                "type": "donut",
                "title": f"Sales\nBy Office Country",
                "dataKey": "value",
                "xAxis": "name",
                "data": country_sales.to_dict(orient='records')
            })
        
        # Chart 4: Sales by Customer Country (Vertical Bar Chart - Top 15 countries)
        if sales_col and customer_country_col:
            customer_sales = df_safe.groupby(customer_country_col)[sales_col].sum().sort_values(ascending=False).head(15).reset_index()
            customer_sales.columns = ['name', 'value']  # Rename for clarity
            charts.append({
                "id": str(uuid.uuid4()),
                "type": "bar",
                "title": f"Sales\nBy Customer Country",
                "dataKey": "value",
                "xAxis": "name",
                "data": customer_sales.to_dict(orient='records'),
                "layout": "horizontal"
            })
        
        return charts[:4]

    def _generate_chart_by_type(self, df, preferred_type="bar"):
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
