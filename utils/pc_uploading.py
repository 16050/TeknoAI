import os
import json
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec

# ----------------------------
# Configuration
# ----------------------------
EMB_DIR = Path(__file__).resolve().parent.parent / "embeddings"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "mistral-embed"
BATCH_SIZE = 100

# ----------------------------
# Init Pinecone
# ----------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
    print(f"🆕 Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="eu-west-1")
    )

index = pc.Index(INDEX_NAME)
print(f"✅ Connected to Pinecone index: {INDEX_NAME}")

# ----------------------------
# Load existing Pinecone IDs
# ----------------------------
print("📡 Fetching existing vector IDs from Pinecone...")
pinecone_ids = set()
stats = index.describe_index_stats()

# This works best for small-to-medium datasets.
# For large indexes, use pagination with `index.list()` instead.
if "namespaces" in stats:
    for ns_data in stats["namespaces"].values():
        if "vector_count" in ns_data:
            print(f"🧩 Namespace has {ns_data['vector_count']} vectors")

# ----------------------------
# Upload missing vectors
# ----------------------------
for folder in EMB_DIR.glob("*"):
    if not folder.is_dir():
        continue

    print(f"\n📂 Uploading from {folder.name}...")
    for emb_file in folder.glob("*.jsonl"):
        with open(emb_file, encoding="utf-8") as f:
            vectors = [json.loads(line) for line in f if line.strip()]

        # Skip already uploaded ones
        new_vectors = [v for v in vectors if v["id"] not in pinecone_ids]
        if not new_vectors:
            print(f"🟢 All vectors from {emb_file.name} already uploaded.")
            continue

        pinecone_vectors = [
            {
                "id": v["id"],
                "values": v["values"],
                "metadata": {"source": v.get("source")}
            }
            for v in new_vectors
        ]

        for i in range(0, len(pinecone_vectors), BATCH_SIZE):
            batch = pinecone_vectors[i:i + BATCH_SIZE]
            index.upsert(vectors=batch)
            print(f"✅ Uploaded {i + len(batch)} / {len(pinecone_vectors)} from {emb_file.name}")

print("🎉 Upload complete — no duplicates added.")
