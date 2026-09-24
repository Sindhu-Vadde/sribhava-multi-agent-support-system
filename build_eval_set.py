from datasets import load_dataset
import random
import json

dataset = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset")

random.seed(42)
sample_indices = random.sample(range(len(dataset["train"])), 20)

eval_set = []
for i in sample_indices:
    row = dataset["train"][i]
    eval_set.append({
        "message": row["instruction"],
        "true_category": row["category"],
        "true_intent": row["intent"]
    })

with open("eval_set.json", "w") as f:
    json.dump(eval_set, f, indent=2)

print("Saved", len(eval_set), "evaluation tickets to eval_set.json")
for item in eval_set[:3]:
    print(item)