from __future__ import annotations

from pathlib import Path

import pandas as pd

from lipstick_analysis_core import analyze_age_color_brand, analyze_overall_survey


def _safe_write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _render_summary_md(
    *,
    overall_colors: pd.DataFrame,
    overall_brands: pd.DataFrame,
    age_profiles: pd.DataFrame,
    age_counts: pd.DataFrame,
    used_survey_path: Path,
    used_age_path: Path,
) -> str:
    def top_row(df: pd.DataFrame, key: str) -> str:
        if df.empty:
            return "N/A"
        return f"{df.iloc[0][key]} ({int(df.iloc[0]['count'])})"

    lines: list[str] = []
    lines.append("# Lipstick Analysis (Collected Outputs)")
    lines.append("")
    lines.append(f"- Overall survey source: `{used_survey_path.as_posix()}`")
    lines.append(f"- Age survey source: `{used_age_path.as_posix()}`")
    lines.append("")
    lines.append("## Overall Favorites")
    lines.append(f"- Most liked color: {top_row(overall_colors, 'color')}")
    lines.append(f"- Most liked brand: {top_row(overall_brands, 'brand')}")
    lines.append("")
    lines.append("## Age Group Summary")
    if age_counts.empty:
        lines.append("- No age responses found.")
    else:
        lines.append(f"- Age groups: {len(age_counts)}")
        total = int(age_counts["count"].sum())
        lines.append(f"- Total responses: {total}")
    lines.append("")
    lines.append("## Files Written")
    lines.append("- `outputs/overall_top_colors.csv`")
    lines.append("- `outputs/overall_top_brands.csv`")
    lines.append("- `outputs/age_group_profiles.csv`")
    lines.append("- `outputs/age_group_counts.csv`")
    lines.append("- `outputs/final_summary.md`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    outputs_dir = base_dir / "outputs"

    survey_path = base_dir / "csv" / "survey.csv"
    if not survey_path.exists():
        raise FileNotFoundError(f"Missing required file: {survey_path}")

    age_path_primary = base_dir / "csv" / "survey color.csv"
    age_path_fallback = base_dir / "csv" / "survey.csv"
    age_path = age_path_primary if age_path_primary.exists() else age_path_fallback

    overall = analyze_overall_survey(survey_path)
    age = analyze_age_color_brand(age_path)

    _safe_write_csv(overall.color_counts, outputs_dir / "overall_top_colors.csv")
    _safe_write_csv(overall.brand_counts, outputs_dir / "overall_top_brands.csv")
    _safe_write_csv(age.age_profiles, outputs_dir / "age_group_profiles.csv")
    _safe_write_csv(age.age_counts, outputs_dir / "age_group_counts.csv")

    summary_md = _render_summary_md(
        overall_colors=overall.color_counts,
        overall_brands=overall.brand_counts,
        age_profiles=age.age_profiles,
        age_counts=age.age_counts,
        used_survey_path=survey_path,
        used_age_path=age_path,
    )
    (outputs_dir / "final_summary.md").write_text(summary_md, encoding="utf-8")

    print(f"Wrote outputs to: {outputs_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

