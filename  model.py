"""
model.py - 体感地図プロジェクト 数理モデル
==========================================
担当: 数理実装担当 B
内容: 心理倍率計算・座標変換・距離計算・LASSO予測
"""

import math
import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score


# =============================================
# 1. 心理倍率（scale）計算
# =============================================

def calc_scale(duty: float, crowd: float, fun: float) -> float:
    """
    心理倍率を計算する。

    モデル式:
        scale = 1 + 0.15 * duty + 0.10 * crowd - 0.10 * fun

    Parameters
    ----------
    duty  : 義務感 (1〜5)
    crowd : 混雑度 (1〜5)
    fun   : 楽しさ (1〜5)

    Returns
    -------
    scale : 心理倍率（1.0付近〜最大1.5程度）

    Examples
    --------
    >>> calc_scale(3, 3, 3)   # 中立 → 1.45
    1.45
    >>> calc_scale(5, 5, 1)   # 最もストレス高 → 1.9
    1.9
    >>> calc_scale(1, 1, 5)   # 最も楽しい → 1.2
    1.2
    """
    return 1 + 0.15 * duty + 0.10 * crowd - 0.10 * fun


def calc_scale_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameに対して心理倍率列を追加して返す。

    Parameters
    ----------
    df : columns に duty, crowd, fun を含む DataFrame

    Returns
    -------
    df : scale 列を追加した DataFrame
    """
    df = df.copy()
    df["scale"] = df.apply(
        lambda row: calc_scale(row["duty"], row["crowd"], row["fun"]),
        axis=1
    )
    return df


# =============================================
# 2. 心理座標変換
# =============================================

def calc_psy_coords(
    home_lat: float,
    home_lon: float,
    lat: float,
    lon: float,
    scale: float
) -> tuple[float, float]:
    """
    ホーム地点を基準に、心理倍率で座標を変換する。

    変換式:
        psy_lat = home_lat + scale * (lat - home_lat)
        psy_lon = home_lon + scale * (lon - home_lon)

    Parameters
    ----------
    home_lat, home_lon : ホーム地点の緯度・経度
    lat, lon           : 対象地点の緯度・経度
    scale              : 心理倍率

    Returns
    -------
    (psy_lat, psy_lon) : 心理座標
    """
    dlat = lat - home_lat
    dlon = lon - home_lon
    psy_lat = home_lat + scale * dlat
    psy_lon = home_lon + scale * dlon
    return psy_lat, psy_lon


def calc_psy_coords_df(
    df: pd.DataFrame,
    home_lat: float,
    home_lon: float
) -> pd.DataFrame:
    """
    DataFrame全体に心理座標変換を適用する。

    Parameters
    ----------
    df               : scale 列を含む DataFrame
    home_lat/home_lon: ホーム地点の緯度・経度

    Returns
    -------
    df : psy_lat, psy_lon 列を追加した DataFrame
    """
    df = df.copy()
    coords = df.apply(
        lambda row: calc_psy_coords(
            home_lat, home_lon,
            row["lat"], row["lon"],
            row["scale"]
        ),
        axis=1,
        result_type="expand"
    )
    df["psy_lat"] = coords[0]
    df["psy_lon"] = coords[1]
    return df


# =============================================
# 3. ハーバーサイン距離計算
# =============================================

def distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    ハーバーサイン公式による2点間の距離（km）を返す。

    公式:
        a = sin²(Δlat/2) + cos(lat1)・cos(lat2)・sin²(Δlon/2)
        c = 2 * atan2(√a, √(1-a))
        d = R * c  (R = 6371 km)

    Parameters
    ----------
    lat1, lon1 : 地点1の緯度・経度（度数法）
    lat2, lon2 : 地点2の緯度・経度（度数法）

    Returns
    -------
    distance : 距離（km）
    """
    R = 6371  # 地球の平均半径（km）

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


def calc_distances_df(
    df: pd.DataFrame,
    home_lat: float,
    home_lon: float
) -> pd.DataFrame:
    """
    ホームからの現実距離・体感距離を計算してDataFrameで返す。

    Parameters
    ----------
    df               : psy_lat, psy_lon 列を含む DataFrame
    home_lat/home_lon: ホーム地点の緯度・経度

    Returns
    -------
    distance_df : 場所・現実距離(km)・体感距離(km) の DataFrame
    """
    rows = []
    for _, row in df.iterrows():
        real_dist = distance_km(
            home_lat, home_lon,
            row["lat"], row["lon"]
        )
        psy_dist = distance_km(
            home_lat, home_lon,
            row["psy_lat"], row["psy_lon"]
        )
        rows.append({
            "場所": row["name"],
            "現実距離(km)": round(real_dist, 3),
            "体感距離(km)": round(psy_dist, 3),
            "倍率": round(row["scale"], 3)
        })
    return pd.DataFrame(rows)


