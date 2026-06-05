
# Ver2 完全版
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

if not Path(CSV_FILE).exists():
    pd.DataFrame(
        columns=["name","lat","lon","duty","crowd","fun"]
    ).to_csv(CSV_FILE,index=False)

df = pd.read_csv(CSV_FILE)

if "clicked_lat" not in st.session_state:
    st.session_state.clicked_lat = 35.681236
    st.session_state.clicked_lon = 139.767125

st.title("🧠 体感地図プロジェクト")

with st.sidebar:
    st.header("📍地点登録")

    place_name = st.text_input("場所名")

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

    duty = st.slider("義務感",1,5,3)
    crowd = st.slider("混雑度",1,5,3)
    fun = st.slider("楽しさ",1,5,3)

    if st.button("地点追加"):
        if place_name:
            new_row = pd.DataFrame([[place_name,lat,lon,duty,crowd,fun]],
                                  columns=["name","lat","lon","duty","crowd","fun"])
            df = pd.concat([df,new_row],ignore_index=True)
            df.to_csv(CSV_FILE,index=False)
            st.success("保存しました")
            st.rerun()

st.subheader("登録地点")
st.dataframe(df,use_container_width=True)

if len(df)==0:
    st.warning("地点を登録してください")
    st.stop()

home = st.selectbox("🏠 ホーム地点", df["name"])

home_row = df[df["name"]==home].iloc[0]
home_lat = home_row["lat"]
home_lon = home_row["lon"]

df["scale"] = 1 + 0.15*df["duty"] + 0.10*df["crowd"] - 0.10*df["fun"]

psy_lat=[]
psy_lon=[]

for _,row in df.iterrows():
    dlat = row["lat"] - home_lat
    dlon = row["lon"] - home_lon

    psy_lat.append(home_lat + row["scale"]*dlat)
    psy_lon.append(home_lon + row["scale"]*dlon)

df["psy_lat"]=psy_lat
df["psy_lon"]=psy_lon

col1,col2 = st.columns(2)

with col1:
    st.subheader("🌎 現実地図")

    real_map = folium.Map(
        location=[home_lat,home_lon],
        zoom_start=12
    )

    for _,row in df.iterrows():
        color = "red" if row["name"]==home else "blue"

        folium.Marker(
            [row["lat"],row["lon"]],
            popup=row["name"],
            tooltip=row["name"],
            icon=folium.Icon(color=color)
        ).add_to(real_map)

        if row["name"] != home:
            folium.PolyLine(
                [[home_lat,home_lon],[row["lat"],row["lon"]]],
                weight=3
            ).add_to(real_map)

    map_data = st_folium(real_map,width=700,height=500,key="real_map")

    if map_data and map_data.get("last_clicked"):
        st.session_state.clicked_lat = map_data["last_clicked"]["lat"]
        st.session_state.clicked_lon = map_data["last_clicked"]["lng"]

        st.success(
            f"選択座標: {st.session_state.clicked_lat:.6f}, "
            f"{st.session_state.clicked_lon:.6f}"
        )

with col2:
    st.subheader("🧠 心理地図")

    psy_map = folium.Map(
        location=[home_lat,home_lon],
        zoom_start=12
    )

    for _,row in df.iterrows():
        color = "red" if row["name"]==home else "green"

        folium.Marker(
            [row["psy_lat"],row["psy_lon"]],
            popup=f"{row['name']}<br>倍率:{row['scale']:.2f}",
            tooltip=row["name"],
            icon=folium.Icon(color=color)
        ).add_to(psy_map)

        if row["name"] != home:
            folium.PolyLine(
                [[home_lat,home_lon],[row["psy_lat"],row["psy_lon"]]],
                color="red",
                weight=3
            ).add_to(psy_map)

    st_folium(psy_map,width=700,height=500,key="psy_map")

st.subheader("心理倍率")
st.dataframe(
    df[["name","duty","crowd","fun","scale"]],
    use_container_width=True
)

distance_data=[]

for _,row in df.iterrows():
    if row["name"]==home:
        continue

    real_dist = distance_km(
        home_lat,home_lon,
        row["lat"],row["lon"]
    )

    psy_dist = distance_km(
        home_lat,home_lon,
        row["psy_lat"],row["psy_lon"]
    )

    distance_data.append([
        row["name"],
        round(real_dist,2),
        round(psy_dist,2)
    ])

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

if st.button("レビュー保存"):

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

st.dataframe(
    review_df,
    use_container_width=True
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

    walk_minutes = int(
        (
            route_distance / 4.8
        ) * 60
    )

    arrival_time = (
        datetime.now()
        + timedelta(
            minutes=walk_minutes
        )
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "距離(km)",
            f"{route_distance:.2f}"
        )

    with col2:

        st.metric(
            "徒歩時間",
            f"{walk_minutes}分"
        )

    with col3:

        st.metric(
            "到着予想",
            arrival_time.strftime(
                "%H:%M"
            )
        )

# ==================================
# CSV出力
# ==================================

st.divider()

st.header(
    "📥 データ出力"
)

with open(
    CSV_FILE,
    "rb"
) as f:

    st.download_button(
        label="locations.csv ダウンロード",
        data=f,
        file_name="locations.csv",
        mime="text/csv"
    )

with open(
    REVIEW_FILE,
    "rb"
) as f:

    st.download_button(
        label="reviews.csv ダウンロード",
        data=f,
        file_name="reviews.csv",
        mime="text/csv"
    )



st.subheader("地点削除")

delete_target = st.selectbox(
    "削除する地点",
    df["name"]
)

if st.button("削除"):
    df = df[df["name"] != delete_target]
    df.to_csv(CSV_FILE,index=False)
    st.rerun()
