import csv, json
from pathlib import Path
in_csv = Path("datasets/BART_label_review_template.csv")
out_jsonl = Path("datasets/BART_labeled_data_reviewed.jsonl")
SYSTEM_TEXT = (
      "You are a BART maintenance inspector. Provide the Discipline, "
      "Condition, Priority, and Description for the observed asset."
  )
def pick(row, auto_key, final_key):
      if row.get("decision", "").strip().lower() == "fix" and row.get(final_key, "").strip():
          return row[final_key].strip()
      return row.get(auto_key, "").strip()
with in_csv.open(newline="", encoding="utf-8") as f_in, out_jsonl.open("w", encoding="utf-8") as
    
    f_out:
reader = csv.DictReader(f_in)
for row in reader:
          discipline = pick(row, "auto_discipline", "final_discipline")
          condition = pick(row, "auto_condition", "final_condition")
          priority = pick(row, "auto_priority", "final_priority")
          description = pick(row, "auto_description", "final_description_optional")
          model_text = (
              f"Discipline: {discipline}, Condition: {condition}, Priority: {priority}\n"
              f"Description: {description}"
          )
          obj = {
              "system_instruction": {
                  "parts": [{"text": SYSTEM_TEXT}]
              },
              "contents": [
                  {
                      "role": "user",
                      "parts": [
                          {"text": "Analyze this infrastructure image."},
                          {
                              "file_data": {
                                  "mime_type": "image/jpeg",
                                  "file_uri": row["image_uri"].strip()
                              }
                          }
                      ]
                  },
                  {
                      "role": "model",
                      "parts": [{"text": model_text}]
                  }
              ]
          }
          f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
print(f"Wrote: {out_jsonl}")
