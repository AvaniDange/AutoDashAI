"""
Visualization Engine — Intelligent, agentic chart and KPI generation.

Profiles the dataset columns, selects appropriate chart types based on data
semantics, and produces aggregated chart-ready data (never raw head/sample).
"""

import uuid
import math
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional


# ---------------------------------------------------------------------------
# Column profiles
# ---------------------------------------------------------------------------

TEMPORAL_KEYWORDS = {"date", "time", "year", "month", "day", "week", "quarter",
                     "timestamp", "created", "updated", "period", "dt"}

ID_KEYWORDS = {"id", "uuid", "key", "index", "code", "serial", "number", "no",
               "pk", "fk", "ref"}


def _is_temporal(series: pd.Series, col_name: str) -> bool:
    """Heuristic: is this column temporal?"""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    name_lower = col_name.lower().replace("_", " ").replace("-", " ")
    if any(kw in name_lower.split() for kw in TEMPORAL_KEYWORDS):
        # Verify it can actually be parsed
        try:
            sample = series.dropna().head(20)
            pd.to_datetime(sample, infer_datetime_format=True)
            return True
        except Exception:
            pass
    return False


def _is_id_column(series: pd.Series, col_name: str, n_rows: int) -> bool:
    """Heuristic: is this a unique-ID / surrogate-key column?"""
    name_lower = col_name.lower().replace("_", " ").replace("-", " ")
    if any(kw in name_lower.split() for kw in ID_KEYWORDS):
        return True
    # Almost-unique string column with high cardinality
    if series.dtype == object and series.nunique() > 0.9 * n_rows and n_rows > 20:
        return True
    return False


class ColumnProfile:
    """Lightweight profile for a single column."""
    __slots__ = ("name", "role", "dtype", "nunique", "sample_values")

    def __init__(self, name, role, dtype, nunique, sample_values):
        self.name = name
        self.role = role          # "numeric", "categorical", "temporal", "skip"
        self.dtype = str(dtype)
        self.nunique = nunique
        self.sample_values = sample_values

    def __repr__(self):
        return f"<{self.name}: {self.role} ({self.nunique} unique)>"


