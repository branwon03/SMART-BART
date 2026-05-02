"""
Offline grouping evaluation script for the BART incident grouping.

This script does not change production grouping behavior. Instead, it uses a
hand-labeled CSV with true_group_id labels to simulate how the grouping pipeline
would assign incident groups at different cosine similarity thresholds.

High-level flow:
1. Load the labeled grouping evaluation CSV.
2. Download/cache images from GCS if needed.
3. Generate/cache real Gemini embeddings.
4. Simulate grouping in report order using the MVP rule:
   - only compare reports within the same discipline
   - reuse the best matching group if similarity >= threshold
   - otherwise create a new predicted group
5. Evaluate predicted groups against true_group_id labels using pairwise metrics,
   cluster purity, and optional sklearn metrics.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd


# Input dataset and local cache/output paths
# The .cache files should stay local because they can contain downloaded images
# and generated embeddings that are expensive/noisy to recreate and test with.
# The output CSVs are useful artifacts to keep for comparing different runs and thresholds.
EVAL_CSV_PATH = Path("datasets/grouping_eval/grouping_eval_subset.csv")
IMAGE_CACHE_DIR = Path(".cache/grouping_eval_images")
EMBEDDING_CACHE_PATH = Path(".cache/grouping_eval_embeddings.jsonl")

# Separate cache for production-style embedding text.
# This prevents overwriting the original description-based eval embeddings.
PRODUCTION_EMBEDDING_CACHE_PATH = Path(
    ".cache/grouping_eval_embeddings_production_style.jsonl"
)

# Output files from the baseline evaluation run.
# These are useful artifacts for comparing threshold behavior.
PREDICTIONS_OUT = Path("datasets/grouping_eval/grouping_eval_predictions.csv")
METRICS_OUT = Path("datasets/grouping_eval/grouping_eval_metrics.csv")

# Added location output paths.
PREDICTIONS_LOCATION_OUT = Path(
    "datasets/grouping_eval/grouping_eval_predictions_location_filtered.csv"
)
METRICS_LOCATION_OUT = Path(
    "datasets/grouping_eval/grouping_eval_metrics_location_filtered.csv"
)

# Added production-style embedding output paths.
PREDICTIONS_PROD_EMBEDDINGS_OUT = Path(
    "datasets/grouping_eval/grouping_eval_predictions_production_embeddings.csv"
)
METRICS_PROD_EMBEDDINGS_OUT = Path(
    "datasets/grouping_eval/grouping_eval_metrics_production_embeddings.csv"
)

# Added production-style embedding + location-filtered output paths.
PREDICTIONS_PROD_EMBEDDINGS_LOCATION_OUT = Path(
    "datasets/grouping_eval/grouping_eval_predictions_production_embeddings_location_filtered.csv"
)
METRICS_PROD_EMBEDDINGS_LOCATION_OUT = Path(
    "datasets/grouping_eval/grouping_eval_metrics_production_embeddings_location_filtered.csv"
)


def auto_set_google_credentials() -> None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    credentials_path = Path("credentials.json")
    if credentials_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path.resolve())


def load_eval_csv(path: Path) -> pd.DataFrame:
    """
    Load and validate the hand-labeled grouping evaluation dataset.

    The important ground-truth column is true_group_id:
    - rows with the same true_group_id should be grouped together
    - rows with different true_group_id values should stay separate
    """

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"line_number", "image_uri", "final_discipline", "true_group_id"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["line_number"] = pd.to_numeric(df["line_number"], errors="raise").astype(int)
    df["final_discipline"] = df["final_discipline"].astype(str).str.strip()
    df["true_group_id"] = df["true_group_id"].astype(str).str.strip()

    # Clean photo_location_id when loading CSV.
    # Missing location is represented as an empty string so the eval can mirror
    # the production fallback: location filters only apply when location exists.
    if "photo_location_id" in df.columns:
        df["photo_location_id"] = (
            df["photo_location_id"].fillna("").astype(str).str.strip()
        )

    return df.sort_values("line_number").reset_index(drop=True)


def summarize_ground_truth(df: pd.DataFrame) -> None:
    """
    Print a quick summary of the labeled dataset before running evaluation.

    This helps us confirm that the dataset has enough multi-image groups to make
    grouping recall meaningful.
    """

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
    """
    Load previously generated embeddings from a local JSONL cache.

    This prevents rerunning Gemini embeddings every time we sweep thresholds.
    """

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
    """
    Append one generated embedding to the local cache.

    The line_number is used as the stable key back to the eval CSV row.
    """

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
    """
    Download one eval image from GCS into the local cache if needed.

    The eval CSV stores image_uri as gs:// paths, while the embedding function
    expects a local image path.
    """

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
    """
    Choose the best available text description to include with the image embedding.

    Preference order:
    1. final_description_optional: our corrected/manual description if available
    2. DESCRIPTION: legacy/original description column if present
    3. auto_description: model-generated description
    """

    for col in ["final_description_optional", "DESCRIPTION", "auto_description"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()

    return ""


def production_style_text_for_embedding(row: pd.Series) -> str:
    """
    Build embedding text that mirrors the production processor's grouping prompt.

    Production uses parsed vlm_summary + discipline to make the embedding focus on
    the physical asset, surrounding scene, and object geometry. In the eval set,
    we use the best audited description available as the asset/scene text.
    """

    physical_asset = text_for_embedding(row) or "unknown maintenance issue"
    discipline = str(row.get("final_discipline", "")).strip() or "unknown"

    return (
        f"Task: Grouping maintenance photos from different angles. "
        f"Physical Asset: {physical_asset}. "
        f"Location Context: {discipline} area. "
        f"Instruction: Identify the specific physical asset and scene. "
        f"Focus on spatial surroundings and object geometry. "
        f"Ignore lighting, blur, or camera quality."
    )


def generate_embeddings(
    df: pd.DataFrame,
    production_style: bool = False,
) -> dict[int, list[float]]:
    """
    Generate or load embeddings for every row in the eval dataset.

    This intentionally calls the same backend embedding helper used by the project
    so the offline evaluation is closer to the real grouping pipeline.

    When production_style=True, this uses a separate cache and a grouping-specific
    embedding prompt that more closely mirrors processor.py.
    """

    from src.backend.inference import generate_embedding

    cache_path = (
        PRODUCTION_EMBEDDING_CACHE_PATH
        if production_style
        else EMBEDDING_CACHE_PATH
    )

    cache = load_embedding_cache(cache_path)

    missing = [
        row for _, row in df.iterrows()
        if int(row["line_number"]) not in cache
    ]

    print("\n=== Embedding Setup ===")
    print(f"Embedding mode: {'production_style' if production_style else 'description_baseline'}")
    print(f"Embedding cache: {cache_path}")
    print(f"Cached embeddings: {len(cache)}")
    print(f"Missing embeddings: {len(missing)}")

    for idx, row in enumerate(missing, start=1):
        line_number = int(row["line_number"])
        image_path = download_gcs_image(str(row["image_uri"]), line_number)

        text = (
            production_style_text_for_embedding(row)
            if production_style
            else text_for_embedding(row)
        )

        try:
            embedding = generate_embedding(text=text, image_paths=[str(image_path)])
        except TypeError:
            embedding = generate_embedding(text, [str(image_path)])

        if embedding is None:
            raise RuntimeError(f"Embedding failed for line {line_number}")

        embedding = [float(x) for x in embedding]
        cache[line_number] = embedding
        save_embedding_to_cache(cache_path, line_number, embedding)

        print(f"[{idx}/{len(missing)}] Embedded line {line_number}")

    return cache


def cosine_similarity(vec_a, vec_b) -> float:
    """
    Use the backend grouping cosine similarity helper.

    This keeps the eval script aligned with production grouping behavior instead
    of duplicating similarity logic here.
    """

    from src.backend.grouping import _cosine_similarity_fallback

    return float(_cosine_similarity_fallback(vec_a, vec_b))


def predict_groups(
    df: pd.DataFrame,
    embeddings: dict[int, list[float]],
    threshold: float,
    location_filter: bool = False,
) -> pd.DataFrame:
    """
    Offline version of the MVP grouping rule, means we are testing the grouping algorithm
    on a saved labeled dataset instead of through the live frontend/backend.

    It processes reports in order and compares each new report against previous
    reports in the same discipline bucket. If the best score passes the threshold,
    it reuses that predicted group. Otherwise, it creates a new predicted group.
    """

    output = df.copy()

    # Store reports that have already been processed so each new row is compared
    # only against earlier reports, similar to how a live processor sees incidents over time.
    # This also simulates the grouping rule where we only compare against previous reports, not future ones.
    previous_reports = []
    pred_group_ids = []
    best_scores = []
    best_match_lines = []

    next_group_num = 1

    for _, row in output.iterrows():
        line_number = int(row["line_number"])
        discipline = str(row["final_discipline"]).strip()
        location_id = str(row.get("photo_location_id", "")).strip()
        embedding = embeddings.get(line_number)

        best_score = -1.0
        best_pred_group = None
        best_match_line = None

        # Grouping rule: only compare reports within the same discipline.
        # This avoids obvious false merges across unrelated maintenance teams.
        for candidate in previous_reports:
            if candidate["discipline"] != discipline:
                continue

            # Production-like location rule:
            # if location metadata exists, require the same location.
            # if the new row has no location, fall back to discipline-only comparison.
            if location_filter and location_id and candidate.get("location_id") != location_id:
                continue

            score = cosine_similarity(embedding, candidate["embedding"])

            if score > best_score:
                best_score = score
                best_pred_group = candidate["pred_group_id"]
                best_match_line = candidate["line_number"]

        # If the best candidate passes the threshold, reuse its predicted group.
        # Otherwise, this report starts a new predicted incident group.
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
                "location_id": location_id,
                "embedding": embedding,
                "pred_group_id": pred_group_id,
            }
        )

    output["pred_group_id"] = pred_group_ids
    output["best_similarity_score"] = best_scores
    output["best_match_line_number"] = best_match_lines

    return output


def pairwise_metrics(df: pd.DataFrame) -> dict:
    """
    Evaluate grouping as pair decisions.

    For every pair of reports:
    - true positive: same true group and same predicted group
    - false positive: different true groups but same predicted group
    - false negative: same true group but different predicted groups
    - true negative: different true groups and different predicted groups

    This is useful because grouping errors are really pair-level merge/split errors.
    """

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
    """
    Measure how clean the predicted groups are.

    For each predicted group, count the most common true_group_id inside it.
    High purity means predicted groups usually avoid mixing unrelated issues.
    """

    correct = 0

    for _, group in df.groupby("pred_group_id"):
        correct += Counter(group["true_group_id"]).most_common(1)[0][1]

    return correct / len(df) if len(df) else 0.0


def optional_sklearn_metrics(df: pd.DataFrame) -> dict:
    """
    Add standard clustering metrics when scikit-learn is installed.

    The script still works without sklearn because these metrics are optional.
    """

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


def evaluate(
    df: pd.DataFrame,
    threshold: float,
    location_filter: bool = False,
    embedding_mode: str = "description_baseline",
) -> dict:
    """
    Combine all evaluation metrics for one threshold value.

    This lets us compare strict thresholds, which reduce false merges, against
    lower thresholds, which improve recall but may group unrelated issues.
    """

    true_sizes = df["true_group_id"].value_counts()
    pred_sizes = df["pred_group_id"].value_counts()

    metrics = {
        "threshold": threshold,
        "embedding_mode": embedding_mode,
        "rows": len(df),
        "true_groups": df["true_group_id"].nunique(),
        "predicted_groups": df["pred_group_id"].nunique(),
        "true_groups_with_2_plus_images": int((true_sizes >= 2).sum()),
        "predicted_groups_with_2_plus_images": int((pred_sizes >= 2).sum()),
        "cluster_purity": cluster_purity(df),
        "location_filter": location_filter,
        "rows_with_location": int(df["photo_location_id"].astype(bool).sum())
        if "photo_location_id" in df.columns
        else 0,
        "rows_missing_location": int((~df["photo_location_id"].astype(bool)).sum())
        if "photo_location_id" in df.columns
        else len(df),
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
    """
    Print concrete false merge and false split examples.

    These examples make the metrics easier to explain because we can point to
    exact line_number pairs where grouping made the wrong decision.
    """

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


def select_output_paths(production_embeddings: bool, location_filter: bool) -> tuple[Path, Path]:
    """
    Choose output files based on the eval mode.

    This keeps baseline, location-filtered, production-style embedding, and
    production-style embedding + location-filtered results separate.
    """

    if production_embeddings and location_filter:
        return (
            METRICS_PROD_EMBEDDINGS_LOCATION_OUT,
            PREDICTIONS_PROD_EMBEDDINGS_LOCATION_OUT,
        )

    if production_embeddings:
        return METRICS_PROD_EMBEDDINGS_OUT, PREDICTIONS_PROD_EMBEDDINGS_OUT

    if location_filter:
        return METRICS_LOCATION_OUT, PREDICTIONS_LOCATION_OUT

    return METRICS_OUT, PREDICTIONS_OUT


def main() -> None:
    """
    Command-line entry point to run one threshold or a full threshold sweep.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.94)
    parser.add_argument("--thresholds", default="0.70,0.75,0.80,0.85,0.90,0.94,0.95,0.97")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--location-filter", action="store_true")
    parser.add_argument("--production-embeddings", action="store_true")
    args = parser.parse_args()

    df = load_eval_csv(EVAL_CSV_PATH)

    if args.location_filter and "photo_location_id" not in df.columns:
        raise ValueError(
            "--location-filter requires a real photo_location_id column in the eval CSV."
        )

    metrics_out, predictions_out = select_output_paths(
        production_embeddings=args.production_embeddings,
        location_filter=args.location_filter,
    )

    embedding_mode = (
        "production_style"
        if args.production_embeddings
        else "description_baseline"
    )

    if args.max_rows:
        df = df.head(args.max_rows).copy()

    summarize_ground_truth(df)

    if args.check_only:
        print("\nCheck-only complete.")
        return

    embeddings = generate_embeddings(
        df,
        production_style=args.production_embeddings,
    )

    if args.sweep:
        rows = []

        for threshold in parse_thresholds(args.thresholds):
            predicted = predict_groups(
                df,
                embeddings,
                threshold,
                location_filter=args.location_filter,
            )
            metrics = evaluate(
                predicted,
                threshold,
                location_filter=args.location_filter,
                embedding_mode=embedding_mode,
            )
            rows.append(metrics)

        sweep_df = pd.DataFrame(rows)
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        sweep_df.to_csv(metrics_out, index=False)

        print("\n=== Threshold Sweep ===")
        print(sweep_df.to_string(index=False))
        print(f"\nSaved metrics to: {metrics_out}")

        best = sweep_df.sort_values("pairwise_f1", ascending=False).iloc[0]
        print("\n=== Best Threshold by Pairwise F1 ===")
        print(best.to_string())

    predicted = predict_groups(
        df,
        embeddings,
        args.threshold,
        location_filter=args.location_filter,
    )
    metrics = evaluate(
        predicted,
        args.threshold,
        location_filter=args.location_filter,
        embedding_mode=embedding_mode,
    )

    print_metrics(metrics)
    show_error_examples(predicted)

    predictions_out.parent.mkdir(parents=True, exist_ok=True)
    predicted.to_csv(predictions_out, index=False)

    print(f"\nSaved predictions to: {predictions_out}")


if __name__ == "__main__":
    main()
