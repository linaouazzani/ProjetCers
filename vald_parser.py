"""
vald_parser.py — Parser PDFs VALD ForceDecks
Version 4 — gère 1 session (reps multiples) ET 2 sessions (entrée+sortie)

Logique de détection :
  - 1 date unique  → session unique → on extrait les moyennes (Average) des tables stats
  - 2 dates uniques → 2 sessions   → on extrait les 2 valeurs d'annotation du graphe

Structure PDF 1 session (ex. Noe) :
  Chaque page : "LEFT SIDERange18.7 - 19.1Average18.9CoV0.7%SD0.1RIGHT SIDERange..."
  → résultat : clés _ent remplies, clés _sort = None

Structure PDF 2 sessions (ex. Adam) :
  Chaque page : "Jump Height (Imp-Mom) [cm]  9.7 L\n13.7 L"
  → 1re valeur = date ancienne = ENTRÉE, 2e = date récente = SORTIE
"""

import re
import pdfplumber
from datetime import datetime


# ────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────

def _safe_float(s):
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, AttributeError, TypeError):
        return None


def _count_unique_dates(text):
    """Nombre de dates JJ/MM/AAAA distinctes et valides dans le texte."""
    seen = set()
    for d in re.findall(r'\d{2}/\d{2}/\d{4}', text):
        try:
            datetime.strptime(d, "%d/%m/%Y")
            seen.add(d)
        except ValueError:
            pass
    return len(seen)


def _is_single_session(page1_text: str):
    """Détecte le nombre de sessions via '1 Test' / '2 Tests' dans le texte page 1.

    Retourne :
        True  → 1 session (entrée uniquement)
        False → 2 sessions (entrée + sortie)
        None  → indéterminé (fallback sur comptage de dates)
    """
    if re.search(r'\b1\s+Test\b', page1_text, re.IGNORECASE):
        return True
    if re.search(r'\b2\s+Tests?\b', page1_text, re.IGNORECASE):
        return False
    return None


def _extract_dates(text):
    """Retourne (date_entree, date_sortie) = (plus ancienne, plus récente).
    Si 1 seule date → (date, None) = session unique."""
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
        return objs[0].strftime("%d/%m/%Y"), None   # session unique
    return None, None


def _extract_stat_avg_side(text, side):
    """Extrait la moyenne depuis une table 'SIDE SIDERange X - Y Average Z CoV...'.

    Gère les 2 variantes :
      - sans espaces : "LEFT SIDERange18.7 - 19.1Average18.9CoV..."
      - avec espaces : "LEFT SIDE Range 18.7 - 19.1 Average 18.9 CoV..."
    """
    pattern = rf'{side}\s+SIDE\s*Range\s*-?[\d.]+\s*-\s*-?[\d.]+\s*Average\s*(-?[\d.]+)'
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))
    return None


def _extract_all_avgs_with_side(text):
    """Retourne la liste [(valeur, side)] de tous les blocs 'Average X [L/R] CoV...'
    dans le texte. side = '' si bilatéral, 'L' ou 'R' si asymétrie."""
    results = []
    for m in re.finditer(
        r'Average\s*(-?[\d.]+)\s*([LR]?)\s*CoV',
        text, re.IGNORECASE
    ):
        val = _safe_float(m.group(1))
        side = m.group(2).upper() if m.group(2) else ""
        if val is not None:
            results.append((val, side))
    return results


# ────────────────────────────────────────────────────────────────
# SLJ — parse_slj_pdf
# ────────────────────────────────────────────────────────────────

