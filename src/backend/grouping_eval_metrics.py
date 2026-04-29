from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd


EVAL_CSV_PATH = Path("datasets/grouping_eval/grouping_eval_subset.csv")
IMAGE_CACHE_DIR = Path(".cache/grouping_eval_images")
EMBEDDING_CACHE_PATH = Path(".cache/grouping_eval_embeddings.jsonl")
PREDICTIONS_OUT = Path("datasets/grouping_eval/grouping_eval_predictions.csv")
METRICS_OUT = Path("datasets/grouping_eval/grouping_eval_metrics.csv")


def auto_set_google_credentials() -> None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    credentials_path = Path("credentials.json")
    if credentials_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path.resolve())


def load_eval_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"line_number", "image_uri", "final_discipline", "true_group_id"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["line_number"] = pd.to_numeric(df["line_number"], errors="raise").astype(int)
    df["final_discipline"] = df["final_discipline"].astype(str).str.strip()
    df["true_group_id"] = df["true_group_id"].astype(str).str.strip()

    return df.sort_values("line_number").reset_index(drop=True)


def summarize_ground_truth(df: pd.DataFrame) -> None:
    group_sizes = df["true_group_id"].value_counts()
    multi_groups = group_sizes[group_sizes >= 2]

    print("\n=== Ground Truth Summary ===")
    print(f"Rows: {len(df)}")
    print(f"Unique true groups: {df['true_group_id'].nunique()}")
    print(f"Groups with 2+ images: {len(multi_groups)}")
    print(f"Duplicate line_numbers: {df['line_number'].duplicated().sum()}")
    print(f"Missing true_group_id: {df['true_group_id'].isna().sum()}")

    print("\n=== Multi-image True Groups ===")
    print(multi_groups.to_string())


def load_embedding_cache(path: Path) -> dict[int, list[float]]:
    if not path.exists():
        return {}

    cache = {}

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                cache[int(record["line_number"])] = record["embedding"]

    return cache


def save_embedding_to_cache(path: Path, line_number: int, embedding: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "line_number": int(line_number),
                    "embedding": [float(x) for x in embedding],
                }
            )
            + "\n"
        )


def image_extension_from_uri(uri: str) -> str:
    suffix = Path(uri.split("?")[0]).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return ".jpg"


def download_gcs_image(gs_uri: str, line_number: int) -> Path:
    if not isinstance(gs_uri, str) or not gs_uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// image_uri for line {line_number}, got: {gs_uri}")

    auto_set_google_credentials()

    from google.cloud import storage

    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    local_path = IMAGE_CACHE_DIR / f"{line_number}{image_extension_from_uri(gs_uri)}"

    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    no_prefix = gs_uri.replace("gs://", "", 1)
    bucket_name, blob_name = no_prefix.split("/", 1)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)

    return local_path


def text_for_embedding(row: pd.Series) -> str:
    for col in ["final_description_optional", "DESCRIPTION", "auto_description"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()

    return ""


def generate_embeddings(df: pd.DataFrame) -> dict[int, list[float]]:
    from src.backend.inference import generate_embedding

    cache = load_embedding_cache(EMBEDDING_CACHE_PATH)

    missing = [
        row for _, row in df.iterrows()
        if int(row["line_number"]) not in cache
    ]

    print("\n=== Embedding Setup ===")
    print(f"Cached embeddings: {len(cache)}")
    print(f"Missing embeddings: {len(missing)}")

    for idx, row in enumerate(missing, start=1):
        line_number = int(row["line_number"])
        image_path = download_gcs_image(str(row["image_uri"]), line_number)
        text = text_for_embedding(row)

        try:
            embedding = generate_embedding(text=text, image_paths=[str(image_path)])
        except TypeError:
            embedding = generate_embedding(text, [str(image_path)])

        if embedding is None:
            raise RuntimeError(f"Embedding failed for line {line_number}")

        embedding = [float(x) for x in embedding]
        cache[line_number] = embedding
        save_embedding_to_cache(EMBEDDING_CACHE_PATH, line_number, embedding)

        print(f"[{idx}/{len(missing)}] Embedded line {line_number}")

    return cache


def cosine_similarity(vec_a, vec_b) -> float:
    from src.backend.grouping import _cosine_similarity_fallback

    return float(_cosine_similarity_fallback(vec_a, vec_b))


def predict_groups(df: pd.DataFrame, embeddings: dict[int, list[float]], threshold: float) -> pd.DataFrame:
    """
    Offline version of the MVP grouping rule.

    It processes reports in order and compares each new report against previous
    reports in the same discipline bucket. If the best score passes the threshold,
    it reuses that predicted group. Otherwise, it creates a new predicted group.
    """

    output = df.copy()

    previous_reports = []
    pred_group_ids = []
    best_scores = []
    best_match_lines = []

    next_group_num = 1

    for _, row in output.iterrows():
        line_number = int(row["line_number"])
        discipline = str(row["final_discipline"]).strip()
        embedding = embeddings.get(line_number)

        best_score = -1.0
        best_pred_group = None
        best_match_line = None

        for candidate in previous_reports:
            if candidate["discipline"] != discipline:
                continue

            score = cosine_similarity(embedding, candidate["embedding"])

            if score > best_score:
                best_score = score
                best_pred_group = candidate["pred_group_id"]
                best_match_line = candidate["line_number"]

        if best_pred_group is not None and best_score >= threshold:
            pred_group_id = best_pred_group
        else:
            pred_group_id = f"pred_{next_group_num:04d}"
            next_group_num += 1

        pred_group_ids.append(pred_group_id)
        best_scores.append(best_score)
        best_match_lines.append(best_match_line)

        previous_reports.append(
            {
                "line_number": line_number,
                "discipline": discipline,
                "embedding": embedding,
                "pred_group_id": pred_group_id,
            }
        )

    output["pred_group_id"] = pred_group_ids
    output["best_similarity_score"] = best_scores
    output["best_match_line_number"] = best_match_lines

    return output


def pairwise_metrics(df: pd.DataFrame) -> dict:
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    for i, j in combinations(df.index, 2):
        same_true = df.loc[i, "true_group_id"] == df.loc[j, "true_group_id"]
        same_pred = df.loc[i, "pred_group_id"] == df.loc[j, "pred_group_id"]

        if same_true and same_pred:
            tp += 1
        elif not same_true and same_pred:
            fp += 1
        elif same_true and not same_pred:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "pairwise_precision": precision,
        "pairwise_recall": recall,
        "pairwise_f1": f1,
        "true_positive_pairs": tp,
        "false_positive_pairs": fp,
        "false_negative_pairs": fn,
        "true_negative_pairs": tn,
    }


