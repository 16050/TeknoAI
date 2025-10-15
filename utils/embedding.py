import os
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ----------------------------
# 🔧 Configuration
# ----------------------------
CHK_DIR = Path(__file__).resolve().parent.parent / "processed/chunks"
EMB_DIR = Path(__file__).resolve().parent.parent / "embeddings"
EMB_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 8
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ----------------------------
# 🧩 Load embedding model
# ----------------------------
model = SentenceTransformer("intfloat/e5-large-v2")  # 1024-dim model

# ----------------------------
# 🧠 Load ALL existing IDs across every embedding file
# ----------------------------
print("📡 Scanning existing embeddings...")
existing_ids = set()
for emb_file in EMB_DIR.rglob("*.jsonl"):
    with open(emb_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                existing_ids.add(json.loads(line)["id"])
            except Exception:
                pass

print(f"✅ Found {len(existing_ids)} embedded IDs already stored globally.")

# ----------------------------
# 📚 Process each chunk file
# ----------------------------
for chunk_file in CHK_DIR.glob("*.jsonl"):
    print(f"\n📄 Processing {chunk_file.name}")

    # Load all chunks
    with open(chunk_file, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]

    # Skip already embedded ones (globally)
    new_data = [d for d in data if d["id"] not in existing_ids]
    if not new_data:
        print(f"🟢 No new chunks to embed in {chunk_file.name}")
        continue

    # Folder for this chunk file's embeddings
    chunk_out_dir = EMB_DIR / chunk_file.stem
    chunk_out_dir.mkdir(parents=True, exist_ok=True)

    # Determine file rotation info
    part_idx = len(list(chunk_out_dir.glob("*.jsonl"))) + 1
    part_path = chunk_out_dir / f"part_{part_idx:04d}.jsonl"
    current_size = part_path.stat().st_size if part_path.exists() else 0
    f_out = open(part_path, "a", encoding="utf-8")

    # ----------------------------
    # 🚀 Embed new chunks
    # ----------------------------
    for i in range(0, len(new_data), BATCH_SIZE):
        batch = new_data[i:i + BATCH_SIZE]
        texts = [d["text"] for d in batch]
        embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True)

        for d, e in zip(batch, embeddings):
            vec = {
                "id": d["id"],
                "values": e.tolist(),
                "source": d.get("source")
            }

            line = json.dumps(vec) + "\n"
            line_size = len(line.encode("utf-8"))

            # Split file if size exceeds 20MB
            if current_size + line_size > MAX_FILE_SIZE_BYTES:
                f_out.close()
                part_idx += 1
                part_path = chunk_out_dir / f"part_{part_idx:04d}.jsonl"
                f_out = open(part_path, "a", encoding="utf-8")
                current_size = 0
                print(f"🌀 Rotated to new file: {part_path.name}")

            f_out.write(line)
            current_size += line_size
            existing_ids.add(d["id"])  # ✅ mark as embedded globally

        print(f"✅ Embedded {i + len(batch)} / {len(new_data)} new chunks")

    f_out.close()
    print(f"💾 Saved embeddings for {chunk_file.name} in {chunk_out_dir}")