def profile_columns(df: pd.DataFrame) -> List[ColumnProfile]:
    """Classify every column in the dataframe."""
    profiles: List[ColumnProfile] = []
    n = len(df)

    for col in df.columns:
        s = df[col]
        nunique = s.nunique()
        sample = s.dropna().head(5).tolist()

        if _is_temporal(s, col):
            role = "temporal"
        elif _is_id_column(s, col, n):
            role = "skip"
        elif pd.api.types.is_numeric_dtype(s):
            # Numeric columns with very few unique vals can act as categorical
            if nunique <= 2 and n > 10:
                role = "categorical"
            else:
                role = "numeric"
        elif s.dtype == object or pd.api.types.is_categorical_dtype(s):
            if nunique > 0.8 * n and n > 30:
                role = "skip"     # free-text / near-unique strings
            else:
                role = "categorical"
        else:
            role = "skip"

        profiles.append(ColumnProfile(col, role, s.dtype, nunique, sample))

    return profiles


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _safe_json_value(v):
    """Convert numpy/pandas scalars to native Python types for JSON."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return 0
        return round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def _safe_records(df_or_series) -> list:
    """Convert a dataframe to JSON-safe list of dicts."""
    if isinstance(df_or_series, pd.Series):
        df_or_series = df_or_series.reset_index()
    records = df_or_series.to_dict(orient="records")
    clean = []
    for rec in records:
        clean.append({k: _safe_json_value(v) for k, v in rec.items()})
    return clean


def _topk_bar_data(df: pd.DataFrame, cat_col: str, num_col: str,
                   k: int = 10, agg: str = "mean") -> list:
    """Top-K categories by aggregated numeric value → bar chart data."""
    grouped = df.groupby(cat_col, dropna=True)[num_col].agg(agg).nlargest(k)
    out = grouped.reset_index()
    out.columns = [cat_col, num_col]
    return _safe_records(out)


def _timeseries_data(df: pd.DataFrame, time_col: str, num_col: str,
                     max_points: int = 60) -> list:
    """Resample temporal data to ~max_points for a trend line."""
    tmp = df[[time_col, num_col]].copy()
    tmp[time_col] = pd.to_datetime(tmp[time_col], errors="coerce")
    tmp = tmp.dropna(subset=[time_col])
    if tmp.empty:
        return []

    tmp = tmp.sort_values(time_col)
    n = len(tmp)

    if n <= max_points:
        tmp[time_col] = tmp[time_col].dt.strftime("%Y-%m-%d")
        return _safe_records(tmp)

    # Choose resample frequency
    span = (tmp[time_col].max() - tmp[time_col].min()).days
    if span > 365 * 3:
        freq = "QS"       # quarterly
    elif span > 365:
        freq = "MS"       # monthly
    elif span > 60:
        freq = "W"        # weekly
    else:
        freq = "D"        # daily

    tmp = tmp.set_index(time_col)
    resampled = tmp.resample(freq).mean(numeric_only=True).dropna().reset_index()
    resampled[time_col] = resampled[time_col].dt.strftime("%Y-%m-%d")
    return _safe_records(resampled)


def _histogram_data(series: pd.Series, bins: int = 20) -> list:
    """Compute histogram bin counts for a numeric column."""
    clean = series.dropna()
    if clean.empty:
        return []
    counts, edges = np.histogram(clean, bins=min(bins, max(5, clean.nunique())))
    data = []
    for i in range(len(counts)):
        label = f"{edges[i]:.1f}–{edges[i+1]:.1f}"
        data.append({"range": label, "count": int(counts[i])})
    return data


def _scatter_data(df: pd.DataFrame, x_col: str, y_col: str,
                  max_points: int = 200) -> list:
    """Prepare scatter data (subsample if huge)."""
    tmp = df[[x_col, y_col]].dropna()
    if len(tmp) > max_points:
        tmp = tmp.sample(max_points, random_state=42)
    return _safe_records(tmp)


def _pie_data(df: pd.DataFrame, cat_col: str, num_col: Optional[str] = None,
              k: int = 6) -> list:
    """Category proportions → pie slices."""
    if num_col:
        grouped = df.groupby(cat_col, dropna=True)[num_col].sum().nlargest(k)
    else:
        grouped = df[cat_col].value_counts().nlargest(k)
    out = grouped.reset_index()
    out.columns = [cat_col, num_col or "count"]
    return _safe_records(out)


# ---------------------------------------------------------------------------
# Chart selection engine
# ---------------------------------------------------------------------------

class VisualizationEngine:
    """Agentic engine that reasons about data before generating charts."""

    def generate_dashboard(self, df: pd.DataFrame) -> Tuple[list, list]:
        """
        Main entry: returns (charts, kpis).
        Charts are ready-to-render dicts with `data` already aggregated.
        """
        profiles = profile_columns(df)
        charts = self._select_charts(df, profiles)
        kpis = self._generate_smart_kpis(df, profiles)
        return charts, kpis

    # --------------------------------------------------------- on-demand chart
    def build_chart_from_spec(self, df: pd.DataFrame, spec: dict) -> Optional[dict]:
        """
        Build a single chart from a Gemini-generated spec.

        spec keys:
            chart_type  : bar | line | area | pie | scatter | table
            x_column    : column name for x-axis / category
            y_column    : column name for y-axis / metric
            aggregation : sum | mean | count | median | min | max  (default: sum)
            top_k       : int, limit categories (default: 10)
            title       : optional custom title
            filter_column : optional column to filter on
            filter_value  : optional value to filter by
        """
        chart_type = spec.get("chart_type", "bar")
        x_col = spec.get("x_column", "")
        y_col = spec.get("y_column", "")
        agg = spec.get("aggregation", "sum")
        top_k = spec.get("top_k", 10)
        title = spec.get("title", "")
        filter_col = spec.get("filter_column")
        filter_val = spec.get("filter_value")

        # Validate columns exist
        if x_col and x_col not in df.columns:
            return None
        if y_col and y_col not in df.columns:
            # If y is missing but x is numeric, use x as the metric
            if x_col and pd.api.types.is_numeric_dtype(df[x_col]):
                y_col = x_col
                x_col = ""
            else:
                return None

        # Apply filter if specified
        work_df = df.copy()
        if filter_col and filter_val and filter_col in work_df.columns:
            work_df = work_df[work_df[filter_col].astype(str).str.contains(str(filter_val), case=False, na=False)]
            if work_df.empty:
                return None

        # Auto-detect roles
        profiles = profile_columns(work_df)
        x_profile = next((p for p in profiles if p.name == x_col), None) if x_col else None
        y_profile = next((p for p in profiles if p.name == y_col), None) if y_col else None

        # Build data based on chart type
        try:
            if chart_type in ("bar", "pie"):
                if x_col and y_col:
                    data = _topk_bar_data(work_df, x_col, y_col, k=top_k, agg=agg)
                elif y_col:
                    data = _histogram_data(work_df[y_col])
                    x_col = "range"
                    y_col = "count"
                else:
                    return None
                if not title:
                    title = f"{y_col} by {x_col}" if chart_type == "bar" else f"{x_col} Breakdown"

            elif chart_type in ("line", "area"):
                if x_profile and x_profile.role == "temporal" and y_col:
                    data = _timeseries_data(work_df, x_col, y_col)
                elif x_col and y_col:
                    # Non-temporal line: group by x
                    data = _topk_bar_data(work_df, x_col, y_col, k=top_k, agg=agg)
                else:
                    return None
                if not title:
                    title = f"{y_col} Trend" if x_profile and x_profile.role == "temporal" else f"{y_col} by {x_col}"

            elif chart_type == "scatter":
                if x_col and y_col:
                    data = _scatter_data(work_df, x_col, y_col)
                else:
                    return None
                if not title:
                    title = f"{y_col} vs {x_col}"

            elif chart_type == "table":
                if x_col and y_col:
                    data = _topk_bar_data(work_df, x_col, y_col, k=top_k, agg=agg)
                else:
                    return None
                if not title:
                    title = f"{y_col} by {x_col}"

            else:
                # Default to bar
                if x_col and y_col:
                    data = _topk_bar_data(work_df, x_col, y_col, k=top_k, agg=agg)
                else:
                    return None
                if not title:
                    title = f"{y_col} by {x_col}"

            if not data:
                return None

            subtitle = spec.get("title", f"Aggregation: {agg}")
            return self._chart(chart_type, title, data, y_col, x_col, subtitle=subtitle)

        except Exception as e:
            print(f"DEBUG: build_chart_from_spec error: {e}")
            return None

    # ------------------------------------------------------------------ charts
    def _select_charts(self, df: pd.DataFrame,
                       profiles: List[ColumnProfile]) -> list:
        numerics = [p for p in profiles if p.role == "numeric"]
        categoricals = [p for p in profiles if p.role == "categorical"]
        temporals = [p for p in profiles if p.role == "temporal"]

        charts: list = []
        used_pairs: set = set()

        # --- 1. Category × Metric → bar (top-K) — limit to 1 for diversity -
        for cat in categoricals[:3]:
            if cat.nunique < 2:
                continue
            for num in numerics[:3]:
                key = ("bar", cat.name, num.name)
                if key in used_pairs:
                    continue
                used_pairs.add(key)
                agg = "sum" if num.nunique > 20 else "mean"
                data = _topk_bar_data(df, cat.name, num.name, k=10, agg=agg)
                if data:
                    charts.append(self._chart(
                        "bar", f"{num.name} by {cat.name}",
                        data, num.name, cat.name,
                        subtitle=f"Top 10 by {agg}"
                    ))
                if len(charts) >= 1:
                    break
            if len(charts) >= 1:
                break

        # --- 2. Temporal × Metric → line (trend) -------------------------
        for tmp in temporals[:1]:
            for num in numerics[:2]:
                key = ("line", tmp.name, num.name)
                if key in used_pairs:
                    continue
                used_pairs.add(key)
                data = _timeseries_data(df, tmp.name, num.name)
                if data:
                    charts.append(self._chart(
                        "line", f"{num.name} over Time",
                        data, num.name, tmp.name,
                        subtitle=f"Trend by {tmp.name}"
                    ))
                if len(charts) >= 4:
                    break

        # --- 3. Distribution → histogram (rendered as area chart) ---------
        for num in numerics[:2]:
            key = ("hist", num.name)
            if key in used_pairs or num.nunique < 5:
                continue
            used_pairs.add(key)
            data = _histogram_data(df[num.name])
            if data:
                charts.append(self._chart(
                    "area", f"Distribution of {num.name}",
                    data, "count", "range",
                    subtitle="Frequency distribution"
                ))
            if len(charts) >= 4:
                break

        # --- 4. Scatter → correlation ------------------------------------
        if len(numerics) >= 2:
            # Pick the pair with highest absolute correlation
            best_pair = self._best_corr_pair(df, numerics)
            if best_pair:
                x, y, corr_val = best_pair
                key = ("scatter", x, y)
                if key not in used_pairs:
                    used_pairs.add(key)
                    data = _scatter_data(df, x, y)
                    if data:
                        charts.append(self._chart(
                            "scatter",
                            f"{y} vs {x}",
                            data, y, x,
                            subtitle=f"Correlation: {corr_val:+.2f}"
                        ))
            elif len(numerics) >= 2:
                # Even without strong correlation, show a scatter for exploration
                x, y = numerics[0].name, numerics[1].name
                data = _scatter_data(df, x, y)
                if data:
                    charts.append(self._chart(
                        "scatter",
                        f"{y} vs {x}",
                        data, y, x,
                        subtitle="Exploratory scatter"
                    ))

        # --- 5. Pie → category proportions --------------------------------
        for cat in categoricals[:2]:
            if cat.nunique < 2 or cat.nunique > 20:
                continue
            key = ("pie", cat.name)
            if key in used_pairs:
                continue
            used_pairs.add(key)
            num_col = numerics[0].name if numerics else None
            data = _pie_data(df, cat.name, num_col, k=6)
            if data:
                value_key = num_col or "count"
                charts.append(self._chart(
                    "pie", f"{cat.name} Breakdown",
                    data, value_key, cat.name,
                    subtitle="Proportional share"
                ))
            if len(charts) >= 6:
                break

        # Fallback: if no charts generated, create simple area from first numeric
        if not charts and numerics:
            col = numerics[0].name
            data = _histogram_data(df[col])
            if data:
                charts.append(self._chart(
                    "bar", f"{col} Distribution",
                    data, "count", "range",
                    subtitle="Value distribution"
                ))

        return charts[:6]

    # ------------------------------------------------------------------ KPIs
    def _generate_smart_kpis(self, df: pd.DataFrame,
                             profiles: List[ColumnProfile]) -> list:
        numerics = [p for p in profiles if p.role == "numeric"]
        categoricals = [p for p in profiles if p.role == "categorical"]
        kpis: list = []

        # 1. Total rows
        kpis.append({
            "title": "Total Records",
            "value": f"{len(df):,}",
            "change": "Dataset Size",
            "context": f"{len(df.columns)} columns"
        })

        # 2. Sum of primary numeric
        if numerics:
            col = numerics[0].name
            total = df[col].sum()
            kpis.append({
                "title": f"Total {col}",
                "value": self._fmt(total),
                "change": "Metric",
                "context": f"Sum across all records"
            })

        # 3. Median of secondary numeric (or same if only one)
        if len(numerics) >= 2:
            col = numerics[1].name
            med = df[col].median()
            kpis.append({
                "title": f"Median {col}",
                "value": self._fmt(med),
                "change": "Metric",
                "context": f"Middle value"
            })
        elif numerics:
            col = numerics[0].name
            avg = df[col].mean()
            kpis.append({
                "title": f"Avg {col}",
                "value": self._fmt(avg),
                "change": "Metric",
                "context": f"Mean across dataset"
            })

        # 4. Unique categories
        if categoricals:
            cat = categoricals[0]
            kpis.append({
                "title": f"Unique {cat.name}",
                "value": f"{cat.nunique:,}",
                "change": "Metric",
                "context": f"Distinct values"
            })

        # 5. Data range for a numeric
        if len(numerics) >= 2:
            col = numerics[1].name
            mn, mx = df[col].min(), df[col].max()
            kpis.append({
                "title": f"{col} Range",
                "value": f"{self._fmt(mn)} – {self._fmt(mx)}",
                "change": "Metric",
                "context": "Min to Max"
            })

        # 6. Coefficient of Variation (stability)
        if numerics:
            col = numerics[0].name
            mean_val = df[col].mean()
            std_val = df[col].std()
            if mean_val != 0 and not np.isnan(mean_val):
                cv = abs(std_val / mean_val) * 100
                label = "Stable" if cv < 30 else ("Moderate" if cv < 60 else "High Variability")
                kpis.append({
                    "title": f"{col} Stability",
                    "value": f"{cv:.1f}% CV",
                    "change": label,
                    "context": "Coefficient of Variation"
                })

        return kpis[:6]

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _chart(chart_type, title, data, data_key, x_axis,
               subtitle="") -> dict:
        return {
            "id": str(uuid.uuid4()),
            "type": chart_type,
            "title": title,
            "subtitle": subtitle,
            "dataKey": data_key,
            "xAxis": x_axis,
            "data": data,
        }

    @staticmethod
    def _fmt(val) -> str:
        """Human-friendly number formatting."""
        if isinstance(val, (int, np.integer)):
            if abs(val) >= 1_000_000:
                return f"{val/1_000_000:,.1f}M"
            if abs(val) >= 1_000:
                return f"{val/1_000:,.1f}K"
            return f"{val:,}"
        if isinstance(val, (float, np.floating)):
            if np.isnan(val) or np.isinf(val):
                return "N/A"
            if abs(val) >= 1_000_000:
                return f"{val/1_000_000:,.1f}M"
            if abs(val) >= 1_000:
                return f"{val/1_000:,.1f}K"
            return f"{val:,.2f}"
        return str(val)

    @staticmethod
    def _best_corr_pair(df, numerics, top_n_cols=15):
        """Find the pair of numeric columns with highest absolute correlation."""
        cols = [p.name for p in numerics[:top_n_cols]]
        if len(cols) < 2:
            return None
        try:
            corr = df[cols].corr()
            best_corr = 0
            best = None
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    v = corr.iloc[i, j]
                    if not np.isnan(v) and abs(v) > abs(best_corr) and abs(v) > 0.3:
                        best_corr = v
                        best = (cols[i], cols[j], v)
            return best
        except Exception:
            return None
