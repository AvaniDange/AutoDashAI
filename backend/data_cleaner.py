# data_cleaner.py
import pandas as pd
import numpy as np
import re
from sklearn.impute import SimpleImputer
import json

# Try to import word2number
try:
    from word2number import w2n
    WORD2NUM_AVAILABLE = True
except ImportError:
    WORD2NUM_AVAILABLE = False

def detect_issues(df: pd.DataFrame) -> list:
    """Detect data quality issues efficiently"""
    issues = []
    if df.empty: return ["Dataset is empty"]
    
    # 1. Missing values
    missing = df.isnull().sum()
    for col, count in missing[missing > 0].items():
        issues.append(f"Column **{col}** has {count} missing values")

    # 2. Duplicates
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues.append(f"⚠️ {duplicates} duplicate rows detected")

    # 3. Text columns that look numeric
    sample_size = min(500, len(df))
    sample_df = df.sample(sample_size) if len(df) > 500 else df
    
    for col in df.columns:
        if df[col].dtype == object:
            try:
                # Try to convert a sample to see if it's mostly numeric
                vals = sample_df[col].astype(str).str.replace(r'[$,\s]', '', regex=True)
                numeric_like = pd.to_numeric(vals, errors='coerce').notnull().sum()
                if numeric_like > sample_size / 2:
                    issues.append(f"Column **{col}** may be numeric but stored as text")
            except:
                pass

    return issues

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Optimized data cleaning for large datasets"""
    if df.empty: return df
    
    print(f"DEBUG: Cleaning dataset with {len(df)} rows and {len(df.columns)} columns")
    cleaned_df = df.copy()
    
    # Bulk replace common null indicators
    null_variants = ["error", "Error", " ", "", "Na", "nan", "None", "n/a", "N/A", "null", "NULL", "NAN"]
    cleaned_df = cleaned_df.replace(null_variants, np.nan)

    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == object:
            # Vectorized cleaning for common currency/suffix patterns
            s = cleaned_df[col].astype(str).str.strip().str.lower()
            
            # Clean commas and dollar signs
            s = s.str.replace(r'[$,]', '', regex=True)
            
            # Convert 'k' and 'm'
            k_mask = s.str.endswith('k', na=False)
            m_mask = s.str.endswith('m', na=False)
            
            if k_mask.any() or m_mask.any():
                nums = pd.to_numeric(s.str.replace(r'[km]', '', regex=True), errors='coerce')
                cleaned_df.loc[k_mask, col] = nums[k_mask] * 1000
                cleaned_df.loc[m_mask, col] = nums[m_mask] * 1_000_000
            
            # Final numeric conversion
            converted = pd.to_numeric(s, errors='coerce')
            # If at least 50% converted successfully, keep the numeric version
            if converted.notnull().sum() > len(df) / 2:
                cleaned_df[col] = converted

    # Imputing Missing Values
    numeric_cols = cleaned_df.select_dtypes(include=[np.number]).columns
    categorical_cols = cleaned_df.select_dtypes(exclude=[np.number]).columns

    if len(numeric_cols) > 0:
        imputer = SimpleImputer(strategy="median") # Median is more robust for EEG/Sensor data
        cleaned_df[numeric_cols] = imputer.fit_transform(cleaned_df[numeric_cols])

    if len(categorical_cols) > 0:
        for col in categorical_cols:
            fill_val = cleaned_df[col].mode().iloc[0] if not cleaned_df[col].mode().empty else "Unknown"
            cleaned_df[col] = cleaned_df[col].fillna(fill_val).astype(str).str.title()

    cleaned_df.drop_duplicates(inplace=True)
    return cleaned_df

def safe_json(obj):
    """
    Recursively remove NaN, Inf, -Inf from any object (dict, list, DataFrame) 
    to make it JSON-safe for FastAPI.
    """
    if isinstance(obj, pd.DataFrame):
        # For DataFrames, return a version where all problematic values are None
        return obj.replace([np.nan, np.inf, -np.inf], None).to_dict(orient='records')
    
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [safe_json(x) for x in obj]
    
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    
    if isinstance(obj, (np.integer, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj.item() # convert numpy type to python type

    return obj
