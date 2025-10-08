from pathlib import Path
import json

TXT_DIR = Path("data/txt")
OUT_DIR = Path("processed/chunks")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paramètres de découpe
CHUNK_SIZE = 1000     # ~ caractères par chunk
OVERLAP = 200         # recouvrement entre chunks

def chunk_text(t: str, size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    i = 0
    n = len(t)
    step = max(1, size - overlap)
    while i < n:
        piece = t[i:i+size]
        if piece.strip():
            chunks.append(piece)
        i += step
    return chunks

def main():
    txt_files = sorted(TXT_DIR.glob("*.txt"))
    if not txt_files:
        print("Aucun .txt trouvé dans data/txt/. Lance d'abord pdf_extractor.py")
        return

    for txt in txt_files:
        text = txt.read_text(encoding="utf-8", errors="ignore")
        pieces = chunk_text(text)
        out = OUT_DIR / f"{txt.stem}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for idx, c in enumerate(pieces, start=1):
                f.write(json.dumps({
                    "id": f"{txt.stem}__{idx}",
                    "source": txt.name,
                    "text": c
                }, ensure_ascii=False) + "\n")
        print(f"✅ {txt.name}: {len(pieces)} chunks → {out.name}")

if __name__ == "__main__":
    main()
