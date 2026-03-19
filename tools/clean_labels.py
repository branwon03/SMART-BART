import csv

mapping = {
    "build": "BUILDINGS",
    "ground": "GROUND",
    "grounds": "GROUNDS",
    "mechan": "MECHANICAL",
    "elect": "ELECTRICAL",
    "comm": "COMMS",
    "elevator": "ELEVATOR_ESCALATOR",
    "escalator": "ELEVATOR_ESCALATOR",
    "fare": "FARE_COLLECTION",
    "system": "SYSTEM_SERVICE",
    "structures": "STRUCTURES",
    "track": "TRACK",
}

def normalize(label):
    label = label.lower()

    for key in mapping:
        if key in label:
            return mapping[key]
        
    return "UNKNOWN"

def clean_file(input_file, output_file):
    cleaned = []

    with open(input_file) as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            image = row[0]
            label = normalize(row[1])
            cleaned.append((image, label))
    
    with open(output_file, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["image", "label"])
        writer.writerows(cleaned)

clean_file("train.csv", "clean_train.csv")
clean_file("valid.csv", "clean_valid.csv")

print("Done cleaning labels.")