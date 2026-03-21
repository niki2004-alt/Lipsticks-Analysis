import pandas as pd
import streamlit as st
from collections import Counter


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
    return [item.strip() for item in text.split(",") if item.strip()]


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


def analyze(data_path: str):
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.strip()

    age_counts = df["Age range"].fillna("Unknown").value_counts()
    all_colors = []
    all_finishes = []
    all_brands = []

    for _, row in df.iterrows():
        all_colors.extend(split_values(row.get("Color", "")))
        finish = normalize_text(row.get("lipstick finish", ""))
        if finish:
            all_finishes.append(finish)
        for b in split_values(row.get("Brand", "")):
            cb = canonical_brand(b)
            if cb:
                all_brands.append(cb)

    colors = pd.DataFrame(Counter(all_colors).most_common(), columns=["color", "count"])
    finishes = pd.DataFrame(Counter(all_finishes).most_common(), columns=["finish", "count"])
    brands = pd.DataFrame(Counter(all_brands).most_common(), columns=["brand", "count"])

    age_profiles = []
    for age in age_counts.index:
        sub = df[df["Age range"] == age]
        color_cnt = Counter()
        finish_cnt = Counter()
        brand_cnt = Counter()
        for _, r in sub.iterrows():
            color_cnt.update(split_values(r.get("Color", "")))
            finish = normalize_text(r.get("lipstick finish", ""))
            if finish:
                finish_cnt[finish] += 1
            for b in split_values(r.get("Brand", "")):
                cb = canonical_brand(b)
                if cb:
                    brand_cnt[cb] += 1

        age_profiles.append({
            "Age range": age,
            "Responses": len(sub),
            "Top color": color_cnt.most_common(1)[0][0] if color_cnt else "N/A",
            "Top finish": finish_cnt.most_common(1)[0][0] if finish_cnt else "N/A",
            "Top brand": brand_cnt.most_common(1)[0][0] if brand_cnt else "N/A",
        })

    age_profiles_df = pd.DataFrame(age_profiles).sort_values("Responses", ascending=False)

    return {
        "age_counts": age_counts,
        "colors": colors,
        "finishes": finishes,
        "brands": brands,
        "age_profiles": age_profiles_df,
    }


def main():
    st.set_page_config(page_title="Survey Age/Color/Brand", layout="wide")
    st.title("Lipstick Survey Age/Color/Brand Dashboard")

    data_path = "csv/age_and_color_and_brand.csv"
    st.markdown("**Data source:** `csv/age_and_color_and_brand.csv`")

    try:
        stats = analyze(data_path)
    except Exception as e:
        st.error(f"Unable to read data: {e}")
        return

    # Age group participation section removed per request.

    st.header("2. Global preferences")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Top color")
        if not stats["colors"].empty:
            top_color = stats["colors"].iloc[0]
            st.metric("Color", top_color["color"], int(top_color["count"]))
        else:
            st.metric("Color", "N/A", 0)
    with c2:
        st.subheader("Top finish")
        if not stats["finishes"].empty:
            top_finish = stats["finishes"].iloc[0]
            st.metric("Finish", top_finish["finish"], int(top_finish["count"]))
        else:
            st.metric("Finish", "N/A", 0)
    with c3:
        st.subheader("Top brand")
        if not stats["brands"].empty:
            top_brand = stats["brands"].iloc[0]
            st.metric("Brand", top_brand["brand"], int(top_brand["count"]))
        else:
            st.metric("Brand", "N/A", 0)

    st.header("3. Age-group preference profiles")
    st.table(stats["age_profiles"])

    st.header("4. Charts")
    st.bar_chart(stats["age_counts"])

    st.write("### Top color")
    if not stats["colors"].empty:
        st.bar_chart(stats["colors"].head(1).set_index("color")[["count"]])
    else:
        st.info("No color data available.")

    st.write("### Top brand")
    if not stats["brands"].empty:
        st.bar_chart(stats["brands"].head(1).set_index("brand")[["count"]])
    else:
        st.info("No brand data available.")


if __name__ == "__main__":
    main()
