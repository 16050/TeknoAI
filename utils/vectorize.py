import os
import json
import time
from pathlib import Path
from mistralai.client import MistralClient
from pinecone import Pinecone, ServerlessSpec

# ------------------------------
# 1. Load API keys from environment
# ------------------------------
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")
PINECONE_KEY = os.getenv("PINECONE_API_KEY")

if not MISTRAL_KEY or not PINECONE_KEY:
    raise ValueError("Please set MISTRAL_API_KEY and PINECONE_API_KEY environment variables.")

# ------------------------------
# 2. Initialize clients
# ------------------------------
client = MistralClient(api_key=MISTRAL_KEY)
pc = Pinecone(api_key=PINECONE_KEY)

# ------------------------------
# 3. Setup Pinecone index
# ------------------------------
INDEX_NAME = "mistral-embed"

if INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud='aws', region='eu-west-1')
    )

index = pc.Index(INDEX_NAME)

# ------------------------------
# 4. Load JSONL chunks
# ------------------------------
CHK_DIR = Path(__file__).resolve().parent.parent / "processed/chunks"
data = []

for file in CHK_DIR.glob("*.jsonl"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

print(f"✅ Loaded {len(data)} chunks.")

# ------------------------------
# 5. Optional: split very long chunks (not strictly necessary here)
# ------------------------------
def split_long_text(text, max_chars=1000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

processed_texts = []
processed_ids = []

for d in data:
    splits = split_long_text(d["text"], max_chars=1000)
    for i, s in enumerate(splits):
        processed_texts.append(s)
        processed_ids.append(f"{d['id']}_{i}" if len(splits) > 1 else d["id"])

print(f"✅ Total sub-chunks: {len(processed_texts)}")

# ------------------------------
# 6. Load cached embeddings
# ------------------------------
OUT_FILE = Path(__file__).resolve().parent.parent / "embeddings" / "vectors.jsonl"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

cached_ids = set()
if OUT_FILE.exists():
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cached_ids.add(json.loads(line)["id"])
    print(f"✅ Found {len(cached_ids)} cached embeddings")

# ------------------------------
# 7. Embed one chunk at a time (free tier safe)
# ------------------------------
vectors = []

for idx, text in zip(processed_ids, processed_texts):
    if idx in cached_ids:
        continue  # skip already embedded

    success = False
    retries = 0
    while not success and retries < 5:
        try:
            response = client.embeddings(model="mistral-embed", input=[text])
            emb = response.data[0].embedding
            vector = {"id": idx, "values": emb, "metadata": {"text": text}}
            vectors.append(vector)

            # Save to cache immediately
            with open(OUT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(vector) + "\n")

            success = True
            print(f"✅ Embedded chunk {idx}")
        except Exception as e:
            msg = str(e)
            if "3505" in msg or "429" in msg:
                wait = 5 + 2 * retries  # exponential-ish backoff
                print(f"⚠️ Capacity exceeded. Waiting {wait}s before retry...")
                time.sleep(wait)
                retries += 1
            else:
                raise e

    # Always wait a bit between requests
    time.sleep(5)

print(f"✅ Finished embedding {len(vectors)} new chunks")

# ------------------------------
# 8. Upload vectors to Pinecone in small batches
# ------------------------------
BATCH_SIZE = 10
for i in range(0, len(vectors), BATCH_SIZE):
    batch = vectors[i:i+BATCH_SIZE]
    index.upsert(vectors=batch)
    print(f"✅ Uploaded batch {i//BATCH_SIZE + 1} ({len(batch)} vectors)")
