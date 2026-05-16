"""
vald_parser.py — Parser PDFs VALD ForceDecks (exportés Firefox HTML→PDF)
Projet CERS Capbreton — version 2 (structure réelle confirmée)

Structure réelle observée ligne par ligne :

  PAGE 1 (SLJ et CMJ) :
    'PROFILE DATE TAGS REPS BW [KG]'
    'Noe Della schiava 30/03/2026'
    '0 6 101.2'          <- TAGS=0, REPS=6, BW=101.2
    '1 Test 1:19 PM'

  PAGE 2 SLJ :
    'Jump Height (Imp-Mom) (Left) [cm]'
    'LEFT SIDE'
    'Range Average CoV SD'
    '18.7 - 19.1 18.9 0.7% 0.1'   <- average = 18.9
    ...
    'RIGHT SIDE'
    'Range Average CoV SD'
    '21.5 - 23 22.3 2.8% 0.6'     <- average = 22.3

  PAGE 3 SLJ :
    'RSI-modified (Imp-Mom) (Left) [m/s]'
    'LEFT SIDE'
    'Range Average CoV SD'
    '0.24 - 0.25 0.24 2.7% 0.01'  <- average = 0.24
    ...
    'RIGHT SIDE'
    'Range Average CoV SD'
    '0.29 - 0.3 0.29 2.3% 0.01'   <- average = 0.29

  PAGE 2 CMJ :
    'Jump Height (Imp-Mom) [cm]'
    'Range Average CoV SD'
    '43.9 - 46.1 44.9 2.0% 0.9'   <- average = 44.9

  Note : RSI CMJ absent de l'export actuel (3 pages).
"""

import re
import pdfplumber


# ---------------------------------------------------------------------------
# Helpers bas niveau
# ---------------------------------------------------------------------------

def _get_pages(pdf_source):
    """Retourne liste de pages, chaque page = liste de lignes.
    pdf_source : chemin str ou objet file-like (BytesIO)."""
    with pdfplumber.open(pdf_source) as pdf:
        result = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            result.append(text.split("\n"))
        return result


def _safe_float(s):
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, AttributeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Ligne de donnees : "18.7 - 19.1 18.9 0.7% 0.1"
# groups : (min, max, average, cov, sd)
# ---------------------------------------------------------------------------
DATA_LINE_RE = re.compile(
    r"^([\d.]+)\s*-\s*([\d.]+)\s+([\d.]+)\s+([\d.]+%)\s+([\d.]+)$"
)


def _extract_side_average(lines, section_title, side):
    """
    Cherche section_title dans les lignes, puis le bloc 'side SIDE',
    retourne Average de la ligne de donnees.
    side : "LEFT" ou "RIGHT"
    """
    in_section = False
    in_side = False
    after_header = False

    for line in lines:
        ls = line.strip()

        if section_title.lower() in ls.lower():
            in_section = True
            in_side = False
            after_header = False
            continue

        if not in_section:
            continue

        if ls.upper() == (side + " SIDE"):
            in_side = True
            after_header = False
            continue

        if not in_side:
            continue

        if "Range" in ls and "Average" in ls:
            after_header = True
            continue

        if after_header:
            m = DATA_LINE_RE.match(ls)
            if m:
                return _safe_float(m.group(3))  # Average
            if ls.upper().endswith(" SIDE") and ls.upper() != (side + " SIDE"):
                in_side = False
                after_header = False

    return None


def _extract_bilateral_average(lines, section_title):
    """CMJ : pas de LEFT/RIGHT, Average directement apres Range/Average/CoV/SD."""
    in_section = False
    after_header = False

    for line in lines:
        ls = line.strip()

        if section_title.lower() in ls.lower():
            in_section = True
            after_header = False
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


# ---------------------------------------------------------------------------
# Calculs
# ---------------------------------------------------------------------------

def _deficit(a, b):
    """Formule Maxime : |a-b| / max(a,b) * 100"""
    if a is not None and b is not None and max(a, b) != 0:
        return round(abs(a - b) / max(a, b) * 100, 1)
    return None


def _lsi(lese, sain):
    """LSI = lese/sain * 100"""
    if lese is not None and sain and sain != 0:
        return round(lese / sain * 100, 1)
    return None


