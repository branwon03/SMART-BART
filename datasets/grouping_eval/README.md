# Grouping Evaluation

This folder contains an offline grouping evaluation workflow for checking whether image reports that refer to the same physical issue are assigned to the same predicted group.

## What this evaluates

This evaluates the grouping step in isolation. It doesn't measure the full live end-to-end pipeline with classification, parser output, database writes, and frontend submission flow.

The purpose is to test whether the embedding-based grouping logic can correctly merge multi-angle reports of the same issue while avoiding false merges with similar-looking but different issues.

## Current campus evaluation subset

The current campus-based subset is a curated MVP evaluation set.

It includes:

- 100 total campus images
- 35 unique `true_group_id` labels
- visually checked ground-truth groups
- 0 missing images
- 0 extra images
- 0 exact duplicate image files

This subset is intentionally not random. It was curated to include both multi-angle images of the same issue and similar-looking hard negatives, so it is more useful for testing grouping behavior than a small random sample would be.

## Visual review

The dataset was visually reviewed in Colab by grouping images by `true_group_id`. Multi-image groups are shown first, followed by singleton groups.

Colab visual review notebook:

https://colab.research.google.com/drive/1wuVFsmDIDKF0RalhX46Qcqeo32IHK0_H?authuser=2#scrollTo=YIC9KBal1O57

The visual review confirmed:

- 100 CSV rows
- 100 images loaded
- 35 unique true groups
- 0 missing images
- 0 extra images

## Main metric result

The main run uses image-heavy production-style embeddings. Manual ground-truth descriptions were removed from the embedding input so the evaluation relies more on the image content instead of the hand-written labels.

Best balanced threshold from the 100-image image-heavy run:

| Threshold | Location filter | Precision | Recall | F1 | False positive pairs | False negative pairs |
|---|---:|---:|---:|---:|---:|---:|
| 0.94 | False | 0.863 | 0.956 | 0.907 | 24 | 7 |
| 0.94 | True, coarse location | 0.863 | 0.956 | 0.907 | 24 | 7 |

Coarse location filtering helped at lower thresholds, but it did not improve the best threshold result. This suggests the embedding similarity threshold is doing most of the grouping work, while location metadata can still be useful as a safety constraint when reliable production metadata exists.

## How to run the evaluation

The eval script depends on optional packages (pandas, scikit-learn, google-cloud-storage). Install them once:

```bash
uv sync --extra eval
```

Run the image-heavy threshold sweep:

```bash
uv run --extra eval python -m src.backend.grouping_eval_metrics \
  --input-csv datasets/grouping_eval/campus_grouping_eval_subset_no_manual_desc_100.csv \
  --image-dir datasets/grouping_eval/campus_images \
  --production-embeddings \
  --sweep \
  --metrics-out datasets/grouping_eval/campus_grouping_eval_metrics_image_heavy_100_v5.csv \
  --predictions-out datasets/grouping_eval/campus_grouping_eval_predictions_image_heavy_100_v5.csv
```

Run the same evaluation with coarse location filtering:

```bash
uv run --extra eval python -m src.backend.grouping_eval_metrics \
  --input-csv datasets/grouping_eval/campus_grouping_eval_subset_no_manual_desc_100_coarse_location.csv \
  --image-dir datasets/grouping_eval/campus_images \
  --production-embeddings \
  --location-filter \
  --sweep \
  --metrics-out datasets/grouping_eval/campus_grouping_eval_metrics_image_heavy_100_coarse_location_v5.csv \
  --predictions-out datasets/grouping_eval/campus_grouping_eval_predictions_image_heavy_100_coarse_location_v5.csv
```

## Notes

These results should be treated as an MVP evaluation result, not a final production benchmark. The subset is useful because the labels were visually checked, but a larger future benchmark should include more locations, more object types, more random sampling, and more real end-to-end submissions.