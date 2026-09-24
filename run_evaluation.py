import json
import time
from sentence_transformers import SentenceTransformer, util
from run_pipeline import run_full_pipeline
from classifier_agent import classify_ticket

model = SentenceTransformer("all-MiniLM-L6-v2")

with open("eval_set.json", "r") as f:
    eval_set = json.load(f)

results = []

for i, item in enumerate(eval_set):
    print(f"\n=== Evaluating {i+1}/{len(eval_set)} ===")
    print("Message:", item["message"][:80])

    predicted = classify_ticket(item["message"])

    category_correct = predicted["category"].upper() == item["true_category"].upper()

    true_intent_embedding = model.encode([item["true_intent"].replace("_", " ")])
    predicted_intent_embedding = model.encode([predicted["intent"].replace("_", " ")])
    similarity = util.cos_sim(true_intent_embedding, predicted_intent_embedding).item()
    intent_semantically_correct = similarity >= 0.7

    print(f"True: {item['true_category']}/{item['true_intent']} | Predicted: {predicted['category']}/{predicted['intent']}")
    print(f"Category correct: {category_correct} | Intent similarity: {similarity:.2f} | Semantically correct: {intent_semantically_correct}")

    results.append({
        "message": item["message"],
        "true_category": item["true_category"],
        "true_intent": item["true_intent"],
        "predicted_category": predicted["category"],
        "predicted_intent": predicted["intent"],
        "category_correct": category_correct,
        "intent_similarity": similarity,
        "intent_semantically_correct": intent_semantically_correct
    })

    time.sleep(5)

with open("eval_results.json", "w") as f:
    json.dump(results, f, indent=2)

category_accuracy = sum(r["category_correct"] for r in results) / len(results)
intent_semantic_accuracy = sum(r["intent_semantically_correct"] for r in results) / len(results)
avg_similarity = sum(r["intent_similarity"] for r in results) / len(results)

print(f"\n\nCategory accuracy: {category_accuracy:.1%}")
print(f"Intent semantic accuracy (similarity \u2265 0.7): {intent_semantic_accuracy:.1%}")
print(f"Average intent similarity: {avg_similarity:.3f}")