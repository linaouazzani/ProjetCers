import pdfplumber, re, sys

def check_page(pdf_path, page_idx):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_idx]
        words = page.extract_words(keep_blank_chars=True, extra_attrs=["x0", "x1", "top"])
        
    print(f"\n=== PAGE {page_idx+1} - extract_words() ===")
    for w in words:
        txt = w["text"].strip()
        if txt and re.match(r'^-?[\d.]+$', txt):
            print(f"  x0={w['x0']:.1f} top={w['top']:.1f} text={repr(txt)}")
        elif txt in ['L', 'R', 'cm', 'm/s', 'N/s']:
            print(f"  x0={w['x0']:.1f} top={w['top']:.1f} text={repr(txt)} ** UNIT **")

# Adam SLJ page 2 (Jump Height Left: 13.7 L vs 9.7 L)
print("=== ADAM SLJ ===")
check_page("C:/Users/HP/Downloads/slj.pdf", 1)
check_page("C:/Users/HP/Downloads/slj.pdf", 2)  # RSI Right + Asymmetry page

# Adam CMJ page 1 (29.1 cm vs 24.8 cm)
print("\n=== ADAM CMJ ===")
check_page("C:/Users/HP/Downloads/cmj.pdf", 0)
check_page("C:/Users/HP/Downloads/cmj.pdf", 2)  # Landing Asymmetry
