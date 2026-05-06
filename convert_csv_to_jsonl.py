import csv
import json
import random
from pathlib import Path

from labeling import GEMINI_USER_INSTRUCTION

in_csv = Path("datasets/BART_label_review_template.csv")
out_stem = Path("datasets/BART_labeled_data_reviewed")
RANDOM_SEED = 42
TRAIN_RATIO = 0.7
VAL_RATIO = 0.2


def pick(row, auto_key, final_key):
    final = row.get(final_key, "").strip()
    if final:
        return final
    if auto_key is None:
        return ""
    return row.get(auto_key, "").strip()


def row_to_obj(row):
    discipline = pick(row, "auto_discipline", "final_discipline")
    condition = pick(row, "auto_condition", "final_condition")
    priority = pick(row, "auto_priority", "final_priority")
    description = pick(row, None, "final_description_optional")
    model_text = (
        f"Discipline: {discipline}, Condition: {condition}, Priority: {priority}\n"
        f"Description: {description}"
    )
    return {
        "system_instruction": {"parts": [{"text": GEMINI_USER_INSTRUCTION}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Analyze this infrastructure image."},
                    {
                        "file_data": {
                            "mime_type": "image/jpeg",
                            "file_uri": row["image_uri"].strip(),
                        }
                    },
                ],
            },
            {"role": "model", "parts": [{"text": model_text}]},
        ],
    }


def split_sizes(n):
    train_n = int(n * TRAIN_RATIO)
    val_n = int(n * VAL_RATIO)
    test_n = n - train_n - val_n
    return train_n, val_n, test_n


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f_out:
        for row in rows:
            f_out.write(json.dumps(row_to_obj(row), ensure_ascii=False) + "\n")


def main():
    with in_csv.open(newline="", encoding="utf-8") as f_in:
        rows = list(csv.DictReader(f_in))

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(rows)

    n = len(rows)
    train_n, val_n, test_n = split_sizes(n)
    train_rows = rows[:train_n]
    val_rows = rows[train_n : train_n + val_n]
    test_rows = rows[train_n + val_n :]

    splits = [
        ("train", train_rows, out_stem.with_name(out_stem.name + "_train.jsonl")),
        ("val", val_rows, out_stem.with_name(out_stem.name + "_val.jsonl")),
        ("test", test_rows, out_stem.with_name(out_stem.name + "_test.jsonl")),
    ]

    for name, subset, path in splits:
        write_jsonl(path, subset)
        print(f"Wrote {len(subset)} rows ({name}): {path}")

    print(f"Total: {n} (train {train_n}, val {val_n}, test {test_n})")


if __name__ == "__main__":
    main()
