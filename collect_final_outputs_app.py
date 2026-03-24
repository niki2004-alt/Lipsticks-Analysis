from __future__ import annotations

from pathlib import Path

import streamlit as st

from lipstick_analysis_core import analyze_age_color_brand, analyze_overall_survey


def main() -> None:
    st.set_page_config(page_title="Collect Final Outputs", layout="wide")
    st.title("Collect Final Lipstick Outputs")

    base_dir = Path(__file__).resolve().parent
    outputs_dir = base_dir / "outputs"

    survey_path = base_dir / "csv" / "survey.csv"
    age_primary = base_dir / "csv" / "survey color.csv"
    age_fallback = base_dir / "csv" / "survey.csv"
    age_path = age_primary if age_primary.exists() else age_fallback

    st.caption(f"Overall source: {survey_path}")
    st.caption(f"Age source: {age_path}")

    if not survey_path.exists():
        st.error(f"Missing required file: {survey_path}")
        return

    try:
        overall = analyze_overall_survey(survey_path)
        age = analyze_age_color_brand(age_path)
    except Exception as exc:
        st.error(f"Failed to analyze CSVs: {exc}")
        return

    c1, c2 = st.columns(2)
    with c1:
        if not overall.color_counts.empty:
            top = overall.color_counts.iloc[0]
            st.metric("Most Liked Color", str(top["color"]), f"{int(top['count'])} mentions")
        else:
            st.metric("Most Liked Color", "N/A")

    with c2:
        if not overall.brand_counts.empty:
            top = overall.brand_counts.iloc[0]
            st.metric("Most Liked Brand", str(top["brand"]), f"{int(top['count'])} mentions")
        else:
            st.metric("Most Liked Brand", "N/A")

    st.divider()

    st.subheader("Overall Top Colors")
    st.dataframe(overall.color_counts, hide_index=True, use_container_width=True)

    st.subheader("Overall Top Brands")
    st.dataframe(overall.brand_counts, hide_index=True, use_container_width=True)

    st.subheader("Age Group Profiles")
    st.dataframe(age.age_profiles, hide_index=True, use_container_width=True)

    st.subheader("Age Group Counts")
    st.dataframe(age.age_counts, hide_index=True, use_container_width=True)

    st.divider()

    st.subheader("Export")
    st.caption("You can download the outputs here, or write them to the `outputs/` folder on disk.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "Download overall_top_colors.csv",
            data=overall.color_counts.to_csv(index=False, encoding="utf-8-sig"),
            file_name="overall_top_colors.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download overall_top_brands.csv",
            data=overall.brand_counts.to_csv(index=False, encoding="utf-8-sig"),
            file_name="overall_top_brands.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_b:
        st.download_button(
            "Download age_group_profiles.csv",
            data=age.age_profiles.to_csv(index=False, encoding="utf-8-sig"),
            file_name="age_group_profiles.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download age_group_counts.csv",
            data=age.age_counts.to_csv(index=False, encoding="utf-8-sig"),
            file_name="age_group_counts.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_c:
        if st.button("Write Files To outputs/", use_container_width=True, type="primary"):
            outputs_dir.mkdir(parents=True, exist_ok=True)
            overall.color_counts.to_csv(outputs_dir / "overall_top_colors.csv", index=False, encoding="utf-8-sig")
            overall.brand_counts.to_csv(outputs_dir / "overall_top_brands.csv", index=False, encoding="utf-8-sig")
            age.age_profiles.to_csv(outputs_dir / "age_group_profiles.csv", index=False, encoding="utf-8-sig")
            age.age_counts.to_csv(outputs_dir / "age_group_counts.csv", index=False, encoding="utf-8-sig")
            st.success(f"Wrote CSVs to: {outputs_dir}")


if __name__ == "__main__":
    main()

