"""
vald_parser.py — Parser PDFs VALD ForceDecks
Projet CERS Capbreton — version 3 (structure réelle avec 2 sessions par PDF)

Structure réelle des PDFs VALD Hub exportés via Firefox → Imprimer → PDF :
  - Un PDF SLJ contient 2 sessions (entrée + sortie) sur ~7 pages
  - Un PDF CMJ contient 2 sessions (entrée + sortie) sur ~4 pages
  - Les valeurs par session sont dans les annotations graphiques
    Ex : "Jump Height (Imp-Mom) [cm]  9.7 L\n13.7 L"
         → 1ère valeur = date ancienne = ENTRÉE
         → 2ème valeur = date récente  = SORTIE
  - Distinguer L (Gauche) et R (Droite) pour SLJ
  - Distinguer "cm" (CMJ bilatéral) pour CMJ Jump Height

API principale :
  parse_slj_pdf(pdf_source) → dict avec clés _ent / _sort
  parse_cmj_pdf(pdf_source) → dict avec clés _ent / _sort

Fonctions historiques conservées (rétrocompatibilité) :
  parse_vald_slj(), parse_vald_cmj(), parse_vald_pdf()
"""

import re
import pdfplumber
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _safe_float(s):
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, AttributeError, TypeError):
        return None


def _extract_dates(text):
    """Extrait et classe les dates uniques trouvées dans le texte.
    Retourne (date_entree, date_sortie) = (ancienne, récente) format JJ/MM/AAAA."""
    raw = re.findall(r'(\d{2}/\d{2}/\d{4})', text)
    seen, objs = set(), []
    for d in raw:
        if d not in seen:
            seen.add(d)
            try:
                objs.append(datetime.strptime(d, "%d/%m/%Y"))
            except ValueError:
                pass
    if len(objs) >= 2:
        return min(objs).strftime("%d/%m/%Y"), max(objs).strftime("%d/%m/%Y")
    if len(objs) == 1:
        s = objs[0].strftime("%d/%m/%Y")
        return s, s
    return None, None


# ---------------------------------------------------------------------------
# API principale — parse_slj_pdf
# ---------------------------------------------------------------------------

