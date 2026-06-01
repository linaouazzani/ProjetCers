import pdfplumber, sys

pdf_path = sys.argv[1]
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        print(f"\n{'='*60}")
        print(f"PAGE {i+1} (len={len(text)})")
        print('='*60)
        print(repr(text[:3000]) if len(text) > 3000 else repr(text))
