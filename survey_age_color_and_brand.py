import pandas as pd
import streamlit as st
from collections import Counter
import re


def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def split_values(text):
    if pd.isna(text):
        return []
    text = normalize_text(text)
    if not text:
        return []
    values = [item.strip() for item in text.split(",") if item.strip()]
    return [v for v in values if v not in {"no", "black", "white", "yellow"}]


def canonical_brand(brand):
    brand = normalize_text(brand)
    if not brand:
        return ""
    mappings = {
        "mac": "mac cosmetics",
        "maccosmetics": "mac cosmetics",
        "rom&nd": "rom&nd",
        "romnd": "rom&nd",
        "blackrouge": "black rouge",
        "3ce": "3ce",
        "maybelline": "maybelline",
        "revlon": "revlon",
        "dior": "dior",
        "chanel": "chanel",
        "novo": "novo",
        "heartyheart": "hearty heart",
        "bella": "bella",
    }
    return mappings.get(brand, brand)


def age_sort_key(age_value: str):
    age = normalize_text(age_value)
    if age == "unknown":
        return (10_000, 0)
    numbers = re.findall(r"\d+", age)
    num = int(numbers[0]) if numbers else 10_000
    if "under" in age:
        return (num - 1, 0)
    if "over" in age or "+" in age:
        return (num + 0.5, 0)
    return (num, 0)


def analyze(data_path: str):
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.strip()

    if "Age_range" not in df.columns:
        raise ValueError("Missing column: Age_range")
    if "Favorite lipstick color family" not in df.columns:
        raise ValueError("Missing column: Favorite lipstick color family")
    if "brand  use most" not in df.columns:
        raise ValueError("Missing column: brand  use most")
    if "lipstick finish" not in df.columns:
        raise ValueError("Missing column: lipstick finish")

    df["Age_range"] = df["Age_range"].fillna("Unknown")

    groupby_age = df.groupby("Age_range")
    age_counts = groupby_age.size()
    age_order = sorted(age_counts.index, key=age_sort_key)
    age_counts = age_counts.reindex(age_order)

    def top_or_other(counter: Counter):
        if not counter:
            return "other"
        item, _ = counter.most_common(1)[0]
        return item

    def top_n_list(counter: Counter, n: int):
        if not counter:
            return "other"
        items = [name for name, _ in counter.most_common(n)]
        return ", ".join(items)

    age_profiles = []
    for age, sub in groupby_age:
        color_cnt = Counter()
        brand_cnt = Counter()
        finish_cnt = Counter()
        for _, r in sub.iterrows():
            color_cnt.update(split_values(r.get("Favorite lipstick color family", "")))
            for b in split_values(r.get("brand  use most", "")):
                cb = canonical_brand(b)
                if cb:
                    brand_cnt[cb] += 1
            finish = normalize_text(r.get("lipstick finish", ""))
            if finish:
                finish_cnt[finish] += 1

        age_profiles.append({
            "Age range": age,
            "Top colors": top_n_list(color_cnt, 3),
            "Top brands": top_n_list(brand_cnt, 3),
            "Top finishes": top_n_list(finish_cnt, 3),
        })

    age_profiles_df = pd.DataFrame(age_profiles)
    age_profiles_df = age_profiles_df.sort_values("Age range", key=lambda s: s.map(age_sort_key))

    return {
        "age_counts": age_counts,
        "age_profiles": age_profiles_df,
    }


def main():
    st.set_page_config(page_title="Survey Color Dashboard", layout="wide")
    st.title("Lipstick Survey (Color) Dashboard")

    data_path = "csv/survey color.csv"
   

    try:
        stats = analyze(data_path)
    except Exception as e:
        st.error(f"Unable to read data: {e}")
        return

    

    st.header("1. Top color & brand by age group")
    st.dataframe(stats["age_profiles"], hide_index=True)


if __name__ == "__main__":
    main()
