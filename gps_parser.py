"""
gps_parser.py — Parser PDF Catapult OpenField (CERS Capbreton)

Format détecté (Bilan GPS.pdf) :
  Chaque session = 3 lignes consécutives :
    1. Date          : "DD/MM/YYYY"
    2. Activity ID   : "Activity YYYYMMDDHHMMSS"  (ignorée)
    3. Données       : "Athlete G2 <17 valeurs>"

Colonnes (ordre dans la ligne de données) :
  0  Tot Dist (m)
  1  Tot Dur (HH:MM:SS)
  2  Max Vel (km/h)
  3  Vel 18-21 km/h — Tot Dist (m)
  4  Vel 21-24 km/h — Tot Dist (m)
  5  Vel >24 km/h   — Tot Dist (m)
  6  Métrage/minute (m/min)
  7  Acc 2-3 m/s²  — Effs
  8  Acc 2-3 m/s²  — Dist (m)
  9  Acc 3-4 m/s²  — Effs
  10 Acc 3-4 m/s²  — Dist (m)
  11 Acc >4 m/s²   — Effs
  12 Acc >4 m/s²   — Dist (m)
  13 Max Acc (m/s²)
  14 Décel B1 — Effs
  15 Décel B2 — Effs
  16 Décel B3 — Effs

Usage CLI :
  python gps_parser.py "C:\\chemin\\Bilan GPS.pdf"
  python gps_parser.py "C:\\chemin\\Bilan GPS.pdf" --json
"""

import re
import json
import sys
from datetime import datetime

import pdfplumber


# ── helpers ──────────────────────────────────────────────────────────────────

def _f(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ".").replace(" ", "").strip())
    except (ValueError, AttributeError):
        return None


def _i(s):
    v = _f(s)
    return int(round(v)) if v is not None else None


DATE_RE  = re.compile(r'^\d{2}/\d{2}/\d{4}$')
ACT_RE   = re.compile(r'^Activity\s+\d+', re.IGNORECASE)
DATA_RE  = re.compile(r'^[A-Za-z]')   # ligne données commence par texte (nom athlète)
DUR_RE   = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$')
NUM_RE   = re.compile(r'^-?\d+(?:[.,]\d+)?$')


def _parse_data_line(line: str):
    """
    Parse une ligne données ex. 'Athlete G2 1515 00:10:44 17.2 0 0 0 58.60 ...'
    Saute les tokens non-numériques de début (nom + device) puis extrait 17 valeurs.
    """
    tokens = line.split()
    # Sauter tokens alphabétiques du début (nom athlète, "G2", etc.)
    idx = 0
    while idx < len(tokens) and not (NUM_RE.match(tokens[idx]) or DUR_RE.match(tokens[idx])):
        idx += 1

    vals = []
    for t in tokens[idx:]:
        if DUR_RE.match(t):
            vals.append(t)
        elif NUM_RE.match(t):
            vals.append(_f(t))
        else:
            vals.append(None)

    def v(pos):
        return vals[pos] if pos < len(vals) else None

    return {
        "distance_m":   _i(v(0)),
        "duree":         v(1),          # string HH:MM:SS
        "vmax_kmh":     _f(v(2)),
        "d_18_21":      _i(v(3)),
        "d_21_24":      _i(v(4)),
        "d_sup24":      _i(v(5)),
        "metrage_min":  _f(v(6)),
        "acc_b1_effs":  _i(v(7)),
        "acc_b1_dist":  _f(v(8)),
        "acc_b2_effs":  _i(v(9)),
        "acc_b2_dist":  _f(v(10)),
        "acc_b3_effs":  _i(v(11)),
        "acc_b3_dist":  _f(v(12)),
        "max_acc":      _f(v(13)),
        "decel_b1":     _i(v(14)),
        "decel_b2":     _i(v(15)),
        "decel_b3":     _i(v(16)),
    }


# ── semaine ───────────────────────────────────────────────────────────────────

def _to_dt(date_str):
    try:
        d, m, y = date_str.split("/")
        return datetime(int(y), int(m), int(d))
    except Exception:
        return None


def _week_label(date_str):
    dt = _to_dt(date_str)
    if not dt:
        return "Inconnue"
    return f"Semaine {dt.strftime('%Y-W%V')}  ({dt.strftime('%d/%m')}–"


def _week_key(date_str):
    dt = _to_dt(date_str)
    if not dt:
        return "9999-W99"
    return dt.strftime('%Y-W%V')


# ── parser principal ──────────────────────────────────────────────────────────

