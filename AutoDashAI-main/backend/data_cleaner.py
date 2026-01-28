# data_cleaner.py
import pandas as pd
import numpy as np
import re
import io
from sklearn.impute import SimpleImputer

# Optional word2number import
try:
    from word2number import w2n
    WORD2NUM_AVAILABLE = True
except ImportError:
    WORD2NUM_AVAILABLE = False


# ------------------ Helper Functions ------------------

def detect_issues(df: pd.DataFrame) -> list:
    """Detect data quality issues"""
    issues = []
    missing = df.isnull().sum()

    for col, count in missing.items():
        if count > 0:
            issues.append(f"Column **{col}** has {count} missing values")

    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues.append(f"⚠️ {duplicates} duplicate rows detected")

    for col in df.columns:
        if df[col].dtype == object:
            numeric_like = df[col].astype(str).str.replace('.', '', 1).str.isnumeric().sum()
            if numeric_like > len(df) / 2:
                issues.append(f"Column **{col}** may be numeric but stored as text")

    return issues


def convert_value(x):
    """Convert mixed data intelligently"""
    if isinstance(x, str):
        x = x.strip().lower()

        if WORD2NUM_AVAILABLE:
            try:
                return w2n.word_to_num(x)
            except:
                pass

        if re.match(r'^\d+(\.\d+)?k$', x):
            return float(x.replace('k', '')) * 1000
        if re.match(r'^\d+(\.\d+)?m$', x):
            return float(x.replace('m', '')) * 1_000_000
        if re.match(r'^-?\d+(\.\d+)?$', x):
            return float(x)

    return x


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data with imputation and conversion"""
    cleaned_df = df.copy()
    cleaned_df = cleaned_df.replace(["error", "Error", " ", "", "Na", "nan", "None"], np.nan)

    for col in cleaned_df.columns:
        cleaned_df[col] = cleaned_df[col].apply(convert_value)

    for col in cleaned_df.columns:
        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
            imputer = SimpleImputer(strategy="mean")
            cleaned_df[col] = imputer.fit_transform(cleaned_df[[col]])
        else:
            mode_series = cleaned_df[col].mode()
            mode_val = mode_series[0] if not mode_series.empty else "Unknown"
            cleaned_df[col] = cleaned_df[col].fillna(mode_val)
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip().str.title()

    cleaned_df.drop_duplicates(inplace=True)
    return cleaned_df


def safe_json(df: pd.DataFrame):
    """Replace NaN/Inf for JSON safety"""
    return df.replace([np.nan, np.inf, -np.inf], None)
