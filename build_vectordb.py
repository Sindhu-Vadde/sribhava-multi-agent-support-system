import pickle
import chromadb
from chromadb.config import Settings

with open("policy_embeddings.pkl", "rb") as f:
    saved = pickle.load(f)

embeddings = saved["embeddings"]
policy_chunks = saved["data"]

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        anonymized_telemetry=False
    )
)
collection = client.get_or_create_collection(name="sribhava_policies")

print("Items already in collection:", collection.count())

if collection.count() == 0:
    ids = [str(i) for i in range(len(policy_chunks))]
    documents = [chunk["content"] for chunk in policy_chunks]
    metadatas = [{"title": chunk["title"]} for chunk in policy_chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas
    )
    print("Added", collection.count(), "items to the vector database")
else:
    print("Data already loaded, skipping add step.")