def parse_gps_pdf(pdf_source):
    """
    Retourne :
      sessions    : liste ordonnée de dicts (une entrée par session)
      semaines    : dict {clé_semaine: résumé agrégé}
      progression : dict {indicateur: % variation 1re→dernière semaine}
      meta        : {athlete, n_sessions, n_semaines, periode}
    """
    # ── 1. Extraction texte ───────────────────────────────────────────────
    all_lines = []
    athlete_name = "Alan"
    with pdfplumber.open(pdf_source) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Récupère nom athlète depuis "BILAN <NOM>"
            m = re.search(r'BILAN\s+([A-ZÉÈÊÀÙÛÜ][A-ZÉÈÊÀÙÛÜa-zéèêàùûü\s]+)', text)
            if m:
                athlete_name = m.group(1).strip().title()
            all_lines.extend(text.split('\n'))

    # ── 2. Extraction sessions ────────────────────────────────────────────
    sessions = []
    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()

        if DATE_RE.match(line):
            date_str = line
            # Cherche la ligne de données (saute Activity ID et lignes vides)
            j = i + 1
            data_line = None
            while j < len(all_lines) and j < i + 4:
                l = all_lines[j].strip()
                if l and not ACT_RE.match(l) and DATA_RE.match(l):
                    # Doit contenir une durée HH:MM:SS ou MM:SS pour être une vraie ligne de données
                    # (filtre les lignes d'en-tête qui contiennent des chiffres comme "18", "21", etc.)
                    if re.search(r'\b\d{1,2}:\d{2}(:\d{2})?\b', l):
                        data_line = l
                        break
                j += 1

            if data_line:
                row = _parse_data_line(data_line)
                row["date"] = date_str
                # Évite doublons
                if not any(s["date"] == date_str for s in sessions):
                    sessions.append(row)
                i = j + 1
                continue
        i += 1

    # ── 3. Tri chronologique ──────────────────────────────────────────────
    sessions.sort(key=lambda s: _to_dt(s["date"]) or datetime.min)

    # ── 4. Agrégation par semaine ─────────────────────────────────────────
    NUM_COLS = ["distance_m", "vmax_kmh", "d_18_21", "d_21_24", "d_sup24",
                "metrage_min", "acc_b1_effs", "acc_b1_dist",
                "acc_b2_effs", "acc_b2_dist", "acc_b3_effs", "acc_b3_dist",
                "max_acc", "decel_b1", "decel_b2", "decel_b3"]

    raw_weeks = {}   # clé_semaine → {col → [vals]}
    for s in sessions:
        wk = _week_key(s["date"])
        if wk not in raw_weeks:
            raw_weeks[wk] = {"dates": []}
            for c in NUM_COLS:
                raw_weeks[wk][c] = []
        raw_weeks[wk]["dates"].append(s["date"])
        for c in NUM_COLS:
            if s.get(c) is not None:
                raw_weeks[wk][c].append(s[c])

    def _sum(lst):
        return round(sum(lst), 1) if lst else None
    def _max(lst):
        return round(max(lst), 1) if lst else None
    def _avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    semaines = {}
    for wk in sorted(raw_weeks.keys()):
        d = raw_weeks[wk]
        dates = sorted(d["dates"], key=lambda x: _to_dt(x) or datetime.min)
        d18 = _sum(d["d_18_21"])
        d21 = _sum(d["d_21_24"])
        d24 = _sum(d["d_sup24"])
        semaines[wk] = {
            "label":       f"Semaine {wk.split('-W')[1]}  ({dates[0]} → {dates[-1]})",
            "n_sessions":  len(dates),
            "dates":       dates,
            # Volume
            "distance_m":  _sum(d["distance_m"]),
            "vmax_kmh":    _max(d["vmax_kmh"]),
            # Haute intensité
            "d_18_21":     d18,
            "d_21_24":     d21,
            "d_sup24":     d24,
            "d_hsr":       round((d18 or 0) + (d21 or 0) + (d24 or 0), 1) or None,
            # Intensité relative
            "metrage_min": _avg(d["metrage_min"]),
            # Accélérations
            "acc_b1_effs": _sum(d["acc_b1_effs"]),
            "acc_b1_dist": _sum(d["acc_b1_dist"]),
            "acc_b2_effs": _sum(d["acc_b2_effs"]),
            "acc_b2_dist": _sum(d["acc_b2_dist"]),
            "acc_b3_effs": _sum(d["acc_b3_effs"]),
            "acc_b3_dist": _sum(d["acc_b3_dist"]),
            "max_acc":     _max(d["max_acc"]),
            # Décélérations
            "decel_b1":    _sum(d["decel_b1"]),
            "decel_b2":    _sum(d["decel_b2"]),
            "decel_b3":    _sum(d["decel_b3"]),
        }

    # ── 5. Progression globale ────────────────────────────────────────────
    wk_keys = list(semaines.keys())
    progression = {}
    if len(wk_keys) >= 2:
        first = semaines[wk_keys[0]]
        last  = semaines[wk_keys[-1]]
        for col in ["distance_m", "vmax_kmh", "d_hsr", "d_18_21", "d_21_24",
                    "d_sup24", "metrage_min", "acc_b1_effs", "acc_b2_effs",
                    "acc_b3_effs", "max_acc", "decel_b1", "decel_b2", "decel_b3"]:
            v0, v1 = first.get(col), last.get(col)
            if v0 is not None and v1 is not None and v0 != 0:
                progression[col] = round((v1 - v0) / abs(v0) * 100, 1)

    meta = {
        "athlete":    athlete_name,
        "n_sessions": len(sessions),
        "n_semaines": len(semaines),
        "periode":    f"{sessions[0]['date']} → {sessions[-1]['date']}" if sessions else "—",
    }

    return {
        "sessions":    sessions,
        "semaines":    semaines,
        "progression": progression,
        "meta":        meta,
    }


