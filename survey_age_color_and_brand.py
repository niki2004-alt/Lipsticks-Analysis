import streamlit as st
from pathlib import Path

from lipstick_analysis_core import analyze_age_color_brand

def main():
    st.set_page_config(page_title="Survey Color Dashboard", layout="wide")
    st.title("Lipstick Survey (Age, Color, Brand) Dashboard")

    base_dir = Path(__file__).resolve().parent
    default_path = base_dir / "csv" / "survey color.csv"
    fallback_path = base_dir / "csv" / "survey.csv"
    data_path = default_path if default_path.exists() else fallback_path

    try:
        stats = analyze_age_color_brand(data_path)
    except Exception as e:
        st.error(f"Unable to read data: {e}")
        return

    st.header("1. Top color & brand by age group")
    st.dataframe(stats.age_profiles, hide_index=True, use_container_width=True)

    st.header("2. Response count by age group")
    st.dataframe(stats.age_counts, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
