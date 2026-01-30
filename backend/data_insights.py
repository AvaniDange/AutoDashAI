"""
Data Insight Generator - Analyzes dashboard data to generate meaningful insights.
Works directly with session data, no image analysis needed.
"""
import pandas as pd
import numpy as np
from typing import List, Dict

def generate_data_insights(df: pd.DataFrame, charts: List[dict]) -> List[Dict[str, str]]:
    """Generate insights from actual dashboard data."""
    insights = []
    
    # 1. Analyze overall data shape
    insights.append({
        "title": "Dataset Overview",
        "description": f"Your dashboard displays {len(df)} records across {len(df.columns)} columns. The data includes {len(df.select_dtypes(include=[np.number]).columns)} numeric metrics for analysis."
    })
    
    # 2. Analyze numeric columns for trends
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        for col in numeric_cols[:2]:  # Top 2 numeric columns
            mean_val = df[col].mean()
            max_val = df[col].max()
            min_val = df[col].min()
            std_val = df[col].std()
            
            # Determine if there's high variation
            if std_val / mean_val > 0.5 if mean_val != 0 else False:
                insights.append({
                    "title": f"{col} - High Variability",
                    "description": f"{col} ranges from {min_val:.2f} to {max_val:.2f} with significant variation (avg: {mean_val:.2f}). This suggests diverse data points that may require segmentation analysis."
                })
            else:
                insights.append({
                    "title": f"{col} - Stable Pattern",
                    "description": f"{col} shows relatively stable values around {mean_val:.2f}. The range is {min_val:.2f} to {max_val:.2f}, indicating consistent performance across the dataset."
                })
    
    # 3. Analyze categorical columns
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    if categorical_cols:
        for col in categorical_cols[:2]:  # Top 2 categorical columns
            unique_count = df[col].nunique()
            most_common = df[col].mode()[0] if not df[col].mode().empty else "N/A"
            most_common_count = (df[col] == most_common).sum()
            
            if unique_count <= 10:
                insights.append({
                    "title": f"{col} Distribution",
                    "description": f"{col} has {unique_count} categories. '{most_common}' appears most frequently ({most_common_count} times, {most_common_count/len(df)*100:.1f}% of data)."
                })
            else:
                insights.append({
                    "title": f"{col} - Many Categories",
                    "description": f"{col} contains {unique_count} unique values, suggesting high diversity. Consider grouping similar categories for clearer visualization."
                })
    
    # 4. Analyze charts
    chart_types = [chart['type'] for chart in charts]
    if chart_types:
        chart_summary = ", ".join(set(chart_types))
        insights.append({
            "title": "Visualization Strategy",
            "description": f"Your dashboard uses {len(charts)} charts ({chart_summary}). Each visualization type highlights different aspects: bars for comparisons, lines for trends, and pies for proportions."
        })
    
    # 5. Look for correlations in numeric data (Optimized for performance)
    if len(numeric_cols) >= 2:
        try:
            # Use a subset of columns if there are too many (EEG data can have 100+)
            corr_subset = numeric_cols[:25] 
            corr_matrix = df[corr_subset].corr()
            high_corr_pairs = []
            for i in range(len(corr_subset)):
                for j in range(i+1, len(corr_subset)):
                    val = corr_matrix.iloc[i, j]
                    if not np.isnan(val) and abs(val) > 0.75:
                        high_corr_pairs.append((corr_subset[i], corr_subset[j], val))
            
            if high_corr_pairs:
                # Get the strongest correlation
                high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
                col1, col2, corr_val = high_corr_pairs[0]
                insights.append({
                    "title": "Strong Relationship Found",
                    "description": f"The model detected a strong connection between {col1} and {col2} (correlation: {corr_val:.2f}). This suggests these metrics are highly interdependent."
                })
        except Exception as e:
            print(f"DEBUG: Correlation analysis skipped: {e}")
    
    # 6. Data quality check
    missing_count = df.isnull().sum().sum()
    if missing_count > 0:
        insights.append({
            "title": "Data Quality Note",
            "description": f"{missing_count} missing values detected in the dataset. These have likely been handled during cleaning, but monitor for data collection issues."
        })
    
    # 7. Actionable recommendation
    insights.append({
        "title": "Next Steps",
        "description": "Use the chat interface to create custom charts, filter data by specific categories, or convert chart types for different perspectives on your data."
    })
    
    return insights[:6]  # Return top 6 insights
