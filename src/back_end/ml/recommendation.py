"""
src/back_end/ml/recommendation.py
=================================
Model Recommendation System menggunakan Matrix Factorization (ALS)
dari library `implicit`. Memberikan rekomendasi produk yang relevan.
"""

import os
import logging
import joblib
import pandas as pd
import numpy as np

try:
    import scipy.sparse as sparse
    from implicit.als import AlternatingLeastSquares
    _IMPLICIT_AVAILABLE = True
except ImportError:
    _IMPLICIT_AVAILABLE = False

logger = logging.getLogger(__name__)


def prepare_item_user_matrix(orders: pd.DataFrame):
    """
    Buat implicit feedback matrix dari history order.
    Returns:
        sparse_item_user, sparse_user_item, user_mapping, item_mapping
    """
    if not _IMPLICIT_AVAILABLE:
        raise ImportError("pip install implicit>=0.7.2 scipy required for ALS Recommender.")

    df = orders.dropna(subset=["customer_id", "product_id"]).copy()
    df["customer_id"] = df["customer_id"].astype(int)
    df["product_id"]  = df["product_id"].astype(int)

    # Hitung frekuensi interaksi
    interaction = df.groupby(["customer_id", "product_id"]).size().reset_index(name="purchases")

    # Buat categorical codes
    interaction["user_cat"] = interaction["customer_id"].astype("category")
    interaction["item_cat"] = interaction["product_id"].astype("category")

    # Mapping: internal_index -> real_id
    user_mapping = dict(enumerate(interaction["user_cat"].cat.categories))
    item_mapping = dict(enumerate(interaction["item_cat"].cat.categories))

    user_indices = interaction["user_cat"].cat.codes.values
    item_indices = interaction["item_cat"].cat.codes.values
    purchases    = interaction["purchases"].values.astype(float)

    sparse_item_user = sparse.csr_matrix((purchases, (item_indices, user_indices)))
    sparse_user_item = sparse.csr_matrix((purchases, (user_indices, item_indices)))

    return sparse_item_user, sparse_user_item, user_mapping, item_mapping


def train_recommender(orders: pd.DataFrame, output_dir: str = "models", factors: int = 20, iterations: int = 15):
    """Train ALS Model dan save ke disk."""
    os.makedirs(output_dir, exist_ok=True)

    item_user, user_item, user_mapping, item_mapping = prepare_item_user_matrix(orders)

    model = AlternatingLeastSquares(
        factors=factors,
        regularization=0.1,
        iterations=iterations,
        random_state=42,
        calculate_training_loss=True
    )

    logger.info(f"[recsys] Training ALS: {item_user.shape[1]} users, {item_user.shape[0]} items...")
    alpha_val  = 40
    data_conf  = (user_item * alpha_val).astype("double")
    model.fit(data_conf)
    logger.info("[recsys] ALS Model trained.")

    # Simpan semua artifacts
    joblib.dump(model,           os.path.join(output_dir, "als_model.pkl"))
    joblib.dump(user_item,       os.path.join(output_dir, "als_user_item_matrix.pkl"))
    joblib.dump(user_mapping,    os.path.join(output_dir, "als_user_map.pkl"))
    joblib.dump(item_mapping,    os.path.join(output_dir, "als_item_map.pkl"))

    # Simpan juga reverse item map (internal_id→real_product_id) & reverse user map
    rev_item_map = {int(v): k for k, v in item_mapping.items()}
    rev_user_map = {int(v): k for k, v in user_mapping.items()}
    joblib.dump(rev_item_map, os.path.join(output_dir, "als_rev_item_map.pkl"))
    joblib.dump(rev_user_map, os.path.join(output_dir, "als_rev_user_map.pkl"))

    logger.info(f"[recsys] Artifacts saved -> {output_dir}")
    return model, user_item, user_mapping, item_mapping


# Global cache for ALS models to prevent loading from disk on every request
_als_cache = {
    "model": None,
    "user_item": None,
    "user_map": None,
    "item_map": None
}

def get_recommendations(customer_id: int, N: int = 5, model_dir: str = "models") -> list:
    """
    Dapatkan N produk rekomendasi untuk customer.
    Robust terhadap perbedaan versi implicit (internal index vs real product_id).
    """
    global _als_cache
    
    if _als_cache["model"] is None:
        paths = {
            "model":    os.path.join(model_dir, "als_model.pkl"),
            "ui":       os.path.join(model_dir, "als_user_item_matrix.pkl"),
            "umap":     os.path.join(model_dir, "als_user_map.pkl"),
            "imap":     os.path.join(model_dir, "als_item_map.pkl"),
        }

        missing = [k for k, p in paths.items() if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(
                f"Model files tidak lengkap: {missing}. Jalankan train_recommender() dulu."
            )

        _als_cache["model"]     = joblib.load(paths["model"])
        _als_cache["user_item"] = joblib.load(paths["ui"])
        _als_cache["user_map"]  = joblib.load(paths["umap"])   # {internal_idx: real_customer_id}
        _als_cache["item_map"]  = joblib.load(paths["imap"])   # {internal_idx: real_product_id}

    model     = _als_cache["model"]
    user_item = _als_cache["user_item"]
    user_map  = _als_cache["user_map"]
    item_map  = _als_cache["item_map"]

    # Bangun reverse user map: real_customer_id -> internal_idx
    rev_user_map = {int(v): k for k, v in user_map.items()}

    customer_id = int(customer_id)
    if customer_id not in rev_user_map:
        logger.info(f"[recsys] Customer {customer_id} tidak ada dalam training data (cold start).")
        return []

    internal_user_id = rev_user_map[customer_id]

    # Jalankan rekomendasi
    ids, scores = model.recommend(
        userid=internal_user_id,
        user_items=user_item[internal_user_id],
        N=N,
        filter_already_liked_items=True,
    )

    # ── Robust lookup: dukung dua format output implicit ───────────────────────
    # Beberapa versi implicit mengembalikan internal index, versi lain real id.
    # Bangun juga "inverted item_map": real_product_id -> internal_idx
    inv_item_map = {int(v): k for k, v in item_map.items()}

    product_ids = []
    for raw_id in ids:
        raw_id = int(raw_id)
        if raw_id in item_map:
            # internal index -> real product_id
            product_ids.append(int(item_map[raw_id]))
        elif raw_id in inv_item_map:
            # already a real product_id
            product_ids.append(raw_id)
        else:
            logger.warning(f"[recsys] id={raw_id} tidak ditemukan di item_map, dilewati.")

    return product_ids


if __name__ == "__main__":
    from src.back_end.ml.data_loader import get_engine, load_full
    logging.basicConfig(level=logging.INFO)
    eng = get_engine()
    df  = load_full(eng)
    model, ui, umap, imap = train_recommender(df)
    if umap:
        test_user = int(list(umap.values())[0])
        recs = get_recommendations(test_user, N=5)
        print(f"Rekomendasi untuk User {test_user}: {recs}")
