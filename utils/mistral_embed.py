import os
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# ----------------------------
# Configuration
# ----------------------------
CHK_DIR = Path(__file__).resolve().parent.parent / "processed/chunks"
OUT_FILE = Path(__file__).resolve().parent.parent / "embeddings" / "vectors.jsonl"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "mistral-embed"
BATCH_SIZE = 8
MAX_META_LENGTH = 1000  # truncate metadata text to 1000 chars

# ----------------------------
# Initialize Pinecone
# ----------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="eu-west-1")
    )

index = pc.Index(INDEX_NAME)

# ----------------------------
# Load chunks
# ----------------------------
data = []
for file in CHK_DIR.glob("*.jsonl"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

print(f"✅ Loaded {len(data)} chunks")

# ----------------------------
# Load existing cache
# ----------------------------
cached_vectors = []
cached_ids = set()
if OUT_FILE.exists():
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            vec = json.loads(line)
            cached_vectors.append(vec)
            cached_ids.add(vec["id"])
    print(f"✅ Found {len(cached_ids)} vectors in local cache")

# ----------------------------
# Find vectors already in Pinecone
# ----------------------------
pinecone_ids = set()
stats = index.describe_index_stats()
# stats["namespaces"] may be empty if you use the default namespace
for ns, ns_info in stats.get("namespaces", {}).items():
    pinecone_ids.update(ns_info.get("vectors", {}).keys())

print(f"✅ Found {len(pinecone_ids)} vectors in Pinecone")

# ----------------------------
# Prepare new chunks to embed
# ----------------------------
data_to_embed = [d for d in data if d["id"] not in cached_ids]
print(f"🟢 {len(data_to_embed)} new chunks to embed")

# ----------------------------
# Load embedding model
# ----------------------------
model = SentenceTransformer("intfloat/e5-large-v2")  # 1024-dimensional embeddings

# ----------------------------
# Embed new chunks and update cache
# ----------------------------
for i in range(0, len(data_to_embed), BATCH_SIZE):
    batch = data_to_embed[i:i + BATCH_SIZE]
    texts = [d["text"] for d in batch]

    embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True)

    with open(OUT_FILE, "a", encoding="utf-8") as f:
        for d, e in zip(batch, embeddings):
            vec = {
                "id": d["id"],
                "values": e.tolist() if hasattr(e, "tolist") else list(e),
                "text": d["text"],  # full text in cache
                "source": d.get("source")
            }
            cached_vectors.append(vec)
            cached_ids.add(vec["id"])
            f.write(json.dumps(vec) + "\n")

    print(f"✅ Embedded {i + len(batch)} / {len(data_to_embed)} new chunks")

# ----------------------------
# Prepare vectors to upload to Pinecone
# Only upload vectors that are NOT yet in Pinecone
# ----------------------------
MAX_META_LENGTH = 1000

vectors_to_upload = []
for vec in cached_vectors:
    if vec["id"] not in pinecone_ids:
        text_preview = vec.get("text")  # for old-style vectors
        if text_preview is None:
            text_preview = vec.get("metadata", {}).get("text", "")
        source = vec.get("source") or vec.get("metadata", {}).get("source")

        vectors_to_upload.append({
            "id": vec["id"],
            "values": vec["values"],
            "metadata": {
                "text_preview": text_preview[:MAX_META_LENGTH],
                "source": source
            }
        })
# ----------------------------
# Upload to Pinecone in batches
# ----------------------------
for i in range(0, len(vectors_to_upload), BATCH_SIZE):
    batch = vectors_to_upload[i:i + BATCH_SIZE]
    index.upsert(vectors=batch)
    print(f"✅ Uploaded {i + len(batch)} / {len(vectors_to_upload)} vectors to Pinecone")

if not vectors_to_upload:
    print("✅ All cached vectors are already in Pinecone. Nothing to upload.")
