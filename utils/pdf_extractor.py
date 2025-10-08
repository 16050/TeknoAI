from pathlib import Path
from PyPDF2 import PdfReader

RAW_DIR = Path("data/raw")
TXT_DIR = Path("data/txt")
TXT_DIR.mkdir(parents=True, exist_ok=True)

def extract_text(pdf_path: Path) -> str:
    text = []
    reader = PdfReader(str(pdf_path))
    for p in reader.pages:
        text.append(p.extract_text() or "")
    return "\n".join(text).strip()

def main():
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        print("Aucun PDF trouvé dans data/raw/")
        return
    for pdf in pdfs:
        out = TXT_DIR / (pdf.stem + ".txt")
        print(f"📄 {pdf.name} → {out.name}")
        text = extract_text(pdf)
        if not text:
            print(f"⚠️ Aucun texte lisible: {pdf.name}")
            continue
        out.write_text(text, encoding="utf-8")
        print(f"✅ Enregistré: {out}")

if __name__ == "__main__":
    main()
