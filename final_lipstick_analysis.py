import re
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from lipstick_analysis_core import analyze_age_color_brand

BASE_DIR = Path(__file__).resolve().parent
SURVEY_CSV = BASE_DIR / "csv" / "survey.csv"
SURVEY_COLOR_CSV = BASE_DIR / "csv" / "survey color.csv"
MARKET1_CSV = BASE_DIR / "csv" / "market1.csv"
MARKET2_CSV = BASE_DIR / "csv" / "market2.csv"
MARKET_COLOR_CODES_CSV = BASE_DIR / "csv" / "market_color_codes.csv"


INVALID_BRANDS = {"", "no", "nothing"}
BRAND_CANONICAL = {
    "go go tales": "gogo tales",
    "mac": "mac cosmetics",
}

COLOR_KEYWORDS = {
    "red",
    "pink",
    "coral",
    "nude",
    "brown",
    "orange",
    "berry",
    "rose",
    "mauve",
    "peach",
    "wine",
    "plum",
}

MARKET_BRAND_ALIASES = {
    "romnd": "rom&nd",
    "romand": "rom&nd",
    "mac": "mac cosmetics",
    "maccosmetics": "mac cosmetics",
    "m a c": "mac cosmetics",
}

CHART_COLOR_MAP = {
    "red": "#e53935",
    "orange": "#fb8c00",
    "pink": "#ec407a",
    "coral": "#ff7f50",
    "nude": "#c49a6c",
    "brown": "#8d6e63",
    "berry": "#8e244d",
    "rose": "#d81b60",
    "mauve": "#8e7aa8",
    "peach": "#ffb07c",
    "wine": "#722f37",
    "plum": "#8e4585",
}

MARKET_COLOR_COLUMNS = [
    "sold_color_code_hex1",
    "sold_color_code_hex2",
    "sold_color_code_hex3",
]


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def split_multi(value: str) -> list[str]:
    cleaned = normalize_text(value)
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def to_title(value: str) -> str:
    return " ".join(p.capitalize() for p in value.split())


def canonical_brand(value: str) -> str:
    value = normalize_text(value)
    alnum = re.sub(r"[^a-z0-9]+", "", value)
    if alnum == "mac":
        return "mac cosmetics"

    mapped = MARKET_BRAND_ALIASES.get(alnum)
    if mapped:
        return mapped

    mapped = BRAND_CANONICAL.get(value)
    if mapped:
        return mapped
    return value


def parse_float(value: str) -> float | None:
    text = normalize_text(str(value)).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_count(value: str) -> int:
    text = normalize_text(str(value)).replace(",", "")
    if not text:
        return 0
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return 0
    number = float(match.group(0))
    if "k" in text:
        number *= 1000
    elif "m" in text:
        number *= 1_000_000
    return int(round(number))


