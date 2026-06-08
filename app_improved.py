
# Ver2 完全版
import requests
import streamlit as st
import pandas as pd
import folium
import math
from pathlib import Path
from streamlit_folium import st_folium
from datetime import datetime, timedelta

st.set_page_config(page_title="体感地図プロジェクト", layout="wide")

CSV_FILE = "locations.csv"

REVIEW_FILE = "reviews.csv"

if not Path(REVIEW_FILE).exists():
    pd.DataFrame(
        columns=[
            "place",
            "stress",
            "review"
        ]
    ).to_csv(
        REVIEW_FILE,
        index=False
    )

def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def geocode_address(address):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "mental-map-app"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=5
        )

        data = response.json()

        if len(data) > 0:

            return (
                float(data[0]["lat"]),
                float(data[0]["lon"])
            )

    except:
        pass

    return None, None

if not Path(CSV_FILE).exists():
    pd.DataFrame(
        columns=["name","category","lat","lon","duty","crowd","fun"]
    ).to_csv(CSV_FILE,index=False)

df = pd.read_csv(CSV_FILE)

if "clicked_lat" not in st.session_state:
    st.session_state.clicked_lat = 35.681236
    st.session_state.clicked_lon = 139.767125

st.title("🧠 体感地図プロジェクト")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("登録地点数", len(df))

with col2:
    review_count = len(pd.read_csv(REVIEW_FILE))
    st.metric("レビュー数", review_count)

with col3:
    st.metric(
        "ホーム候補数",
        len(df["name"].unique()) if len(df) > 0 else 0
    )

st.info("ホーム地点を基準に心理距離を可視化しています。")


with st.sidebar:

    st.header("📍地点登録")

    place_name = st.text_input(
        "場所名（例: 東京駅）"
    )

    auto_search = st.checkbox(
        "住所検索を使う",
        value=True
    )

    if auto_search and place_name:

        search_lat, search_lon = geocode_address(
            place_name
        )

        if search_lat is not None:

            st.success(
                f"取得成功\n緯度:{search_lat:.6f}\n経度:{search_lon:.6f}"
            )

            lat = search_lat
            lon = search_lon

        else:

            st.error(
                "場所が見つかりません"
            )

            lat = float(st.session_state.clicked_lat)
            lon = float(st.session_state.clicked_lon)

    else:

        lat = st.number_input(
            "緯度",
            value=float(st.session_state.clicked_lat),
            format="%.6f"
        )

        lon = st.number_input(
            "経度",
            value=float(st.session_state.clicked_lon),
            format="%.6f"
        )

    category = st.selectbox(
    "カテゴリ",
    [
        "自宅",
        "大学",
        "職場・バイト",
        "飲食店",
        "娯楽",
        "買い物",
        "その他"
    ]
)
    duty = st.slider(
        "義務感",
        1,5,3
    )

    crowd = st.slider(
        "混雑度",
        1,5,3
    )

    fun = st.slider(
        "楽しさ",
        1,5,3
    )

    if st.button(
        "地点追加",
        use_container_width=True
    ):

        if place_name:

            new_row = pd.DataFrame(
                [[
                    place_name,
                    category,
                    lat,
                    lon,
                    duty,
                    crowd,
                    fun
                ]],
            columns=[
                    "name",
                    "category",
                    "lat",
                    "lon",
                    "duty",
                    "crowd",
                    "fun"
            ]
    )

            df = pd.concat(
                [df,new_row],
                ignore_index=True
            )

            df.to_csv(
                CSV_FILE,
                index=False
            )

            st.success("保存しました")
            st.rerun()

st.subheader("登録地点")
st.dataframe(df,use_container_width=True)

if len(df)==0:
    st.warning("地点を登録してください")
    st.stop()

df["scale"] = 1 + 0.15*df["duty"] + 0.10*df["crowd"] - 0.10*df["fun"]

col1,col2 = st.columns(2)


st.subheader("心理倍率")
st.dataframe(
    df[["name","duty","crowd","fun","scale"]],
    use_container_width=True
)

distance_data=[]

distance_df = pd.DataFrame(
    distance_data,
    columns=["場所","現実距離(km)","体感距離(km)"]
)

st.subheader("📏距離比較")
st.dataframe(distance_df,use_container_width=True)

# ==================================
# レビュー投稿
# ==================================

st.divider()

st.header("📝 レビュー投稿")

place_review = st.selectbox(
    "レビュー対象",
    df["name"],
    key="review_place"
)

stress_review = st.slider(
    "ストレス度",
    1,
    5,
    3,
    key="review_stress"
)

review_text = st.text_area(
    "レビュー内容"
)

if st.button("レビュー保存", use_container_width=True):

    review_df = pd.read_csv(
        REVIEW_FILE
    )

    new_review = pd.DataFrame(
        [[
            place_review,
            stress_review,
            review_text
        ]],
        columns=[
            "place",
            "stress",
            "review"
        ]
    )

    review_df = pd.concat(
        [
            review_df,
            new_review
        ],
        ignore_index=True
    )

    review_df.to_csv(
        REVIEW_FILE,
        index=False
    )

    st.success("レビュー保存完了")
    st.rerun()
