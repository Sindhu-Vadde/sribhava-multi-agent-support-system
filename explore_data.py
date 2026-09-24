from datasets import load_dataset
from clean_data import clean_and_fill_placeholders, find_remaining_placeholders

dataset = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset")

sample_row = dataset["train"][0]
print("Original:", sample_row["instruction"])
print("Cleaned:", clean_and_fill_placeholders(sample_row["instruction"]))

print("\nChecking for remaining placeholders across the full dataset...")
remaining = find_remaining_placeholders(dataset)
print("Remaining placeholders after cleaning:", len(remaining))
for p in sorted(remaining):
    print(p)