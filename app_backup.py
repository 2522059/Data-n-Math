import streamlit as st
import pandas as pd
import folium
import numpy as np
from pathlib import Path
from streamlit_folium import st_folium

st.set_page_config(
    page_title="体感地図プロジェクト",
    layout="wide"
)

CSV_FILE = "locations.csv"

# =====================
# CSV初期化
# =====================

if not Path(CSV_FILE).exists():

    pd.DataFrame(
        columns=[
            "name",
            "lat",
            "lon",
            "duty",
            "crowd",
            "fun"
        ]
    ).to_csv(CSV_FILE, index=False)

df = pd.read_csv(CSV_FILE)

# =====================
# タイトル
# =====================

st.title("🧠 体感地図プロジェクト")

st.markdown("""
### 概要

- 左：現実地図
- 右：心理地図
- 義務感が高いほど遠くなる
- 楽しい場所ほど近くなる
""")

# =====================
# サイドバー
# =====================

with st.sidebar:

    st.header("📍地点登録")

    place_name = st.text_input("場所名")

    lat = st.number_input(
        "緯度",
        value=35.681236,
        format="%.6f"
    )

    lon = st.number_input(
        "経度",
        value=139.767125,
        format="%.6f"
    )

    duty = st.slider(
        "義務感",
        1,
        5,
        3
    )

    crowd = st.slider(
        "混雑度",
        1,
        5,
        3
    )

    fun = st.slider(
        "楽しさ",
        1,
        5,
        3
    )

    if st.button("地点追加"):

        if place_name != "":

            new_row = pd.DataFrame(
                [[
                    place_name,
                    lat,
                    lon,
                    duty,
                    crowd,
                    fun
                ]],
                columns=[
                    "name",
                    "lat",
                    "lon",
                    "duty",
                    "crowd",
                    "fun"
                ]
            )

            df = pd.concat(
                [df, new_row],
                ignore_index=True
            )

            df.to_csv(
                CSV_FILE,
                index=False
            )

            st.success("保存しました")
            st.rerun()

# =====================
# データ確認
# =====================

st.subheader("登録地点")

st.dataframe(
    df,
    use_container_width=True
)

# =====================
# 地点が無い場合
# =====================

if len(df) == 0:

    st.warning("地点を登録してください")
    st.stop()

# =====================
# ホーム地点
# =====================

home = st.selectbox(
    "🏠 ホーム地点",
    df["name"]
)

home_row = df[df["name"] == home].iloc[0]

home_lat = home_row["lat"]
home_lon = home_row["lon"]

# =====================
# 心理倍率
# =====================

df["scale"] = (
    1
    + 0.15 * df["duty"]
    + 0.10 * df["crowd"]
    - 0.10 * df["fun"]
)

# =====================
# 座標変換
# =====================

psy_lat = []
psy_lon = []

for _, row in df.iterrows():

    scale = row["scale"]

    dlat = row["lat"] - home_lat
    dlon = row["lon"] - home_lon

    new_lat = home_lat + scale * dlat
    new_lon = home_lon + scale * dlon

    psy_lat.append(new_lat)
    psy_lon.append(new_lon)

df["psy_lat"] = psy_lat
df["psy_lon"] = psy_lon

# =====================
# 地図
# =====================

col1, col2 = st.columns(2)

# -----------------
# 現実地図
# -----------------

with col1:

    st.subheader("🌎 現実地図")

    real_map = folium.Map(
        location=[
            home_lat,
            home_lon
        ],
        zoom_start=12
    )

    for _, row in df.iterrows():

        color = "red" if row["name"] == home else "blue"

        folium.Marker(
            [
                row["lat"],
                row["lon"]
            ],
            popup=row["name"],
            tooltip=row["name"],
            icon=folium.Icon(
                color=color
            )
        ).add_to(real_map)

    st_folium(
        real_map,
        width=700,
        height=500
    )

# -----------------
# 心理地図
# -----------------

with col2:

    st.subheader("🧠 心理地図")

    psy_map = folium.Map(
        location=[
            home_lat,
            home_lon
        ],
        zoom_start=12
    )

    for _, row in df.iterrows():

        color = "red" if row["name"] == home else "green"

        folium.Marker(
            [
                row["psy_lat"],
                row["psy_lon"]
            ],
            popup=(
                f"{row['name']}<br>"
                f"倍率:{row['scale']:.2f}"
            ),
            tooltip=row["name"],
            icon=folium.Icon(
                color=color
            )
        ).add_to(psy_map)

    st_folium(
        psy_map,
        width=700,
        height=500
    )

# =====================
# 倍率表示
# =====================

st.subheader("心理倍率")

st.dataframe(
    df[
        [
            "name",
            "duty",
            "crowd",
            "fun",
            "scale"
        ]
    ],
    use_container_width=True
)

# =====================
# 削除機能
# =====================

st.subheader("地点削除")

delete_target = st.selectbox(
    "削除する地点",
    df["name"]
)

if st.button("削除"):

    df = df[
        df["name"] != delete_target
    ]

    df.to_csv(
        CSV_FILE,
        index=False
    )

    st.rerun()