import re
import pickle
from sentence_transformers import SentenceTransformer

with open("sribhava_policies.md", "r", encoding="utf-8") as f:
    full_text = f.read()

sections = re.split(r"\n## POLICY: ", full_text)

policy_chunks = []
for section in sections[1:]:
    lines = section.split("\n", 1)
    title = lines[0].strip()
    content = lines[1].strip() if len(lines) > 1 else ""
    policy_chunks.append({"title": title, "content": content})

print("Total policy chunks found:", len(policy_chunks))
for chunk in policy_chunks:
    print("-", chunk["title"])

model = SentenceTransformer("all-MiniLM-L6-v2")

texts_to_embed = [chunk["content"] for chunk in policy_chunks]

print("\nEmbedding", len(texts_to_embed), "policy chunks...")
embeddings = model.encode(texts_to_embed, show_progress_bar=True)

print("Done. Shape:", embeddings.shape)

with open("policy_embeddings.pkl", "wb") as f:
    pickle.dump({"embeddings": embeddings, "data": policy_chunks}, f)

print("Saved to policy_embeddings.pkl")