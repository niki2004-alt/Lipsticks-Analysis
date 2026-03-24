from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# Keep this module Streamlit-free so it can be used by both dashboards and CLI scripts.


def normalize_text(value: object) -> str:
    text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def split_csv_list(value: object) -> list[str]:
    """Split 'a, b, c' style multi-select cells into normalized tokens."""
    cleaned = normalize_text(value)
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def canonical_brand(value: object) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""

    # Normalize alphanumeric-only variants first.
    alnum = re.sub(r"[^a-z0-9]+", "", raw)
    aliases = {
        "mac": "mac cosmetics",
        "maccosmetics": "mac cosmetics",
        "m a c": "mac cosmetics",
        "romnd": "rom&nd",
        "romand": "rom&nd",
        "blackrouge": "black rouge",
        "gogotales": "gogo tales",
        "heartyheart": "hearty heart",
    }
    if alnum in aliases:
        return aliases[alnum]

    # Also map the full text (with spaces/punctuation) for a few common cases.
    full_map = {
        "mac": "mac cosmetics",
        "romnd": "rom&nd",
        "rom&nd": "rom&nd",
    }
    return full_map.get(raw, raw)


def age_sort_key(age_value: object) -> tuple[float, int]:
    age = normalize_text(age_value)
    if not age or age == "unknown":
        return (10_000.0, 0)

    numbers = re.findall(r"\d+", age)
    num = float(numbers[0]) if numbers else 10_000.0

    if "under" in age:
        return (num - 1.0, 0)
    if "over" in age or "+" in age:
        return (num + 0.5, 0)
    return (num, 0)


def _find_col(df: pd.DataFrame, *, exact_normalized: set[str]) -> str | None:
    for col in df.columns:
        if normalize_text(col) in exact_normalized:
            return col
    return None


@dataclass(frozen=True)
class OverallSurveyResults:
    color_counts: pd.DataFrame
    brand_counts: pd.DataFrame


def analyze_overall_survey(survey_csv: Path) -> OverallSurveyResults:
    """
    survey.csv contains columns like:
      - color  (favorite color family)
      - use most (brand)
    We auto-detect those columns by normalized header text.
    """
    df = pd.read_csv(survey_csv, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]

    color_col = _find_col(df, exact_normalized={"color"})
    brand_col = _find_col(df, exact_normalized={"use most"})
    if not color_col or not brand_col:
        raise ValueError("survey.csv must include columns 'color' and 'use most' (case/space-insensitive)")

    invalid_brands = {"", "no", "nothing"}
    color_counter: Counter[str] = Counter()
    brand_counter: Counter[str] = Counter()

    for _, row in df.iterrows():
        for color in split_csv_list(row.get(color_col, "")):
            color_counter[color] += 1
        for brand in split_csv_list(row.get(brand_col, "")):
            b = canonical_brand(brand)
            if b and b not in invalid_brands:
                brand_counter[b] += 1

    color_df = pd.DataFrame(
        [{"color": _to_title(k), "count": int(v)} for k, v in color_counter.most_common()]
    )
    brand_df = pd.DataFrame(
        [{"brand": _to_title(k), "count": int(v)} for k, v in brand_counter.most_common()]
    )
    return OverallSurveyResults(color_counts=color_df, brand_counts=brand_df)


@dataclass(frozen=True)
class AgeSurveyResults:
    age_counts: pd.DataFrame
    age_profiles: pd.DataFrame


def analyze_age_color_brand(survey_csv: Path) -> AgeSurveyResults:
    """
    Supports both:
      - csv/survey color.csv (Age_range, Favorite lipstick color family, brand  use most, lipstick finish)
      - csv/survey.csv (Age, color, use most, Favorite lipstick)
    """
    df = pd.read_csv(survey_csv, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]

    age_col = _find_col(df, exact_normalized={"age_range", "age range", "age"})
    # Color could be "Favorite lipstick color family" or just "color"
    color_col = _find_col(df, exact_normalized={"favorite lipstick color family", "color"})
    # Brand could be "brand  use most" or "use most"
    brand_col = _find_col(df, exact_normalized={"brand use most", "brand  use most", "use most"})
    # Finish could be "lipstick finish" or "favorite lipstick"
    finish_col = _find_col(df, exact_normalized={"lipstick finish", "favorite lipstick"})

    missing = [name for name, col in [("age", age_col), ("color", color_col), ("brand", brand_col), ("finish", finish_col)] if not col]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    df[age_col] = df[age_col].fillna("Unknown")

    # A few tokens frequently show up as non-answers in these sheets.
    drop_tokens = {"no", "white", "yellow"}

    # If someone typed a wear-color (e.g. "black") it is a valid shade family in some contexts,
    # but in our "favorite family" question it is usually a non-answer/noise.
    noise_colors = {"black"}

    profiles: list[dict[str, str]] = []

    def top_n(counter: Counter[str], n: int) -> str:
        if not counter:
            return "Other"
        items = [_to_title(name) for name, _ in counter.most_common(n)]
        return ", ".join(items)

    age_counts = (
        df.groupby(age_col, dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(age_col, key=lambda s: s.map(age_sort_key))
        .reset_index(drop=True)
    )

    for age_value, sub in df.groupby(age_col, dropna=False):
        color_cnt: Counter[str] = Counter()
        brand_cnt: Counter[str] = Counter()
        finish_cnt: Counter[str] = Counter()

        for _, r in sub.iterrows():
            for c in split_csv_list(r.get(color_col, "")):
                c_norm = normalize_text(c)
                if not c_norm or c_norm in drop_tokens or c_norm in noise_colors:
                    continue
                color_cnt[c_norm] += 1

            for b in split_csv_list(r.get(brand_col, "")):
                b_norm = canonical_brand(b)
                if b_norm and b_norm not in drop_tokens:
                    brand_cnt[b_norm] += 1

            finish = normalize_text(r.get(finish_col, ""))
            if finish and finish not in drop_tokens:
                finish_cnt[finish] += 1

        profiles.append(
            {
                "Age range": str(age_value),
                "Top colors": top_n(color_cnt, 3),
                "Top brands": top_n(brand_cnt, 3),
                "Top finishes": top_n(finish_cnt, 3),
                "Responses": str(len(sub)),
            }
        )

    profiles_df = pd.DataFrame(profiles).sort_values(
        "Age range", key=lambda s: s.map(age_sort_key)
    )

    return AgeSurveyResults(age_counts=age_counts, age_profiles=profiles_df.reset_index(drop=True))


def _to_title(value: str) -> str:
    value = normalize_text(value)
    if not value:
        return ""
    return " ".join(part.capitalize() for part in value.split())