def parse_slj_pdf(pdf_source):
    """Parse un PDF SLJ VALD Hub (1 ou 2 sessions).

    Retourne dict :
      slj_hauteur_g_ent/sort  : Jump Height Left  entrée/sortie (cm)
      slj_hauteur_d_ent/sort  : Jump Height Right entrée/sortie (cm)
      rsi_g_ent/sort          : RSI-modified Left  entrée/sortie (m/s)
      rsi_d_ent/sort          : RSI-modified Right entrée/sortie (m/s)
      slj_flight_g_ent/sort   : Flight Time Left  entrée/sortie (cm)
      slj_flight_d_ent/sort   : Flight Time Right entrée/sortie (cm)
      peak_force_asym_ent/sort: Asymmetry % entrée/sortie
      date_entree / date_sortie
    Les clés _sort sont None pour un PDF 1 session.
    """
    result = {
        "slj_hauteur_g_ent":    None, "slj_hauteur_g_sort":   None,
        "slj_hauteur_d_ent":    None, "slj_hauteur_d_sort":   None,
        "rsi_g_ent":            None, "rsi_g_sort":           None,
        "rsi_d_ent":            None, "rsi_d_sort":           None,
        "slj_flight_g_ent":     None, "slj_flight_g_sort":    None,
        "slj_flight_d_ent":     None, "slj_flight_d_sort":    None,
        "peak_force_asym_ent":  None, "peak_force_asym_sort": None,
        "date_entree":          None, "date_sortie":          None,
    }

    with pdfplumber.open(pdf_source) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    full_text = "\n".join(pages)

    result["date_entree"], result["date_sortie"] = _extract_dates(full_text)

    # Détection via "1 Test" / "2 Tests" en page 1 ; fallback sur comptage dates
    _single = _is_single_session(pages[0] if pages else "")
    if _single is None:
        _single = _count_unique_dates(full_text) <= 1

    if _single:
        _parse_slj_single(pages, result)
    else:
        _parse_slj_multi(full_text, result)

    return result


def _parse_slj_single(pages, result):
    """1 session SLJ : extrait les moyennes LEFT/RIGHT SIDE par page."""
    for page_text in pages:
        pt = page_text.upper()

        # Jump Height (Imp-Mom) — page contient LEFT et RIGHT SIDE, pas Flight Time
        if "JUMP HEIGHT (IMP-MOM)" in pt and "FLIGHT TIME" not in pt:
            g = _extract_stat_avg_side(page_text, "LEFT")
            d = _extract_stat_avg_side(page_text, "RIGHT")
            if g is not None and result["slj_hauteur_g_ent"] is None:
                result["slj_hauteur_g_ent"] = g
            if d is not None and result["slj_hauteur_d_ent"] is None:
                result["slj_hauteur_d_ent"] = d

        # RSI-modified
        if "RSI-MODIF" in pt:
            g = _extract_stat_avg_side(page_text, "LEFT")
            d = _extract_stat_avg_side(page_text, "RIGHT")
            if g is not None and result["rsi_g_ent"] is None:
                result["rsi_g_ent"] = g
            if d is not None and result["rsi_d_ent"] is None:
                result["rsi_d_ent"] = d

        # Flight Time
        if "FLIGHT TIME" in pt:
            g = _extract_stat_avg_side(page_text, "LEFT")
            d = _extract_stat_avg_side(page_text, "RIGHT")
            if g is not None and result["slj_flight_g_ent"] is None:
                result["slj_flight_g_ent"] = g
            if d is not None and result["slj_flight_d_ent"] is None:
                result["slj_flight_d_ent"] = d