def parse_slj_pdf(pdf_source):
    """
    Parse un PDF SLJ exporté depuis VALD Hub.
    Le PDF contient 2 sessions (entrée + sortie) dans le même fichier.
    pdf_source : chemin str ou BytesIO.

    Retourne dict :
    {
        "slj_hauteur_g_ent":   float|None,   # Jump Height Left  entrée (cm)
        "slj_hauteur_g_sort":  float|None,   # Jump Height Left  sortie (cm)
        "slj_hauteur_d_ent":   float|None,   # Jump Height Right entrée (cm)
        "slj_hauteur_d_sort":  float|None,   # Jump Height Right sortie (cm)
        "rsi_g_ent":           float|None,   # RSI-modified Left  entrée (m/s)
        "rsi_g_sort":          float|None,   # RSI-modified Left  sortie (m/s)
        "rsi_d_ent":           float|None,   # RSI-modified Right entrée (m/s)
        "rsi_d_sort":          float|None,   # RSI-modified Right sortie (m/s)
        "slj_flight_g_ent":    float|None,   # Jump Height Flight Time Left  entrée (cm)
        "slj_flight_g_sort":   float|None,
        "slj_flight_d_ent":    float|None,
        "slj_flight_d_sort":   float|None,
        "peak_force_asym_ent": float|None,   # Concentric Peak Force Asymmetry entrée (%)
        "peak_force_asym_sort":float|None,
        "date_entree":         str|None,     # JJ/MM/AAAA
        "date_sortie":         str|None,
    }
    """
    result = {
        "slj_hauteur_g_ent":    None, "slj_hauteur_g_sort":  None,
        "slj_hauteur_d_ent":    None, "slj_hauteur_d_sort":  None,
        "rsi_g_ent":            None, "rsi_g_sort":          None,
        "rsi_d_ent":            None, "rsi_d_sort":          None,
        "slj_flight_g_ent":     None, "slj_flight_g_sort":   None,
        "slj_flight_d_ent":     None, "slj_flight_d_sort":   None,
        "peak_force_asym_ent":  None, "peak_force_asym_sort":None,
        "date_entree":          None, "date_sortie":         None,
    }

    with pdfplumber.open(pdf_source) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Dates
    result["date_entree"], result["date_sortie"] = _extract_dates(full_text)

    # SLJ Jump Height — Left (G) : "Jump Height (Imp-Mom) [cm]  9.7 L\n13.7 L"
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s+([\d.]+)\s*L\s+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["slj_hauteur_g_ent"]  = _safe_float(m.group(1))
        result["slj_hauteur_g_sort"] = _safe_float(m.group(2))

    # SLJ Jump Height — Right (D) : "Jump Height (Imp-Mom) [cm]  8.4 R  11 R"
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s+([\d.]+)\s*R\s+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["slj_hauteur_d_ent"]  = _safe_float(m.group(1))
        result["slj_hauteur_d_sort"] = _safe_float(m.group(2))

    # RSI-modified — Left (G) : "RSI-modified (Imp-Mom) [m/s]  0.13 L\n0.12 L"
    m = re.search(
        r'RSI-modifi(?:ed|é) \(Imp-Mom\) \[m/s\]\s*([\d.]+)\s*L\s+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["rsi_g_ent"]  = _safe_float(m.group(1))
        result["rsi_g_sort"] = _safe_float(m.group(2))

    # RSI-modified — Right (D) : "RSI-modified (Imp-Mom) [m/s]  0.11 R  0.11 R"
    m = re.search(
        r'RSI-modifi(?:ed|é) \(Imp-Mom\) \[m/s\]\s*([\d.]+)\s*R\s+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["rsi_d_ent"]  = _safe_float(m.group(1))
        result["rsi_d_sort"] = _safe_float(m.group(2))

    # Jump Height Flight Time — Left : "Jump Height (Flight Time) [cm]  10.9 L\n15.2 L"
    m = re.search(
        r'Jump Height \(Flight Time\) \[cm\]\s*([\d.]+)\s*L\s+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["slj_flight_g_ent"]  = _safe_float(m.group(1))
        result["slj_flight_g_sort"] = _safe_float(m.group(2))

    # Jump Height Flight Time — Right : "Jump Height (Flight Time) [cm]  9.3 R\n13.3 R"
    m = re.search(
        r'Jump Height \(Flight Time\) \[cm\]\s*([\d.]+)\s*R\s+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["slj_flight_d_ent"]  = _safe_float(m.group(1))
        result["slj_flight_d_sort"] = _safe_float(m.group(2))

    # Concentric Peak Force Asymmetry : "Asymmetry [%]  1.7\n1.9"
    m = re.search(r'Asymmetry \[%\]\s*([\d.]+)\s+([\d.]+)', full_text)
    if m:
        result["peak_force_asym_ent"]  = _safe_float(m.group(1))
        result["peak_force_asym_sort"] = _safe_float(m.group(2))

    return result


# ---------------------------------------------------------------------------
# API principale — parse_cmj_pdf
# ---------------------------------------------------------------------------

def parse_cmj_pdf(pdf_source):
    """
    Parse un PDF CMJ exporté depuis VALD Hub.
    Le PDF contient 2 sessions (entrée + sortie) dans le même fichier.
    pdf_source : chemin str ou BytesIO.

    Retourne dict :
    {
        "cmj_hauteur_ent":      float|None,  # Jump Height Imp-Mom entrée (cm)
        "cmj_hauteur_sort":     float|None,  # Jump Height Imp-Mom sortie (cm)
        "cmj_rfd_ent":          float|None,  # Concentric RFD entrée (N/s)
        "cmj_rfd_sort":         float|None,
        "cmj_landing_asym_ent": float|None,  # Peak Landing Force Asymmetry entrée (%)
        "cmj_landing_asym_sort":float|None,
        "cmj_landing_side_ent": str|None,    # "D" (positif) ou "G" (négatif)
        "cmj_landing_side_sort":str|None,
        "cmj_ecc_vel_ent":      float|None,  # Eccentric Peak Velocity entrée (m/s, négatif)
        "cmj_ecc_vel_sort":     float|None,
        "date_entree":          str|None,    # JJ/MM/AAAA
        "date_sortie":          str|None,
    }
    """
    result = {
        "cmj_hauteur_ent":      None, "cmj_hauteur_sort":     None,
        "cmj_rfd_ent":          None, "cmj_rfd_sort":         None,
        "cmj_landing_asym_ent": None, "cmj_landing_asym_sort":None,
        "cmj_landing_side_ent": None, "cmj_landing_side_sort":None,
        "cmj_ecc_vel_ent":      None, "cmj_ecc_vel_sort":     None,
        "date_entree":          None, "date_sortie":          None,
    }

    with pdfplumber.open(pdf_source) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Dates
    result["date_entree"], result["date_sortie"] = _extract_dates(full_text)

    # Jump Height Imp-Mom : "24.8 cm\n29.1 cm" — distingué de SLJ par le suffixe "cm"
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s*([\d.]+)\s*cm\s+([\d.]+)\s*cm',
        full_text
    )
    if m:
        result["cmj_hauteur_ent"]  = _safe_float(m.group(1))
        result["cmj_hauteur_sort"] = _safe_float(m.group(2))

    # Concentric RFD : "1000 N/s\n3419 N/s"
    m = re.search(
        r'Concentric RFD \[N/s\]\s*([\d.]+)\s*N/s\s+([\d.]+)\s*N/s',
        full_text
    )
    if m:
        result["cmj_rfd_ent"]  = _safe_float(m.group(1))
        result["cmj_rfd_sort"] = _safe_float(m.group(2))

    # Peak Landing Force Asymmetry : "55\n-17" (positif=D, négatif=G)
    m = re.search(r'Asymmetry \[%\]\s*(-?[\d.]+)\s+(-?[\d.]+)', full_text)
    if m:
        v1 = _safe_float(m.group(1))
        v2 = _safe_float(m.group(2))
        result["cmj_landing_asym_ent"]  = v1
        result["cmj_landing_asym_sort"] = v2
        if v1 is not None:
            result["cmj_landing_side_ent"]  = "D" if v1 > 0 else "G"
        if v2 is not None:
            result["cmj_landing_side_sort"] = "D" if v2 > 0 else "G"

    # Eccentric Peak Velocity : "-0.96 m/s\n-1.03 m/s"
    m = re.search(
        r'Eccentric Peak Velocity \[m/s\]\s*(-?[\d.]+)\s*m/s\s+(-?[\d.]+)\s*m/s',
        full_text
    )
    if m:
        result["cmj_ecc_vel_ent"]  = _safe_float(m.group(1))
        result["cmj_ecc_vel_sort"] = _safe_float(m.group(2))

    return result


# ---------------------------------------------------------------------------
# Fonctions historiques (rétrocompatibilité — format 1 session par PDF)
# ---------------------------------------------------------------------------

def _get_pages(pdf_source):
    """Retourne liste de pages, chaque page = liste de lignes."""
    with pdfplumber.open(pdf_source) as pdf:
        result = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            result.append(text.split("\n"))
        return result


HEADER_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
HEADER_DATA_RE = re.compile(r"^(\d+)\s+(\d+)\s+([\d.]+)$")


def _parse_header(lines):
    date, reps, bw_kg = None, None, None
    for line in lines:
        line = line.strip()
        if not date:
            m = HEADER_DATE_RE.search(line)
            if m:
                date = m.group(1)
        if reps is None:
            m = HEADER_DATA_RE.match(line)
            if m:
                reps = int(m.group(2))
                bw_kg = _safe_float(m.group(3))
    return {"date": date, "reps": reps, "bw_kg": bw_kg}


DATA_LINE_RE = re.compile(
    r"^([\d.]+)\s*-\s*([\d.]+)\s+([\d.]+)\s+([\d.]+%)\s+([\d.]+)$"
)


def _extract_side_average(lines, section_title, side):
    in_section = False
    in_side = False
    after_header = False
    for line in lines:
        ls = line.strip()
        if section_title.lower() in ls.lower():
            in_section = True; in_side = False; after_header = False
            continue
        if not in_section:
            continue
        if ls.upper() == (side + " SIDE"):
            in_side = True; after_header = False
            continue
        if not in_side:
            continue
        if "Range" in ls and "Average" in ls:
            after_header = True
            continue
        if after_header:
            m = DATA_LINE_RE.match(ls)
            if m:
                return _safe_float(m.group(3))
            if ls.upper().endswith(" SIDE") and ls.upper() != (side + " SIDE"):
                in_side = False; after_header = False
    return None


def _extract_bilateral_average(lines, section_title):
    in_section = False
    after_header = False
    for line in lines:
        ls = line.strip()
        if section_title.lower() in ls.lower():
            in_section = True; after_header = False
            continue
        if not in_section:
            continue
        if "Range" in ls and "Average" in ls:
            after_header = True
            continue
        if after_header:
            m = DATA_LINE_RE.match(ls)
            if m:
                return _safe_float(m.group(3))
            if ls and not re.match(r"^[\d.]", ls):
                break
    return None


def _deficit(a, b):
    if a is not None and b is not None and max(a, b) != 0:
        return round(abs(a - b) / max(a, b) * 100, 1)
    return None


def _lsi(lese, sain):
    if lese is not None and sain and sain != 0:
        return round(lese / sain * 100, 1)
    return None


def _color(deficit):
    if deficit is None:
        return "grey"
    if deficit < 10:
        return "green"
    if deficit <= 15:
        return "orange"
    return "red"


def parse_vald_slj(pdf_source):
    """HISTORIQUE — PDF SLJ à 1 session (ancien format). Préférer parse_slj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p]
    header = _parse_header(pages[0] if pages else [])
    page2 = pages[1] if len(pages) > 1 else []
    slj_g = _extract_side_average(page2, "Jump Height (Imp-Mom) (Left) [cm]", "LEFT")
    slj_d = _extract_side_average(page2, "Jump Height (Imp-Mom) (Left) [cm]", "RIGHT")
    page3 = pages[2] if len(pages) > 2 else []
    rsi_g = _extract_side_average(page3, "RSI-modified (Imp-Mom) (Left) [m/s]", "LEFT")
    rsi_d = _extract_side_average(page3, "RSI-modified (Imp-Mom) (Left) [m/s]", "RIGHT")
    if slj_g is None:
        slj_g = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "LEFT")
    if slj_d is None:
        slj_d = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "RIGHT")
    if rsi_g is None:
        rsi_g = _extract_side_average(all_lines, "RSI-modified (Imp-Mom) (Left) [m/s]", "LEFT")
    if rsi_d is None:
        rsi_d = _extract_side_average(all_lines, "RSI-modified (Imp-Mom) (Left) [m/s]", "RIGHT")
    dh = _deficit(slj_g, slj_d)
    dr = _deficit(rsi_g, rsi_d)
    return {
        "slj_hauteur_g": slj_g, "slj_hauteur_d": slj_d,
        "rsi_g": rsi_g, "rsi_d": rsi_d,
        "date": header["date"], "bw_kg": header["bw_kg"], "reps": header["reps"],
        "deficit_hauteur": dh, "deficit_rsi": dr,
        "lsi_hauteur": _lsi(slj_g, slj_d), "lsi_rsi": _lsi(rsi_g, rsi_d),
        "color_hauteur": _color(dh), "color_rsi": _color(dr),
    }


def parse_vald_cmj(pdf_source):
    """HISTORIQUE — PDF CMJ à 1 session (ancien format). Préférer parse_cmj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p]
    header = _parse_header(pages[0] if pages else [])
    page2 = pages[1] if len(pages) > 1 else []
    hauteur = _extract_bilateral_average(page2, "Jump Height (Imp-Mom) [cm]")
    if hauteur is None:
        hauteur = _extract_bilateral_average(all_lines, "Jump Height (Imp-Mom) [cm]")
    rsi = _extract_bilateral_average(all_lines, "RSI-modified")
    return {
        "cmj_hauteur": hauteur, "cmj_rsi": rsi,
        "date": header["date"], "bw_kg": header["bw_kg"], "reps": header["reps"],
    }


def parse_vald_pdf(pdf_source):
    """HISTORIQUE — PDF VALD unifié à 1 session. Préférer parse_slj_pdf()/parse_cmj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p]
    header = _parse_header(pages[0] if pages else [])
    slj_g = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "LEFT")
    slj_d = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "RIGHT")
    rsi_g = _extract_side_average(all_lines, "RSI-modified (Imp-Mom) (Left) [m/s]", "LEFT")
    rsi_d = _extract_side_average(all_lines, "RSI-modified (Imp-Mom) (Left) [m/s]", "RIGHT")
    cmj_hauteur = _extract_bilateral_average(all_lines, "Jump Height (Imp-Mom) [cm]")
    cmj_rsi = _extract_bilateral_average(all_lines, "RSI-modified (Imp-Mom) [m/s]")
    return {
        "slj_hauteur_g": slj_g, "slj_hauteur_d": slj_d,
        "rsi_g": rsi_g, "rsi_d": rsi_d,
        "cmj_hauteur": cmj_hauteur, "cmj_rsi": cmj_rsi,
        "date": header["date"], "bw_kg": header["bw_kg"], "reps": header["reps"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 3:
        print("Usage: python vald_parser.py [slj|cmj|slj-old|cmj-old|vald] fichier.pdf")
        sys.exit(1)

    mode = sys.argv[1].lower()
    path = sys.argv[2]

    if mode == "slj":
        result = parse_slj_pdf(path)
    elif mode == "cmj":
        result = parse_cmj_pdf(path)
    elif mode == "slj-old":
        result = parse_vald_slj(path)
    elif mode == "cmj-old":
        result = parse_vald_cmj(path)
    elif mode == "vald":
        result = parse_vald_pdf(path)
    else:
        print(f"Mode inconnu : {mode} (utiliser slj, cmj, slj-old, cmj-old, vald)")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
