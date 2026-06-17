"""
models/segmentation.py
KMeans customer segmentation + cluster interpretation.
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # non-interactive backend
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


# Base RFM features always used for clustering
BASE_FEATURES = ["recency", "frequency", "monetary"]
# Optional behavioral features used when available
EXTRA_FEATURES = ["avg_order_value", "unique_categories", "avg_days_between_orders"]


def run_kmeans(rfm: pd.DataFrame, n_clusters: int = 4, random_state: int = 42):
    """
    Train KMeans pada fitur RFM (+behavioral features jika tersedia).

    Returns:
        rfm      : DataFrame dengan kolom 'cluster' dan 'segment'
        kmeans   : fitted KMeans model
        scaler   : fitted StandardScaler
    """
    # Pilih fitur yang tersedia
    features = BASE_FEATURES + [f for f in EXTRA_FEATURES if f in rfm.columns]
    logger.info(f"[segmentation] Clustering features: {features}")

    scaler = StandardScaler()
    X = scaler.fit_transform(rfm[features].fillna(0))

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    rfm = rfm.copy()
    rfm["cluster"] = kmeans.fit_predict(X)

    score = silhouette_score(X, rfm["cluster"])
    logger.info(f"[segmentation] KMeans n_clusters={n_clusters} | Silhouette={score:.3f}")

    centroids = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=features
    )
    logger.info(f"[segmentation] Cluster centroids (RFM only):\n{centroids[BASE_FEATURES].round(2).to_string()}")

    rfm = _assign_labels(rfm, centroids)
    return rfm, kmeans, scaler


def _assign_labels(rfm: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    """Label cluster berdasarkan centroid recency & monetary."""
    c = centroids.copy()
    c["cluster_id"] = range(len(c))
    c["score"] = c["monetary"] - c["recency"] * 0.3 + c["frequency"] * 2
    ranks = c.sort_values("score", ascending=False)["cluster_id"].tolist()
    label_map = {
        ranks[0]: "🏆 Champions",
        ranks[1]: "💚 Loyal",
        ranks[2]: "🌱 Potential",
        ranks[3]: "⚠️ At Risk",
    }
    rfm = rfm.copy()
    rfm["segment"] = rfm["cluster"].map(label_map)
    logger.info(f"[segmentation] Segment distribution:\n{rfm['segment'].value_counts().to_string()}")
    return rfm


def find_optimal_k(rfm: pd.DataFrame, k_range=range(2, 9), output_dir="outputs"):
    """Elbow + Silhouette plot untuk memilih k optimal."""
    os.makedirs(output_dir, exist_ok=True)
    scaler = StandardScaler()
    X = scaler.fit_transform(rfm[BASE_FEATURES].fillna(0))

    inertias, silhouettes = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X, labels))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(list(k_range), inertias, "bo-")
    ax1.set_title("Elbow Method"); ax1.set_xlabel("k"); ax1.set_ylabel("Inertia")

    ax2.plot(list(k_range), silhouettes, "rs-")
    ax2.set_title("Silhouette Score"); ax2.set_xlabel("k"); ax2.set_ylabel("Score")

    plt.tight_layout()
    path = os.path.join(output_dir, "optimal_k.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"[segmentation] Optimal-k plot → {path}")
    return path


def plot_segments(rfm: pd.DataFrame, output_dir="outputs") -> str:
    """Scatter plot Frequency vs Monetary, warna per segment."""
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0D1117")
    palette = {
        "🏆 Champions": "#00B4D8",
        "💚 Loyal":     "#06D6A0",
        "🌱 Potential": "#F77F00",
        "⚠️ At Risk":  "#EF233C",
    }

    for ax in axes:
        ax.set_facecolor("#161B22")
        for spine in ax.spines.values():
            spine.set_color("#21262D")

    # Scatter: Frequency vs Monetary
    for seg, grp in rfm.groupby("segment"):
        axes[0].scatter(grp["frequency"], grp["monetary"],
                        label=seg, alpha=0.6, s=10, color=palette.get(seg, "#8B949E"))
    axes[0].set_xlabel("Frequency", color="#E6EDF3")
    axes[0].set_ylabel("Monetary ($)", color="#E6EDF3")
    axes[0].set_title("Frequency vs Monetary", color="#E6EDF3")
    axes[0].tick_params(colors="#8B949E")
    axes[0].legend(fontsize=8, facecolor="#21262D", labelcolor="#E6EDF3")

    # Bar: Customer count per segment
    counts = rfm["segment"].value_counts()
    bars = axes[1].barh(counts.index, counts.values,
                        color=[palette.get(s, "#8B949E") for s in counts.index])
    axes[1].set_xlabel("Customers", color="#E6EDF3")
    axes[1].set_title("Customers per Segment", color="#E6EDF3")
    axes[1].tick_params(colors="#E6EDF3")
    for bar, val in zip(bars, counts.values):
        axes[1].text(val + 100, bar.get_y() + bar.get_height()/2,
                     f"{val:,}", va="center", color="#E6EDF3", fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, "segmentation.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    print(f"[segmentation] Plot → {path}")
    return path


if __name__ == "__main__":
    from src.back_end.ml.data_loader import get_engine, load_orders
    from src.back_end.ml.features import create_rfm
    eng = get_engine()
    df  = load_orders(eng)
    rfm = create_rfm(df)
    rfm, km, scaler = run_kmeans(rfm)
    find_optimal_k(rfm)
    plot_segments(rfm)
