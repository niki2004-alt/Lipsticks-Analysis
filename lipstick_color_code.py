import pandas as pd
import requests
from io import BytesIO
from colorthief import ColorThief
from tqdm import tqdm

# tqdm ကို pandas apply နဲ့သုံးဖို့ enable
tqdm.pandas()

# 1. CSV ဖိုင်ကို load
df = pd.read_csv("lipstick_urls.csv")

# 2. Dominant color ထုတ်တဲ့ function
def get_dominant_color(img_url):
    try:
        response = requests.get(img_url, timeout=10)
        if response.status_code == 200:
            color_thief = ColorThief(BytesIO(response.content))
            dominant_color = color_thief.get_color(quality=1)
            return '#%02x%02x%02x' % dominant_color
    except Exception as e:
        print(f"\nError with {img_url}: {e}")
    return None

# 3. Progress bar နဲ့ process
df['color_code'] = df['image_url'].progress_apply(get_dominant_color)

# 4. Export
df.to_csv("lipstick_with_colors.csv", index=False)

print("\nExported lipstick_with_colors.csv with color codes!")