def _parse_slj_multi(full_text, result):
    """2 sessions SLJ : extrait les 2 valeurs d'annotation du graphe."""

    # Jump Height Left : "9.7 L\n13.7 L" ou "9.7 L  13.7 L"
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s+([\d.]+)\s*L[\s\n]+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["slj_hauteur_g_ent"]  = _safe_float(m.group(1))
        result["slj_hauteur_g_sort"] = _safe_float(m.group(2))

    # Jump Height Right
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s+([\d.]+)\s*R[\s\n]+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["slj_hauteur_d_ent"]  = _safe_float(m.group(1))
        result["slj_hauteur_d_sort"] = _safe_float(m.group(2))

    # RSI Left
    m = re.search(
        r'RSI-modifi(?:ed|é) \(Imp-Mom\) \[m/s\]\s*([\d.]+)\s*L[\s\n]+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["rsi_g_ent"]  = _safe_float(m.group(1))
        result["rsi_g_sort"] = _safe_float(m.group(2))

    # RSI Right
    m = re.search(
        r'RSI-modifi(?:ed|é) \(Imp-Mom\) \[m/s\]\s*([\d.]+)\s*R[\s\n]+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["rsi_d_ent"]  = _safe_float(m.group(1))
        result["rsi_d_sort"] = _safe_float(m.group(2))

    # Flight Time Left
    m = re.search(
        r'Jump Height \(Flight Time\) \[cm\]\s*([\d.]+)\s*L[\s\n]+([\d.]+)\s*L',
        full_text
    )
    if m:
        result["slj_flight_g_ent"]  = _safe_float(m.group(1))
        result["slj_flight_g_sort"] = _safe_float(m.group(2))

    # Flight Time Right
    m = re.search(
        r'Jump Height \(Flight Time\) \[cm\]\s*([\d.]+)\s*R[\s\n]+([\d.]+)\s*R',
        full_text
    )
    if m:
        result["slj_flight_d_ent"]  = _safe_float(m.group(1))
        result["slj_flight_d_sort"] = _safe_float(m.group(2))

    # Asymmetry (toujours positif en SLJ)
    m = re.search(r'Asymmetry \[%\]\s*([\d.]+)\s+([\d.]+)', full_text)
    if m:
        result["peak_force_asym_ent"]  = _safe_float(m.group(1))
        result["peak_force_asym_sort"] = _safe_float(m.group(2))


# ────────────────────────────────────────────────────────────────
# CMJ — parse_cmj_pdf
# ────────────────────────────────────────────────────────────────

def parse_cmj_pdf(pdf_source):
    """Parse un PDF CMJ VALD Hub (1 ou 2 sessions).

    Retourne dict :
      cmj_hauteur_ent/sort          : Jump Height bilatéral (cm)
      cmj_rfd_ent/sort              : Concentric RFD (N/s)
      cmj_conc_asym_ent/sort        : Concentric Peak Force Asymmetry signé (% ; + = D, − = G)
      cmj_conc_asym_side_ent/sort   : côté dominant ('L' ou 'R')
      cmj_landing_asym_ent/sort     : Peak Landing Force Asymmetry signé (% ; + = D, − = G)
      cmj_landing_side_ent/sort     : côté dominant ('L'/'R' ou 'G'/'D')
      cmj_ecc_vel_ent/sort          : Eccentric Peak Velocity (m/s, négatif)
      date_entree / date_sortie
    """
    result = {
        "cmj_hauteur_ent":          None, "cmj_hauteur_sort":         None,
        "cmj_rfd_ent":              None, "cmj_rfd_sort":             None,
        "cmj_conc_asym_ent":        None, "cmj_conc_asym_sort":       None,
        "cmj_conc_asym_side_ent":   None, "cmj_conc_asym_side_sort":  None,
        "cmj_landing_asym_ent":     None, "cmj_landing_asym_sort":    None,
        "cmj_landing_side_ent":     None, "cmj_landing_side_sort":    None,
        "cmj_ecc_vel_ent":          None, "cmj_ecc_vel_sort":         None,
        "date_entree":              None, "date_sortie":              None,
    }

    with pdfplumber.open(pdf_source) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    full_text = "\n".join(pages)

    result["date_entree"], result["date_sortie"] = _extract_dates(full_text)

    # Détection via "1 Test" / "2 Tests" en page 1 ; fallback sur comptage dates
    _single = _is_single_session(pages[0] if pages else "")
    if _single is None:
        _single = _count_unique_dates(full_text) <= 1

    if _single:
        _parse_cmj_single(pages, result)
    else:
        _parse_cmj_multi(full_text, result)

    return result


def _parse_cmj_single(pages, result):
    """1 session CMJ : extrait les moyennes depuis les tables stats par page."""
    for page_text in pages:
        pt = page_text.upper()
        avgs = _extract_all_avgs_with_side(page_text)

        # ── Page : Jump Height (Imp-Mom) + Concentric Peak Force Asymmetry ──
        if "JUMP HEIGHT (IMP-MOM)" in pt:
            for val, side in avgs:
                if side:  # L ou R → asymétrie concentrique
                    if result["cmj_conc_asym_ent"] is None:
                        result["cmj_conc_asym_ent"] = val if side == "R" else -val
                        result["cmj_conc_asym_side_ent"] = side
                else:     # bilatéral → hauteur de saut
                    if result["cmj_hauteur_ent"] is None:
                        result["cmj_hauteur_ent"] = val

        # ── Page : Eccentric Peak Velocity + Peak Landing Force Asymmetry ──
        if "ECCENTRIC PEAK VELOCITY" in pt:
            for val, side in avgs:
                if side:  # L ou R → landing asymmetry
                    if result["cmj_landing_asym_ent"] is None:
                        result["cmj_landing_asym_ent"] = val if side == "R" else -val
                        result["cmj_landing_side_ent"] = side
                else:     # bilatéral → vitesse excentrique (négatif)
                    if result["cmj_ecc_vel_ent"] is None:
                        result["cmj_ecc_vel_ent"] = val

        # ── Page : Concentric RFD ──
        if "CONCENTRIC RFD" in pt:
            for val, side in avgs:
                if not side and result["cmj_rfd_ent"] is None:
                    result["cmj_rfd_ent"] = val
                    break


def _parse_cmj_multi(full_text, result):
    """2 sessions CMJ : extrait les 2 valeurs d'annotation du graphe."""

    # Jump Height : "24.8 cm\n29.1 cm" — suffixe "cm" distingue de SLJ (L/R)
    m = re.search(
        r'Jump Height \(Imp-Mom\) \[cm\]\s*([\d.]+)\s*cm[\s\n]+([\d.]+)\s*cm',
        full_text
    )
    if m:
        result["cmj_hauteur_ent"]  = _safe_float(m.group(1))
        result["cmj_hauteur_sort"] = _safe_float(m.group(2))

    # Concentric RFD : "1000 N/s\n3419 N/s"
    m = re.search(
        r'Concentric RFD \[N/s\]\s*([\d.]+)\s*N/s[\s\n]+([\d.]+)\s*N/s',
        full_text
    )
    if m:
        result["cmj_rfd_ent"]  = _safe_float(m.group(1))
        result["cmj_rfd_sort"] = _safe_float(m.group(2))

    # Landing Asymmetry : "55\n-17" (positif = D, négatif = G)
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
        r'Eccentric Peak Velocity \[m/s\]\s*(-?[\d.]+)\s*m/s[\s\n]+(-?[\d.]+)\s*m/s',
        full_text
    )
    if m:
        result["cmj_ecc_vel_ent"]  = _safe_float(m.group(1))
        result["cmj_ecc_vel_sort"] = _safe_float(m.group(2))


# ────────────────────────────────────────────────────────────────
# FONCTIONS HISTORIQUES (rétrocompatibilité)
# ────────────────────────────────────────────────────────────────

def _get_pages(pdf_source):
    with pdfplumber.open(pdf_source) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


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
    if deficit is None: return "grey"
    if deficit < 10:    return "green"
    if deficit <= 15:   return "orange"
    return "red"


def parse_vald_slj(pdf_source):
    """HISTORIQUE — PDF SLJ à 1 session (ancien format). Préférer parse_slj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p.split("\n")]
    header = _parse_header(pages[0].split("\n") if pages else [])
    slj_g = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "LEFT")
    slj_d = _extract_side_average(all_lines, "Jump Height (Imp-Mom) (Left) [cm]", "RIGHT")
    rsi_g = _extract_side_average(all_lines, "RSI-modified (Imp-Mom) (Left) [m/s]", "LEFT")
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
    """HISTORIQUE — PDF CMJ à 1 session. Préférer parse_cmj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p.split("\n")]
    header = _parse_header(pages[0].split("\n") if pages else [])
    hauteur = _extract_bilateral_average(all_lines, "Jump Height (Imp-Mom) [cm]")
    rsi = _extract_bilateral_average(all_lines, "RSI-modified")
    return {
        "cmj_hauteur": hauteur, "cmj_rsi": rsi,
        "date": header["date"], "bw_kg": header["bw_kg"], "reps": header["reps"],
    }


def parse_vald_pdf(pdf_source):
    """HISTORIQUE — PDF VALD unifié à 1 session. Préférer parse_slj_pdf()/parse_cmj_pdf()."""
    pages = _get_pages(pdf_source)
    all_lines = [l for p in pages for l in p.split("\n")]
    header = _parse_header(pages[0].split("\n") if pages else [])
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


# ────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────
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
        print(f"Mode inconnu : {mode}")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