def _color(deficit):
    """Couleur selon seuils Maxime : vert <10%, orange 10-15%, rouge >15%"""
    if deficit is None:
        return "grey"
    if deficit < 10:
        return "green"
    if deficit <= 15:
        return "orange"
    return "red"


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def parse_vald_slj(pdf_source):
    """
    Parse un PDF SLJ VALD ForceDecks.
    pdf_source : chemin str ou BytesIO.

    Retourne dict :
    {
        "slj_hauteur_g":   float|None,  # Jump Height LEFT avg (cm)
        "slj_hauteur_d":   float|None,  # Jump Height RIGHT avg (cm)
        "rsi_g":           float|None,  # RSI-modified LEFT avg (m/s)
        "rsi_d":           float|None,  # RSI-modified RIGHT avg (m/s)
        "date":            str|None,
        "bw_kg":           float|None,
        "reps":            int|None,
        "deficit_hauteur": float|None,  # |D-G|/max(D,G)*100
        "deficit_rsi":     float|None,
        "lsi_hauteur":     float|None,  # G/D*100
        "lsi_rsi":         float|None,
        "color_hauteur":   str,         # green/orange/red/grey
        "color_rsi":       str,
    }
    """
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p]

    header = _parse_header(pages[0] if pages else [])

    page2 = pages[1] if len(pages) > 1 else []
    slj_g = _extract_side_average(page2, "Jump Height (Imp-Mom) (Left) [cm]", "LEFT")
    slj_d = _extract_side_average(page2, "Jump Height (Imp-Mom) (Left) [cm]", "RIGHT")

    page3 = pages[2] if len(pages) > 2 else []
    rsi_g = _extract_side_average(page3, "RSI-modified (Imp-Mom) (Left) [m/s]", "LEFT")
    rsi_d = _extract_side_average(page3, "RSI-modified (Imp-Mom) (Left) [m/s]", "RIGHT")

    # Fallbacks sur toutes les pages
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
        "slj_hauteur_g":   slj_g,
        "slj_hauteur_d":   slj_d,
        "rsi_g":           rsi_g,
        "rsi_d":           rsi_d,
        "date":            header["date"],
        "bw_kg":           header["bw_kg"],
        "reps":            header["reps"],
        "deficit_hauteur": dh,
        "deficit_rsi":     dr,
        "lsi_hauteur":     _lsi(slj_g, slj_d),
        "lsi_rsi":         _lsi(rsi_g, rsi_d),
        "color_hauteur":   _color(dh),
        "color_rsi":       _color(dr),
    }


def parse_vald_cmj(pdf_source):
    """
    Parse un PDF CMJ VALD ForceDecks.
    pdf_source : chemin str ou BytesIO.

    Retourne dict :
    {
        "cmj_hauteur": float|None,  # Jump Height avg (cm) bilateral
        "cmj_rsi":     float|None,  # RSI-modified avg (m/s) -- absent si page manquante
        "date":        str|None,
        "bw_kg":       float|None,
        "reps":        int|None,
    }
    Note : cmj_rsi = None si la page RSI n'est pas dans l'export.
    Passer la valeur via champ manuel dans app.py.
    """
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p]

    header = _parse_header(pages[0] if pages else [])

    page2 = pages[1] if len(pages) > 1 else []
    hauteur = _extract_bilateral_average(page2, "Jump Height (Imp-Mom) [cm]")
    if hauteur is None:
        hauteur = _extract_bilateral_average(all_lines, "Jump Height (Imp-Mom) [cm]")

    rsi = _extract_bilateral_average(all_lines, "RSI-modified")

    return {
        "cmj_hauteur": hauteur,
        "cmj_rsi":     rsi,
        "date":        header["date"],
        "bw_kg":       header["bw_kg"],
        "reps":        header["reps"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 3:
        print("Usage: python vald_parser.py [slj|cmj] fichier.pdf")
        sys.exit(1)

    mode = sys.argv[1].lower()
    path = sys.argv[2]

    if mode == "slj":
        result = parse_vald_slj(path)
    elif mode == "cmj":
        result = parse_vald_cmj(path)
    else:
        print(f"Mode inconnu : {mode}")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