def cluster_purity(df: pd.DataFrame) -> float:
    correct = 0

    for _, group in df.groupby("pred_group_id"):
        correct += Counter(group["true_group_id"]).most_common(1)[0][1]

    return correct / len(df) if len(df) else 0.0


def optional_sklearn_metrics(df: pd.DataFrame) -> dict:
    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    except ImportError:
        return {}

    return {
        "normalized_mutual_info": normalized_mutual_info_score(
            df["true_group_id"], df["pred_group_id"]
        ),
        "adjusted_rand_index": adjusted_rand_score(
            df["true_group_id"], df["pred_group_id"]
        ),
    }


def evaluate(df: pd.DataFrame, threshold: float) -> dict:
    true_sizes = df["true_group_id"].value_counts()
    pred_sizes = df["pred_group_id"].value_counts()

    metrics = {
        "threshold": threshold,
        "rows": len(df),
        "true_groups": df["true_group_id"].nunique(),
        "predicted_groups": df["pred_group_id"].nunique(),
        "true_groups_with_2_plus_images": int((true_sizes >= 2).sum()),
        "predicted_groups_with_2_plus_images": int((pred_sizes >= 2).sum()),
        "cluster_purity": cluster_purity(df),
    }

    metrics.update(pairwise_metrics(df))
    metrics.update(optional_sklearn_metrics(df))

    return metrics


def print_metrics(metrics: dict) -> None:
    print("\n=== Grouping Metrics ===")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")


def show_error_examples(df: pd.DataFrame, limit: int = 10) -> None:
    false_merges = []
    false_splits = []

    for i, j in combinations(df.index, 2):
        same_true = df.loc[i, "true_group_id"] == df.loc[j, "true_group_id"]
        same_pred = df.loc[i, "pred_group_id"] == df.loc[j, "pred_group_id"]

        if same_pred and not same_true:
            false_merges.append(
                (
                    int(df.loc[i, "line_number"]),
                    int(df.loc[j, "line_number"]),
                    df.loc[i, "true_group_id"],
                    df.loc[j, "true_group_id"],
                    df.loc[i, "pred_group_id"],
                )
            )

        if same_true and not same_pred:
            false_splits.append(
                (
                    int(df.loc[i, "line_number"]),
                    int(df.loc[j, "line_number"]),
                    df.loc[i, "true_group_id"],
                    df.loc[i, "pred_group_id"],
                    df.loc[j, "pred_group_id"],
                )
            )

    print("\n=== Example False Merges ===")
    if false_merges:
        for row in false_merges[:limit]:
            print(row)
    else:
        print("None")

    print("\n=== Example False Splits ===")
    if false_splits:
        for row in false_splits[:limit]:
            print(row)
    else:
        print("None")


def parse_thresholds(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.94)
    parser.add_argument("--thresholds", default="0.70,0.75,0.80,0.85,0.90,0.94,0.95,0.97")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()

    df = load_eval_csv(EVAL_CSV_PATH)

    if args.max_rows:
        df = df.head(args.max_rows).copy()

    summarize_ground_truth(df)

    if args.check_only:
        print("\nCheck-only complete.")
        return

    embeddings = generate_embeddings(df)

    if args.sweep:
        rows = []

        for threshold in parse_thresholds(args.thresholds):
            predicted = predict_groups(df, embeddings, threshold)
            metrics = evaluate(predicted, threshold)
            rows.append(metrics)

        sweep_df = pd.DataFrame(rows)
        METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
        sweep_df.to_csv(METRICS_OUT, index=False)

        print("\n=== Threshold Sweep ===")
        print(sweep_df.to_string(index=False))
        print(f"\nSaved metrics to: {METRICS_OUT}")

        best = sweep_df.sort_values("pairwise_f1", ascending=False).iloc[0]
        print("\n=== Best Threshold by Pairwise F1 ===")
        print(best.to_string())

    predicted = predict_groups(df, embeddings, args.threshold)
    metrics = evaluate(predicted, args.threshold)

    print_metrics(metrics)
    show_error_examples(predicted)

    PREDICTIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
    predicted.to_csv(PREDICTIONS_OUT, index=False)

    print(f"\nSaved predictions to: {PREDICTIONS_OUT}")


if __name__ == "__main__":
    main()