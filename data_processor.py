"""
Data processing engine for CSV/Excel ingestion, schema extraction,
statistical profiling, and outlier detection.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def load_file(uploaded_file) -> pd.DataFrame:
    """Load a CSV or Excel file into a pandas DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file type: {name}")
    return df


def get_schema_summary(df: pd.DataFrame) -> str:
    """Generate a structured schema summary for the LLM context."""
    lines = []
    lines.append(f"DATASET SHAPE: {df.shape[0]} rows × {df.shape[1]} columns")
    lines.append("")
    lines.append("COLUMN SCHEMA:")
    lines.append("-" * 60)

    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        null_count = df[col].isna().sum()
        unique_count = df[col].nunique()

        line = f"  • {col} | type: {dtype} | non-null: {non_null} | nulls: {null_count} | unique: {unique_count}"
        lines.append(line)

    return "\n".join(lines)


def get_numeric_stats(df: pd.DataFrame) -> str:
    """Generate statistical summary for numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return "NO NUMERIC COLUMNS IN DATASET."

    lines = []
    lines.append("NUMERIC COLUMN STATISTICS:")
    lines.append("-" * 60)

    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            lines.append(f"  • {col}: all values are null")
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lines.append(f"  • {col}:")
        lines.append(f"      min={series.min():.4g}, max={series.max():.4g}, "
                      f"mean={series.mean():.4g}, median={series.median():.4g}, "
                      f"std={series.std():.4g}")
        lines.append(f"      Q1={q1:.4g}, Q3={q3:.4g}, IQR={iqr:.4g}")

    return "\n".join(lines)


def get_text_stats(df: pd.DataFrame) -> str:
    """Generate summary for text/categorical columns."""
    text_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not text_cols:
        return "NO TEXT/CATEGORICAL COLUMNS IN DATASET."

    lines = []
    lines.append("TEXT/CATEGORICAL COLUMN STATISTICS:")
    lines.append("-" * 60)

    for col in text_cols:
        series = df[col].dropna()
        if series.empty:
            lines.append(f"  • {col}: all values are null")
            continue

        unique = series.nunique()
        top_values = series.value_counts().head(5)
        top_str = ", ".join([f"'{v}' ({c})" for v, c in top_values.items()])

        lines.append(f"  • {col}:")
        lines.append(f"      unique values: {unique}")
        lines.append(f"      top values: {top_str}")

    return "\n".join(lines)


def detect_outliers(df: pd.DataFrame) -> Tuple[str, pd.DataFrame]:
    """
    Detect outliers using the IQR method on numeric columns.
    Returns a text summary and a DataFrame of outlier flags.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return "NO NUMERIC COLUMNS — outlier detection skipped.", pd.DataFrame()

    outlier_flags = pd.DataFrame(index=df.index)
    lines = []
    lines.append("OUTLIER REPORT (IQR method: outside Q1-1.5*IQR to Q3+1.5*IQR):")
    lines.append("-" * 60)

    total_outliers = 0
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        is_outlier = (df[col] < lower) | (df[col] > upper)
        outlier_flags[col] = is_outlier
        count = is_outlier.sum()
        total_outliers += count

        if count > 0:
            outlier_vals = df.loc[is_outlier, col].tolist()
            # Show at most 10 outlier values
            display_vals = outlier_vals[:10]
            suffix = f" ... and {len(outlier_vals) - 10} more" if len(outlier_vals) > 10 else ""
            lines.append(f"  • {col}: {count} outliers (range [{lower:.4g}, {upper:.4g}])")
            lines.append(f"      values: {display_vals}{suffix}")
        else:
            lines.append(f"  • {col}: no outliers detected")

    lines.append(f"\nTOTAL OUTLIER CELLS: {total_outliers}")
    return "\n".join(lines), outlier_flags


def build_full_context(df: pd.DataFrame) -> str:
    """Build the complete data context string for the LLM system prompt."""
    parts = [
        get_schema_summary(df),
        "",
        get_numeric_stats(df),
        "",
        get_text_stats(df),
        "",
        detect_outliers(df)[0],
    ]
    return "\n\n".join(parts)


def get_profile_cards(df: pd.DataFrame) -> dict:
    """Return summary metrics for UI display."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    text_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    other_cols = [c for c in df.columns if c not in numeric_cols and c not in text_cols]

    outlier_summary, _ = detect_outliers(df)
    # Count total outlier cells
    total_outliers = 0
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        total_outliers += ((df[col] < lower) | (df[col] > upper)).sum()

    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "numeric_cols": len(numeric_cols),
        "text_cols": len(text_cols),
        "other_cols": len(other_cols),
        "null_cells": int(df.isna().sum().sum()),
        "total_outliers": total_outliers,
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
    }