# =============================================
# 4. LASSO回帰モデル
# =============================================

def fit_lasso(
    df: pd.DataFrame,
    alpha: float = 0.01,
    target: str = "scale"
) -> dict:
    """
    duty・crowd・fun を特徴量として LASSO 回帰を学習する。

    LASSO の目的関数:
        min { (1/2n)||y - Xw||² + α||w||₁ }

    L1正則化項 α||w||₁ により、不要な特徴量の係数をゼロにする
    （スパース推定）。

    Parameters
    ----------
    df     : duty, crowd, fun, (target) 列を含む DataFrame
    alpha  : 正則化強度（大きいほどスパース）
    target : 目的変数列名（デフォルト: "scale"）

    Returns
    -------
    result : {
        "model"       : 学習済みLassoオブジェクト,
        "scaler"      : StandardScalerオブジェクト,
        "coef"        : 係数 dict,
        "intercept"   : 切片,
        "r2_train"    : 訓練R²,
        "r2_test"     : テストR²,
        "rmse_test"   : テストRMSE,
        "X_cols"      : 特徴量列名リスト
    }
    """
    feature_cols = ["duty", "crowd", "fun"]
    X = df[feature_cols].values
    y = df[target].values

    # 標準化（平均0・分散1）
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 訓練・テスト分割（データ少ない場合は全量使用）
    if len(df) >= 4:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.25, random_state=42
        )
    else:
        X_train, X_test = X_scaled, X_scaled
        y_train, y_test = y, y

    # LASSO学習
    model = Lasso(alpha=alpha, max_iter=10000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    return {
        "model": model,
        "scaler": scaler,
        "coef": dict(zip(feature_cols, model.coef_)),
        "intercept": model.intercept_,
        "r2_train": r2_score(y_train, model.predict(X_train)),
        "r2_test": r2_score(y_test, y_pred),
        "rmse_test": math.sqrt(mean_squared_error(y_test, y_pred)),
        "X_cols": feature_cols
    }


def fit_lasso_cv(
    df: pd.DataFrame,
    target: str = "scale"
) -> dict:
    """
    クロスバリデーションで最適な alpha を自動選択する LASSO。

    Parameters
    ----------
    df     : duty, crowd, fun, (target) 列を含む DataFrame
    target : 目的変数列名

    Returns
    -------
    result : fit_lasso と同形式の dict に "best_alpha" を追加
    """
    feature_cols = ["duty", "crowd", "fun"]
    X = df[feature_cols].values
    y = df[target].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # CVで最適alpha探索
    lasso_cv = LassoCV(
        alphas=np.logspace(-4, 1, 100),
        cv=min(5, len(df)),
        max_iter=10000
    )
    lasso_cv.fit(X_scaled, y)

    best_alpha = lasso_cv.alpha_
    result = fit_lasso(df, alpha=best_alpha, target=target)
    result["best_alpha"] = best_alpha
    return result


def predict_scale(
    model,
    scaler,
    duty: float,
    crowd: float,
    fun: float
) -> float:
    """
    学習済みモデルで新しい地点の scale を予測する。

    Parameters
    ----------
    model, scaler : fit_lasso の返り値から取得
    duty, crowd, fun : 新地点のパラメータ

    Returns
    -------
    predicted_scale : float
    """
    X_new = np.array([[duty, crowd, fun]])
    X_scaled = scaler.transform(X_new)
    return float(model.predict(X_scaled)[0])


# =============================================
# 動作確認（直接実行時）
# =============================================

if __name__ == "__main__":
    print("=== scale計算テスト ===")
    print(f"中立(3,3,3)     : {calc_scale(3,3,3):.2f}")
    print(f"高ストレス(5,5,1): {calc_scale(5,5,1):.2f}")
    print(f"楽しい(1,1,5)   : {calc_scale(1,1,5):.2f}")

    print("\n=== ダミーデータでLASSOテスト ===")
    np.random.seed(0)
    dummy = pd.DataFrame({
        "duty":  np.random.randint(1, 6, 30),
        "crowd": np.random.randint(1, 6, 30),
        "fun":   np.random.randint(1, 6, 30),
    })
    dummy["scale"] = dummy.apply(
        lambda r: calc_scale(r["duty"], r["crowd"], r["fun"]) + np.random.normal(0, 0.05),
        axis=1
    )

    result = fit_lasso(dummy, alpha=0.01)
    print(f"係数   : {result['coef']}")
    print(f"切片   : {result['intercept']:.4f}")
    print(f"R²(test): {result['r2_test']:.4f}")
    print(f"RMSE   : {result['rmse_test']:.4f}")