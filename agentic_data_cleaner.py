import pandas as pd
import streamlit as st
import numpy as np
import re
from sklearn.impute import SimpleImputer

# Try importing word2number, else skip gracefully
try:
    from word2number import w2n
    WORD2NUM_AVAILABLE = True
except ImportError:
    WORD2NUM_AVAILABLE = False

# ---------------- STREAMLIT CONFIG ----------------
st.set_page_config(page_title="Agentic Data Cleaner", layout="wide")

st.title("🤖 Agentic AI Data Cleaner and Completer")

uploaded_file = st.file_uploader("📂 Upload an Excel or CSV file", type=["csv", "xlsx"])

if uploaded_file:
    # ---- Step 1: Load File ----
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📊 Original Data Preview")
    st.dataframe(df.head())

    # ---- Step 2: Detect Issues ----
    st.subheader("🧩 Detected Issues")

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

    if not issues:
        st.success("✅ No major issues detected.")
    else:
        for issue in issues:
            st.warning(issue)

    # ---- Step 3: Auto-cleaning ----
    st.subheader("⚡ Auto-Cleaning and Completion in Progress...")

    cleaned_df = df.copy()

    # Convert common error or empty tokens to NaN
    cleaned_df = cleaned_df.replace(["error", "Error", " ", "", "Na", "nan", "None"], np.nan)

    # --- Smart conversion function ---
    def convert_value(x):
        if isinstance(x, str):
            x = x.strip().lower()

            # Try converting word numbers like 'twenty-eight'
            if WORD2NUM_AVAILABLE:
                try:
                    return w2n.word_to_num(x)
                except:
                    pass

            # Convert compact forms like 50k, 2.5m
            if re.match(r'^\d+(\.\d+)?k$', x):
                return float(x.replace('k', '')) * 1000
            if re.match(r'^\d+(\.\d+)?m$', x):
                return float(x.replace('m', '')) * 1000000

            # If numeric-looking string
            if re.match(r'^-?\d+(\.\d+)?$', x):
                return float(x)

        return x

    # Apply conversion to all cells
    for col in cleaned_df.columns:
        cleaned_df[col] = cleaned_df[col].apply(convert_value)

    # ---- Step 4: Imputation ----
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype in [np.int64, np.float64, float, int]:
            # Fill numeric missing values with mean
            imputer = SimpleImputer(strategy="mean")
            cleaned_df[col] = imputer.fit_transform(cleaned_df[[col]])
        else:
            # Fill text columns with most common value (mode)
            mode_series = cleaned_df[col].mode()
            if not mode_series.empty:
                mode_val = mode_series[0]
            else:
                mode_val = "Unknown"
            cleaned_df[col] = cleaned_df[col].fillna(mode_val)
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip().str.title()

    # ---- Step 5: Drop duplicates safely ----
    try:
        cleaned_df.drop_duplicates(inplace=True)
    except Exception as e:
        st.warning(f"⚠️ Could not drop duplicates: {e}")

    st.success("✅ Auto-cleaning complete! Errors fixed, values imputed, and types standardized.")

    st.subheader("🧼 Cleaned Data Preview")
    st.dataframe(cleaned_df.head())

    # ---- Step 6: Download cleaned file ----
    cleaned_filename_csv = "cleaned_data.csv"
    cleaned_filename_excel = "cleaned_data.xlsx"

    # Save CSV
    cleaned_df.to_csv(cleaned_filename_csv, index=False)

    # Save Excel
    cleaned_df.to_excel(cleaned_filename_excel, index=False)

    # Download buttons
    st.download_button(
      "📥 Download Cleaned File (CSV)",
       data=open(cleaned_filename_csv, "rb"),
       file_name="cleaned_data.csv",
      mime="text/csv"
      )

    st.download_button(
       "📊 Download Cleaned File (Excel)",
       data=open(cleaned_filename_excel, "rb"),
       file_name="cleaned_data.xlsx",
       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Please upload a CSV or Excel file to start cleaning.")
