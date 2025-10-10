from pathlib import Path
import json, os
from mistralai.client import MistralClient
from pinecone import Pinecone, ServerlessSpec

CHK_DIR = Path(__file__).resolve().parent.parent / "processed/chunks"
OUT_DIR = Path("embeddings/vectors")

# Load data from all JSONL files
data = []
for file in CHK_DIR.glob("*.jsonl"):
    for line in open(file, encoding="utf-8"):
        if line.strip():
            data.append(json.loads(line))

print(f"Loaded {len(data)} chunks.")

# Init clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "mistral-embed"

# Create index if it doesn't exist
if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)

#client = Mistral(api_key="f9czE4s5JWlzlrNB9fUfevRMDww7ds0P")
client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

def embed(docs: list[str]) -> list[list[float]]:
  embeddings = client.embeddings(
      model="mistral-embed",
      input=docs,
  )
  return embeddings.data

# generate embeddings
embeddings = embed([d["text"] for d in data])

# extract embedding vectors
embeddings = [e.embedding for e in embeddings]

# prepare vectors for Pinecone
vectors = []
for d, e in zip(data, embeddings):
    vectors.append({
        "id": d['id'],
        "values": e,
        "metadata": {'text': d['text']}
    })

# upload to Pinecone
index.upsert(vectors=vectors)
print(f"✅ Uploaded {len(vectors)} vectors to Pinecone!")