review_df = pd.read_csv(
    REVIEW_FILE
)

st.subheader(
    "保存済みレビュー"
)

for _, row in review_df.iterrows():

    with st.expander(f"📍 {row['place']}"):

        st.write(
            f"ストレス度: {row['stress']} / 5"
        )

        st.write(
            row["review"]
        )

# ==================================
# 移動シミュレーション
# ==================================

st.divider()

st.header(
    "🚶 移動シミュレーション"
)

start_place = st.selectbox(
    "出発地点",
    df["name"],
    key="start_place"
)

goal_place = st.selectbox(
    "目的地点",
    df["name"],
    key="goal_place"
)

if start_place != goal_place:

    start_row = df[
        df["name"] == start_place
    ].iloc[0]

    goal_row = df[
        df["name"] == goal_place
    ].iloc[0]

    route_distance = distance_km(
        start_row["lat"],
        start_row["lon"],
        goal_row["lat"],
        goal_row["lon"]
    )

    # 体感距離計算

    start_scale = start_row["scale"]
    goal_scale = goal_row["scale"]

    avg_scale = (
        start_scale + goal_scale
    ) / 2

    psy_distance = (
        route_distance * avg_scale
    )

    map_col1, map_col2 = st.columns(2)

    # ==================================
    # 現実ルート
    # ==================================

    with map_col1:

        st.subheader("🌎 現実ルート")

        real_map = folium.Map(
            location=[
                (start_row["lat"] + goal_row["lat"]) / 2,
                (start_row["lon"] + goal_row["lon"]) / 2
            ],
            zoom_start=12
        )

        folium.Marker(
            [start_row["lat"], start_row["lon"]],
            popup=f"出発: {start_place}",
            tooltip=start_place,
            icon=folium.Icon(color="green")
        ).add_to(real_map)

        folium.Marker(
            [goal_row["lat"], goal_row["lon"]],
            popup=f"目的地: {goal_place}",
            tooltip=goal_place,
            icon=folium.Icon(color="red")
        ).add_to(real_map)

        folium.PolyLine(
            [
                [start_row["lat"], start_row["lon"]],
                [goal_row["lat"], goal_row["lon"]]
            ],
            color="blue",
            weight=5
        ).add_to(real_map)

        st_folium(
            real_map,
            width=600,
            height=400,
            key="route_real"
        )

    # ==================================
    # 心理ルート
    # ==================================

    with map_col2:

        st.subheader("🧠 心理ルート")

        start_psy_lat = start_row["lat"]
        start_psy_lon = start_row["lon"]

        goal_psy_lat = (
            start_row["lat"]
            + (goal_row["lat"] - start_row["lat"])
            * avg_scale
        )

        goal_psy_lon = (
            start_row["lon"]
            + (goal_row["lon"] - start_row["lon"])
            * avg_scale
        )

        psy_map = folium.Map(
            location=[
                (start_psy_lat + goal_psy_lat) / 2,
                (start_psy_lon + goal_psy_lon) / 2
            ],
            zoom_start=12
        )

        folium.Marker(
            [start_psy_lat, start_psy_lon],
            popup=f"出発: {start_place}",
            icon=folium.Icon(color="green")
        ).add_to(psy_map)

        folium.Marker(
            [goal_psy_lat, goal_psy_lon],
            popup=f"目的地: {goal_place}",
            icon=folium.Icon(color="red")
        ).add_to(psy_map)

        folium.PolyLine(
            [
                [start_psy_lat, start_psy_lon],
                [goal_psy_lat, goal_psy_lon]
            ],
            color="red",
            weight=5
        ).add_to(psy_map)

        st_folium(
            psy_map,
            width=600,
            height=400,
            key="route_psy"
        )

        

    walk_minutes = int(
        (route_distance / 4.8) * 60
    )

    arrival_time = (
        datetime.now()
        + timedelta(minutes=walk_minutes)
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "現実距離(km)",
            f"{route_distance:.2f}"
        )

    with col2:
        st.metric(
            "体感距離(km)",
            f"{psy_distance:.2f}"
        )

    with col3:
        st.metric(
            "体感倍率",
            f"{avg_scale:.2f}倍"
        )

    with col4:
        st.metric(
            "徒歩時間",
            f"{walk_minutes}分"
        )

    with col5:
        st.metric(
            "到着予想",
            arrival_time.strftime("%H:%M")
        )

# ==================================
# CSV出力
# ==================================

st.divider()

st.header(
    "📥 データ出力"
)

col1, col2 = st.columns(2)

with col1:

    with open(CSV_FILE, "rb") as f:

        st.download_button(
            "📍 locations.csv",
            f,
            "locations.csv",
            use_container_width=True
        )

with col2:

    with open(REVIEW_FILE, "rb") as f:

        st.download_button(
            "📝 reviews.csv",
            f,
            "reviews.csv",
            use_container_width=True
        )



st.subheader("地点削除")

delete_target = st.selectbox(
    "削除する地点",
    df["name"]
)

if st.button("削除", use_container_width=True):
    df = df[df["name"] != delete_target]
    df.to_csv(CSV_FILE,index=False)
    st.rerun()