# ── analyse textuelle ─────────────────────────────────────────────────────────

def analyser_progression(result):
    semaines = result["semaines"]
    prog     = result["progression"]
    meta     = result["meta"]

    SEP = "═" * 72
    sep = "─" * 72

    lines = [
        SEP,
        f"  RAPPORT GPS CATAPULT OPENFIELD — {meta['athlete'].upper()}",
        f"  Période : {meta['periode']}  |  {meta['n_sessions']} sessions  |  {meta['n_semaines']} semaines",
        SEP,
    ]

    for wk_key, s in semaines.items():
        lines.append(f"\n{sep}")
        lines.append(f"  {s['label']}  —  {s['n_sessions']} session(s)")
        lines.append(sep)
        lines.append(f"  {'Indicateur':<35} {'Valeur':>12}")
        lines.append(f"  {'─'*33} {'─'*12}")

        def row(label, val, unit=""):
            v = f"{val:,}".replace(",", " ") if isinstance(val, int) else (f"{val:.1f}" if isinstance(val, float) else "—")
            return f"  {label:<35} {v + ' ' + unit if val is not None else '—':>14}"

        lines.append(row("Distance totale",          s["distance_m"],  "m"))
        lines.append(row("Vitesse maximale",          s["vmax_kmh"],    "km/h"))
        lines.append(row("Métrage / minute",          s["metrage_min"], "m/min"))
        lines.append(row("Distance HSR totale (>18)", s["d_hsr"],       "m"))
        lines.append(row("  › 18–21 km/h",            s["d_18_21"],     "m"))
        lines.append(row("  › 21–24 km/h",            s["d_21_24"],     "m"))
        lines.append(row("  › >24 km/h",              s["d_sup24"],     "m"))
        lines.append(row("Acc B1 (2–3 m/s²) efforts", s["acc_b1_effs"], "effs"))
        lines.append(row("Acc B1 (2–3 m/s²) dist",   s["acc_b1_dist"], "m"))
        lines.append(row("Acc B2 (3–4 m/s²) efforts", s["acc_b2_effs"], "effs"))
        lines.append(row("Acc B2 (3–4 m/s²) dist",   s["acc_b2_dist"], "m"))
        lines.append(row("Acc B3 (>4 m/s²) efforts", s["acc_b3_effs"], "effs"))
        lines.append(row("Acc B3 (>4 m/s²) dist",    s["acc_b3_dist"], "m"))
        lines.append(row("Accélération maximale",     s["max_acc"],     "m/s²"))
        lines.append(row("Décélérations B1",          s["decel_b1"],    "effs"))
        lines.append(row("Décélérations B2",          s["decel_b2"],    "effs"))
        lines.append(row("Décélérations B3",          s["decel_b3"],    "effs"))

    # Tendances
    lines.append(f"\n{SEP}")
    lines.append("  TENDANCES GLOBALES — 1re semaine → dernière semaine")
    lines.append(SEP)
    labels = {
        "distance_m":    "Distance totale",
        "vmax_kmh":      "Vitesse maximale",
        "d_hsr":         "Distance HSR (>18 km/h)",
        "d_18_21":       "Distance 18–21 km/h",
        "d_21_24":       "Distance 21–24 km/h",
        "d_sup24":       "Distance >24 km/h",
        "metrage_min":   "Métrage/minute",
        "acc_b1_effs":   "Acc B1 efforts",
        "acc_b2_effs":   "Acc B2 efforts",
        "acc_b3_effs":   "Acc B3 efforts",
        "max_acc":       "Accélération max",
        "decel_b1":      "Décélérations B1",
        "decel_b2":      "Décélérations B2",
        "decel_b3":      "Décélérations B3",
    }
    for k, label in labels.items():
        if k in prog:
            p = prog[k]
            arrow = "↑ PROGRESSION" if p > 0 else ("↓ RÉGRESSION " if p < 0 else "→ STABLE    ")
            lines.append(f"  {arrow}  {label:<30}  {p:+.1f}%")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gps_parser.py fichier.pdf [--json]")
        sys.exit(1)

    path = sys.argv[1]
    as_json = "--json" in sys.argv

    result = parse_gps_pdf(path)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        # Tableau brut sessions
        print("\nSESSIONS BRUTES EXTRAITES :")
        header = ["date","distance_m","duree","vmax_kmh","d_18_21","d_21_24","d_sup24",
                  "metrage_min","acc_b1_effs","acc_b1_dist","acc_b2_effs","acc_b2_dist",
                  "acc_b3_effs","acc_b3_dist","max_acc","decel_b1","decel_b2","decel_b3"]
        print("  " + " | ".join(f"{h:>12}" for h in header))
        for s in result["sessions"]:
            vals = [str(s.get(h, "—") or "—") for h in header]
            print("  " + " | ".join(f"{v:>12}" for v in vals))

        print("\n")
        print(analyser_progression(result))
