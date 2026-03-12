import json
import random 
import csv

with open("Labels/annotated_labels.json") as f:
    data = json.load(f) 


dataset = []

#loop through each item in the directory 
#data.items() give, the filename and the label information
for image, info in data.items():

    #remove the period and any extra spaces from the label 
    label = info["raw_response"].replace(".", "").strip()

    #add the image and label to the dataset
    dataset.append((image, label))


random.shuffle(dataset)

split = int(0.8 * len(dataset))

train = dataset[:split]
valid = dataset[split:]

print("Training set size:", len(train))
print("Validation set size:", len(valid))

#save the training set to a csv file
with open("train.csv", "w") as f:

    writer = csv.writer(f)
    writer.writerow(["image", "label"])
    writer.writerows(train)

#save the validation set to a csv file
with open("valid.csv", "w") as f:
    
    writer = csv.writer(f)
    writer.writerow(["image", "label"])
    writer.writerows(valid)