def normalize_hex(value: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.startswith("#"):
        text = f"#{text}"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return None
    return text.upper()


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    return (
        int(hex_code[1:3], 16),
        int(hex_code[3:5], 16),
        int(hex_code[5:7], 16),
    )


def srgb_to_linear(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def color_distance(hex_a: str, hex_b: str) -> float:
    rgb_a = hex_to_rgb(hex_a)
    rgb_b = hex_to_rgb(hex_b)
    la = [srgb_to_linear(c) for c in rgb_a]
    lb = [srgb_to_linear(c) for c in rgb_b]
    return sum((la[i] - lb[i]) ** 2 for i in range(3))


def map_hex_to_color(hex_code: str) -> str | None:
    normalized = normalize_hex(hex_code)
    if not normalized:
        return None
    best_color = None
    best_distance = None
    for color_name, ref_hex in CHART_COLOR_MAP.items():
        distance = color_distance(normalized, ref_hex)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_color = color_name
    return best_color


def extract_colors(text: str) -> set[str]:
    normalized = normalize_text(text)
    found = set()
    for color in COLOR_KEYWORDS:
        if re.search(rf"\b{re.escape(color)}\b", normalized):
            found.add(color)
    return found


def load_market_color_codes() -> pd.DataFrame:
    if not MARKET_COLOR_CODES_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(
        MARKET_COLOR_CODES_CSV,
        encoding="utf-8-sig",
        engine="python",
        on_bad_lines="skip",
    )
    counter = Counter()

    for _, row in df.iterrows():
        for col in MARKET_COLOR_COLUMNS:
            color_hex = row.get(col)
            color_name = map_hex_to_color(color_hex)
            if color_name:
                counter[color_name] += 1

    if not counter:
        return pd.DataFrame()

    total = sum(counter.values())
    color_df = pd.DataFrame(
        [
            {
                "color": to_title(color),
                "count": count,
                "probability": count / total,
                "hex": CHART_COLOR_MAP.get(color, "#9e9e9e"),
            }
            for color, count in counter.most_common()
        ]
    )
    return color_df


def load_market_data() -> pd.DataFrame:
    rows = []

    if MARKET1_CSV.exists():
        m1 = pd.read_csv(MARKET1_CSV, encoding="utf-8-sig")
        for _, row in m1.iterrows():
            brand = canonical_brand(str(row.get("brandName", "")))
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            rows.append(
                {
                    "market": "market1",
                    "brand": brand,
                    "name": name,
                    "price": parse_float(row.get("price", "")),
                    "rating": parse_float(row.get("ratingScore", "")),
                    "sold_count": parse_count(row.get("itemSoldCntShow", "")),
                    "colors_in_name": extract_colors(name),
                }
            )

    if MARKET2_CSV.exists():
        m2 = pd.read_csv(MARKET2_CSV, encoding="utf-8-sig")
        for _, row in m2.iterrows():
            name = str(row.get("item_basic_name", "")).strip()
            if not name:
                continue

            raw_brand = str(row.get("item_basic_brand", "")).strip()
            if not raw_brand and normalize_text(name).startswith("mac"):
                raw_brand = "mac"
            brand = canonical_brand(raw_brand)

            rows.append(
                {
                    "market": "market2",
                    "brand": brand,
                    "name": name,
                    "price": parse_float(row.get("item_basic_price", "")),
                    "rating": parse_float(row.get("item_basic_rating_star", "")),
                    "sold_count": parse_count(row.get("item_basic_display_sold_count_text", "")),
                    "colors_in_name": extract_colors(name),
                }
            )

    return pd.DataFrame(rows)


def match_products(
    market_df: pd.DataFrame, preferred_brands: list[str], preferred_colors: list[str]
) -> pd.DataFrame:
    if market_df.empty:
        return market_df

    pref_brands = {canonical_brand(b) for b in preferred_brands}
    pref_colors = {normalize_text(c) for c in preferred_colors}

    def score_row(row: pd.Series) -> int:
        score = 0
        if row["brand"] in pref_brands:
            score += 2
        if row["colors_in_name"] & pref_colors:
            score += 1
        return score

    scored = market_df.copy()
    scored["match_score"] = scored.apply(score_row, axis=1)
    scored = scored[scored["match_score"] > 0].copy()
    if scored.empty:
        return scored

    scored["matched_colors"] = scored["colors_in_name"].apply(
        lambda colors: ", ".join(to_title(c) for c in sorted(colors & pref_colors))
    )
    scored["brand"] = scored["brand"].apply(to_title)
    scored["price"] = scored["price"].fillna(0.0)
    scored["rating"] = scored["rating"].fillna(0.0)
    scored = scored.sort_values(
        by=["match_score", "sold_count", "rating"], ascending=[False, False, False]
    )
    return scored


def analyze_survey(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path, encoding="utf-8-sig")

    color_col = None
    brand_col = None
    for col in df.columns:
        key = normalize_text(col)
        if key == "color":
            color_col = col
        elif key == "use most":
            brand_col = col

    if not color_col or not brand_col:
        raise ValueError("survey.csv must include 'color' and 'use most' columns")

    color_counter = Counter()
    brand_counter = Counter()

    for _, row in df.iterrows():
        for color in split_multi(str(row.get(color_col, ""))):
            color_counter[color] += 1

        for brand in split_multi(str(row.get(brand_col, ""))):
            brand = canonical_brand(brand)
            if brand not in INVALID_BRANDS:
                brand_counter[brand] += 1

    color_df = pd.DataFrame(
        [{"color": to_title(k), "count": v} for k, v in color_counter.most_common()]
    )
    brand_df = pd.DataFrame(
        [{"brand": to_title(k), "count": v} for k, v in brand_counter.most_common()]
    )
    return color_df, brand_df


def main() -> None:
    st.set_page_config(page_title="Final Lipstick Analysis", layout="wide")
    st.title("Final Lipstick Analysis")
    st.caption("Source: survey.csv")

    if not SURVEY_CSV.exists():
        st.error(f"File not found: {SURVEY_CSV}")
        return

    try:
        color_df, brand_df = analyze_survey(SURVEY_CSV)
    except Exception as exc:
        st.error(f"Failed to analyze survey.csv: {exc}")
        return

    if color_df.empty or brand_df.empty:
        st.warning("No valid color/brand data found.")
        return

    top_color = color_df.iloc[0]
    top_brand = brand_df.iloc[0]

    col1, col2 = st.columns(2)
    col1.metric("Most Liked Color", f"{top_color['color']}", f"{int(top_color['count'])} mentions")
    col2.metric("Most Liked Brand", f"{top_brand['brand']}", f"{int(top_brand['count'])} mentions")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Colors")
        top_colors_df = color_df.head(10).copy()
        top_colors_df["hex"] = top_colors_df["color"].apply(
            lambda c: CHART_COLOR_MAP.get(normalize_text(c), "#9e9e9e")
        )
        top_colors_chart = (
            alt.Chart(top_colors_df)
            .mark_bar()
            .encode(
                x=alt.X("color:N", sort=top_colors_df["color"].tolist(), title="Color"),
                y=alt.Y("count:Q", title="Mentions"),
                color=alt.Color("hex:N", scale=None, legend=None),
                tooltip=["color", "count"],
            )
        )
        st.altair_chart(top_colors_chart, use_container_width=True)
        st.dataframe(color_df, use_container_width=True)

    with c2:
        st.subheader("Top Brands")
        st.bar_chart(brand_df.head(10).set_index("brand")["count"])
        st.dataframe(brand_df, use_container_width=True)

    st.subheader("Survey: Age vs Color vs Brand")
    age_source = SURVEY_COLOR_CSV if SURVEY_COLOR_CSV.exists() else SURVEY_CSV
    try:
        age_stats = analyze_age_color_brand(age_source)
    except Exception as exc:
        st.warning(f"Unable to analyze age/color/brand survey from {age_source.name}: {exc}")
    else:
        st.caption(f"Source: {age_source.name}")
        profiles_view = age_stats.age_profiles.drop(columns=["Responses"], errors="ignore")
        st.dataframe(profiles_view, hide_index=True, use_container_width=True)

    st.subheader("Market Color Code Distribution")
    market_color_df = load_market_color_codes()
    if market_color_df.empty:
        st.warning("market_color_codes.csv was not found or has no valid hex values.")
    else:
        market_color_chart = (
            alt.Chart(market_color_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "color:N",
                    sort=market_color_df["color"].tolist(),
                    title="Color",
                ),
                y=alt.Y(
                    "probability:Q",
                    axis=alt.Axis(format="~%"),
                    title="Probability",
                ),
                color=alt.Color("hex:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("color:N", title="Color"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("probability:Q", title="Probability", format="~%"),
                ],
            )
        )
        st.altair_chart(market_color_chart, use_container_width=True)
        st.dataframe(market_color_df, use_container_width=True)

    st.subheader("Survey Match With Market1 + Market2")
    default_brands = brand_df["brand"].head(3).tolist()
    default_colors = color_df["color"].head(3).tolist()

    selected_brands = st.multiselect(
        "Preferred Brands (from survey)",
        options=brand_df["brand"].tolist(),
        default=default_brands,
    )
    selected_colors = st.multiselect(
        "Preferred Colors (from survey)",
        options=color_df["color"].tolist(),
        default=default_colors,
    )

    market_df = load_market_data()
    if market_df.empty:
        st.warning("market1.csv and market2.csv were not found or have no valid rows.")
        return

    matched_df = match_products(market_df, selected_brands, selected_colors)
    if matched_df.empty:
        st.info("No product matches found for current filters.")
        return

    st.metric("Matched Products", int(len(matched_df)))
    bar_col1, bar_col2 = st.columns(2)
    with bar_col1:
        st.caption("Matched Products by Brand")
        brand_counts = (
            matched_df.groupby("brand", as_index=False)["name"]
            .count()
            .rename(columns={"name": "count"})
            .sort_values("count", ascending=False)
            .head(10)
            .set_index("brand")
        )
        st.bar_chart(brand_counts["count"])

    with bar_col2:
        st.caption("Matched Products by Market")
        market_counts = (
            matched_df.groupby("market", as_index=False)["name"]
            .count()
            .rename(columns={"name": "count"})
            .sort_values("count", ascending=False)
            .set_index("market")
        )
        st.bar_chart(market_counts["count"])

    selected_color_norm = [normalize_text(c) for c in selected_colors]
    color_count_map = {c: 0 for c in selected_color_norm}
    for colors in matched_df["colors_in_name"]:
        for color in colors:
            if color in color_count_map:
                color_count_map[color] += 1

    if color_count_map:
        st.caption("Each Selected Related Color")
        color_chart_df = pd.DataFrame(
            [
                {
                    "color": to_title(c),
                    "count": color_count_map[c],
                    "hex": CHART_COLOR_MAP.get(c, "#9e9e9e"),
                }
                for c in selected_color_norm
            ]
        )
        color_chart = (
            alt.Chart(color_chart_df)
            .mark_bar()
            .encode(
                x=alt.X("color:N", sort=selected_colors, title="Color"),
                y=alt.Y("count:Q", title="Matched Product Count"),
                color=alt.Color("hex:N", scale=None, legend=None),
                tooltip=["color", "count"],
            )
        )
        st.altair_chart(color_chart, use_container_width=True)

    display_cols = [
        "market",
        "brand",
        "name",
        "match_score",
        "price",
        "rating",
        "sold_count",
    ]
    st.dataframe(matched_df[display_cols].head(200), use_container_width=True)


if __name__ == "__main__":
    main()
