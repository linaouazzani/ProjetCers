"""
gps_parser.py — Parser GPS Catapult OpenField v2 (CERS Capbreton)
===================================================================
Stratégie hybride, 3 passes successives :
  1. Lignes de texte (format bilan Catapult) — détection dynamique des colonnes
  2. Tables pdfplumber (exports avec grilles PDF)
  3. Fallback brut regex si les deux passes précédentes échouent

Formats détectés automatiquement :
  Format A — ancien  : dist | durée | vmax | d18-21 | d21-24 | d>24 | m/min | acc×6 | max_acc | decel×3
  Format B — nouveau : dist | vmax  | d15-18 | d18-21 | d21-24 | d>24 | m/min | acc×6 | max_acc | decel_effs+dist×3

CLI :
  python gps_parser.py fichier.pdf [--json]
"""

import re
import json
import sys
from datetime import datetime

import pdfplumber


# ─────────────────────────────────────────────────────────────────────────────
# REGEX
# ─────────────────────────────────────────────────────────────────────────────

DATE_RE  = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
DUR_RE   = re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b')
NUM_RE   = re.compile(r'^-?\d+(?:[.,]\d+)?$')
ACT_RE   = re.compile(r'^Activity\s+\d+', re.IGNORECASE)
NUMS_IN  = re.compile(r'\b(\d+(?:[.,]\d+)?)\b')   # standalone numbers in a line


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS NUMÉRIQUES
# ─────────────────────────────────────────────────────────────────────────────

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


def _to_dt(date_str):
    try:
        d, m, y = date_str.split("/")
        return datetime(int(y), int(m), int(d))
    except Exception:
        return None


def _week_key(date_str):
    dt = _to_dt(date_str)
    if not dt:
        return "9999-W99"
    return dt.strftime('%Y-W%V')


def _empty_session(date_str):
    return {
        'date': date_str, 'session_name': None,
        'distance_m': None, 'duree': None, 'vmax_kmh': None,
        'd_15_18': None, 'd_18_21': None, 'd_21_24': None, 'd_sup24': None,
        'metrage_min': None,
        'acc_b1_effs': None, 'acc_b1_dist': None,
        'acc_b2_effs': None, 'acc_b2_dist': None,
        'acc_b3_effs': None, 'acc_b3_dist': None,
        'max_acc': None,
        'decel_b1': None, 'decel_b2': None, 'decel_b3': None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTION AUTOMATIQUE DU FORMAT
# ─────────────────────────────────────────────────────────────────────────────

def _detect_format(header_text):
    """
    Analyse le texte des en-têtes (avant les premières données) pour déduire :
      - has_duration  : la ligne de données contient une durée HH:MM:SS
      - has_vel_b3    : présence d'une bande vitesse 15-18 km/h (décale les indices de +1)
      - has_decel_dist: les colonnes décel ont aussi des dist (format B, stride=2)

    Retourne (has_duration, has_vel_b3, has_decel_dist).
    """
    hl = header_text.lower()

    has_duration = bool(re.search(r'tot\s*dur|total\s*dur|duration|durée', hl))

    has_vel_b3 = bool(re.search(r'15\s*[-–]\s*18|vel\s+b3\b|b3\s+vel', hl))

    # Format B : 6 colonnes décel (effs + dist × 3) → ≥ 5 occurrences de "decel"
    decel_count = len(re.findall(r'\bdecel\b|\bdécel\b', hl))
    has_decel_dist = (decel_count >= 5)

    return has_duration, has_vel_b3, has_decel_dist


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION DEPUIS LES LIGNES DE TEXTE (PASSE 1)
# ─────────────────────────────────────────────────────────────────────────────

def _find_data_start(tokens):
    """
    Retourne l'index du premier token de données réel dans une ligne.
    Saute :
      • Les tokens alphabétiques (nom athlète, nom device)
      • Les entiers courts (< 50) qui suivent immédiatement les tokens alphabétiques
        → correspondent à un numéro de device type "Gouf 5" ou "Gen 2"
    """
    idx = 0

    # Sauter les tokens commençant par une lettre
    while idx < len(tokens) and re.match(r'^[A-Za-zÀ-ÿ]', tokens[idx]):
        idx += 1

    # Sauter les petits entiers type numéro de device (< 50) s'ils précèdent une grande valeur
    if idx < len(tokens) - 1:
        v_curr = _f(tokens[idx])
        v_next = _f(tokens[idx + 1]) if idx + 1 < len(tokens) else None
        if (v_curr is not None
                and v_curr == int(v_curr)
                and 0 < v_curr < 50
                and v_next is not None
                and (v_next > 100 or DUR_RE.search(tokens[idx + 1]))):
            idx += 1   # c'est un ID de device → on le saute

    return idx


def _parse_data_line(line, has_duration, has_vel_b3, has_decel_dist):
    """
    Transforme une ligne de données brutes en dict de métriques.
    Adapte le mapping selon le format détecté.
    """
    tokens = line.split()
    start  = _find_data_start(tokens)

    nums    = []
    dur_str = None

    for t in tokens[start:]:
        dur_m = DUR_RE.fullmatch(t)
        if dur_m:
            dur_str = dur_m.group(1)
            # La durée n'est PAS ajoutée à nums (champ séparé)
        else:
            v = _f(t)
            if v is not None:
                nums.append(v)
            # Les tokens non numériques au milieu sont ignorés

    def n(i):
        return nums[i] if 0 <= i < len(nums) else None

    # Décalage pour la bande vitesse 15-18 km/h supplémentaire (Format B)
    vo = 1 if has_vel_b3 else 0

    # Stride pour les décélérations :
    #   Format A : decel_b1_effs | decel_b2_effs | decel_b3_effs          (stride=1)
    #   Format B : decel_b1_effs | decel_b1_dist | decel_b2_effs | ...    (stride=2)
    ds = 2 if has_decel_dist else 1

    sess = _empty_session("")     # date sera remplie par l'appelant
    sess['distance_m']  = _i(n(0))
    sess['duree']       = dur_str
    sess['vmax_kmh']    = _f(n(1))
    sess['d_15_18']     = _i(n(2)) if has_vel_b3 else None
    sess['d_18_21']     = _i(n(2 + vo))
    sess['d_21_24']     = _i(n(3 + vo))
    sess['d_sup24']     = _i(n(4 + vo))
    sess['metrage_min'] = _f(n(5 + vo))
    sess['acc_b1_effs'] = _i(n(6 + vo))
    sess['acc_b1_dist'] = _f(n(7 + vo))
    sess['acc_b2_effs'] = _i(n(8 + vo))
    sess['acc_b2_dist'] = _f(n(9 + vo))
    sess['acc_b3_effs'] = _i(n(10 + vo))
    sess['acc_b3_dist'] = _f(n(11 + vo))
    sess['max_acc']     = _f(n(12 + vo))
    sess['decel_b1']    = _i(n(13 + vo))
    sess['decel_b2']    = _i(n(13 + vo + ds))
    sess['decel_b3']    = _i(n(13 + vo + ds * 2))
    return sess


def _session_is_plausible(sess):
    """Rejette les sessions dont les valeurs ne correspondent pas à des données GPS réelles."""
    dist  = sess.get('distance_m')
    vmax  = sess.get('vmax_kmh')
    m_min = sess.get('metrage_min')

    if dist  is not None and dist  > 100:           return True
    if vmax  is not None and 5 < vmax < 70:         return True
    if m_min is not None and 10 < m_min < 300:      return True
    return False


def _extract_from_text_lines(all_lines):
    """
    Passe 1 : parcourt toutes les lignes, détecte le format dans les en-têtes,
    puis extrait chaque paire (date → ligne de données).
    """
    # ── Détection du format depuis les 20 premières lignes ──────────────────
    header_sample = '\n'.join(all_lines[:20])
    has_duration, has_vel_b3, has_decel_dist = _detect_format(header_sample)
    print(f"[GPS] Format detecte: has_duration={has_duration}, "
          f"has_vel_b3={has_vel_b3}, has_decel_dist={has_decel_dist}")

    sessions   = []
    used_lines = set()
    i          = 0

    while i < len(all_lines):
        line = all_lines[i].strip()

        m = DATE_RE.search(line)
        if m:
            date_str = m.group(1)

            # Cherche la ligne de données (jusqu'à 7 lignes suivantes)
            data_line     = None
            data_line_idx = None

            for j in range(i + 1, min(i + 8, len(all_lines))):
                if j in used_lines:
                    continue
                l = all_lines[j].strip()
                if not l:
                    continue
                if ACT_RE.match(l):
                    continue
                # Critère : au moins 4 valeurs numériques standalone
                num_count = len(NUMS_IN.findall(l))
                has_dur   = bool(DUR_RE.search(l))
                if num_count >= 4 or (has_dur and num_count >= 1):
                    data_line     = l
                    data_line_idx = j
                    break

            if data_line:
                sess = _parse_data_line(data_line, has_duration, has_vel_b3, has_decel_dist)
                sess['date'] = date_str
                if _session_is_plausible(sess):
                    sessions.append(sess)
                    if data_line_idx is not None:
                        used_lines.add(data_line_idx)
                    i = data_line_idx + 1
                    continue

        i += 1

    return sessions


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION DEPUIS LES TABLES PDFPLUMBER (PASSE 2)
# ─────────────────────────────────────────────────────────────────────────────

# Mots-clés pour mapper les colonnes de la table (lowercase, sans doublons)
_HEADER_MAP = [
    ('date',        ['date', 'jour', 'day']),
    ('session_name',['session', 'activit', 'nom', 'name', 'séance']),
    ('distance_m',  ['tot dist', 'totdist', 'total dist', 'dist (m']),
    ('duree',       ['tot dur', 'duration', 'durée', 'time (']),
    ('vmax_kmh',    ['max vel', 'maxvel', 'vmax', 'max speed', 'vitesse max']),
    ('metrage_min', ['m/min', 'metrage', 'métrage', 'dist/min']),
    ('d_15_18',     ['15', '18']),     # affiné ci-dessous
    ('d_18_21',     ['18', '21']),
    ('d_21_24',     ['21', '24']),
    ('d_sup24',     ['>24', 'sup 24', '> 24', 'sup24']),
    ('acc_b1_effs', ['acc b1', 'acc 2-3', 'b1 eff']),
    ('acc_b1_dist', ['acc b1 dist', 'b1 dist']),
    ('acc_b2_effs', ['acc b2', 'acc 3-4', 'b2 eff']),
    ('acc_b2_dist', ['acc b2 dist', 'b2 dist']),
    ('acc_b3_effs', ['acc b3', 'acc >4', 'b3 eff']),
    ('acc_b3_dist', ['acc b3 dist', 'b3 dist']),
    ('max_acc',     ['max acc', 'acc max']),
    ('decel_b1',    ['dec b1', 'decel b1', 'décel b1']),
    ('decel_b2',    ['dec b2', 'decel b2', 'décel b2']),
    ('decel_b3',    ['dec b3', 'decel b3', 'décel b3']),
]


def _build_col_map(header_row):
    col = {}
    for i, cell in enumerate(header_row):
        if not cell:
            continue
        hl = re.sub(r'\s+', ' ', str(cell).lower().replace('\n', ' ')).strip()
        for metric, keywords in _HEADER_MAP:
            if metric in col:
                continue
            if any(kw in hl for kw in keywords):
                # Disambiguate velocity bands
                if metric == 'd_15_18' and not ('15' in hl and '18' in hl):
                    continue
                if metric == 'd_18_21' and not ('18' in hl and '21' in hl):
                    continue
                if metric == 'd_21_24' and not ('21' in hl and '24' in hl):
                    continue
                col[metric] = i
                break
    return col


def _row_to_session_mapped(row, col):
    cells    = [str(c or '').strip() for c in row]
    date_str = None

    if 'date' in col:
        m = DATE_RE.search(cells[col['date']])
        if m:
            date_str = m.group(1)
    if not date_str:
        for c in cells:
            m = DATE_RE.search(c)
            if m:
                date_str = m.group(1)
                break
    if not date_str:
        return None

    def get(key):
        idx = col.get(key)
        return cells[idx] if idx is not None and idx < len(cells) else None

    sess = _empty_session(date_str)
    sess['session_name'] = get('session_name')
    sess['distance_m']   = _i(get('distance_m'))
    sess['duree']        = get('duree')
    sess['vmax_kmh']     = _f(get('vmax_kmh'))
    sess['metrage_min']  = _f(get('metrage_min'))
    sess['d_15_18']      = _i(get('d_15_18'))
    sess['d_18_21']      = _i(get('d_18_21'))
    sess['d_21_24']      = _i(get('d_21_24'))
    sess['d_sup24']      = _i(get('d_sup24'))
    sess['acc_b1_effs']  = _i(get('acc_b1_effs'))
    sess['acc_b1_dist']  = _f(get('acc_b1_dist'))
    sess['acc_b2_effs']  = _i(get('acc_b2_effs'))
    sess['acc_b2_dist']  = _f(get('acc_b2_dist'))
    sess['acc_b3_effs']  = _i(get('acc_b3_effs'))
    sess['acc_b3_dist']  = _f(get('acc_b3_dist'))
    sess['max_acc']      = _f(get('max_acc'))
    sess['decel_b1']     = _i(get('decel_b1'))
    sess['decel_b2']     = _i(get('decel_b2'))
    sess['decel_b3']     = _i(get('decel_b3'))
    return sess


def _row_to_session_positional(row):
    """Extraction positionnelle sans en-têtes (dernier recours pour les tables)."""
    cells    = [str(c or '').strip() for c in row]
    date_str = None
    date_idx = 0

    for i, c in enumerate(cells):
        m = DATE_RE.search(c)
        if m:
            date_str = m.group(1)
            date_idx = i
            break
    if not date_str:
        return None

    # Collecte des valeurs après la date
    nums    = []
    dur_str = None
    for c in cells[date_idx + 1:]:
        if not c:
            continue
        dur_m = DUR_RE.fullmatch(c)
        if dur_m:
            dur_str = dur_m.group(1)
        else:
            v = _f(c)
            if v is not None:
                nums.append(v)

    def n(i):
        return nums[i] if 0 <= i < len(nums) else None

    sess = _empty_session(date_str)
    sess['distance_m']  = _i(n(0))
    sess['duree']       = dur_str
    sess['vmax_kmh']    = _f(n(1 if dur_str else 1))
    sess['d_18_21']     = _i(n(2))
    sess['d_21_24']     = _i(n(3))
    sess['d_sup24']     = _i(n(4))
    sess['metrage_min'] = _f(n(5))
    sess['acc_b1_effs'] = _i(n(6))
    sess['acc_b1_dist'] = _f(n(7))
    sess['acc_b2_effs'] = _i(n(8))
    sess['acc_b2_dist'] = _f(n(9))
    sess['acc_b3_effs'] = _i(n(10))
    sess['acc_b3_dist'] = _f(n(11))
    sess['max_acc']     = _f(n(12))
    sess['decel_b1']    = _i(n(13))
    sess['decel_b2']    = _i(n(14))
    sess['decel_b3']    = _i(n(15))
    return sess


def _extract_from_tables(tables):
    """Passe 2 : extraction depuis les tables pdfplumber (si grilles PDF présentes)."""
    sessions = []
    for table in tables:
        if not table or len(table) < 2:
            continue

        # Cherche une ligne d'en-tête (majorité de tokens textuels)
        header_idx = None
        col        = {}
        for i, row in enumerate(table[:6]):
            if not row:
                continue
            cells = [str(c or '').strip() for c in row]
            text_count = sum(
                1 for c in cells
                if c and not NUM_RE.match(c.replace(',', '.')) and not DATE_RE.search(c)
            )
            if text_count >= 2:
                col = _build_col_map(row)
                if col:
                    header_idx = i
                    break

        if header_idx is not None and col:
            print(f"[GPS] Table : entete trouve -> {col}")
            for row in table[header_idx + 1:]:
                if not row:
                    continue
                sess = _row_to_session_mapped(row, col)
                if sess and _session_is_plausible(sess):
                    sessions.append(sess)
        else:
            # Pas d'en-tête → tentative positionnelle
            for row in table:
                if not row:
                    continue
                if any(DATE_RE.search(str(c or '')) for c in row):
                    sess = _row_to_session_positional(row)
                    if sess and _session_is_plausible(sess):
                        sessions.append(sess)

    return sessions


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK BRUT PAR MOTS-CLÉS (PASSE 3)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_raw_fallback(all_lines):
    """
    Passe 3 : extrait les dates et les nombres adjacents sans faire d'hypothèse
    sur le format. Retourne toujours au moins quelques sessions si des dates
    sont présentes dans le texte.
    """
    full_text  = '\n'.join(all_lines)
    all_dates  = list(dict.fromkeys(DATE_RE.findall(full_text)))  # unique + ordre

    if not all_dates:
        return []

    sessions = []
    for k, date_str in enumerate(all_dates):
        pos_start = full_text.find(date_str)
        pos_end   = (full_text.find(all_dates[k + 1]) if k + 1 < len(all_dates)
                     else len(full_text))
        block     = full_text[pos_start:pos_end]

        # Durée
        dur_m   = DUR_RE.search(block)
        dur_str = dur_m.group(1) if dur_m else None

        # Tous les nombres standalone (hors fragments de date)
        raw_nums = [_f(t) for t in NUMS_IN.findall(block)
                    if t not in date_str.split('/')]
        nums = [v for v in raw_nums if v is not None]

        def find_after(kw):
            pat = re.compile(re.escape(kw) + r'[^\d\n]{0,20}(\d+(?:[.,]\d+)?)',
                             re.IGNORECASE)
            m2 = pat.search(block)
            return _f(m2.group(1)) if m2 else None

        dist = (find_after('Tot Dist') or find_after('Total Dist') or
                find_after('Distance') or
                next((v for v in nums if v > 100), None))
        vmax = (find_after('Max Vel') or find_after('Max Speed') or
                next((v for v in nums if 5 < v < 70), None))

        sess = _empty_session(date_str)
        sess['distance_m'] = _i(dist)
        sess['duree']      = dur_str
        sess['vmax_kmh']   = _f(vmax)

        if _session_is_plausible(sess):
            sessions.append(sess)
            print(f"[GPS] Fallback {date_str}: dist={dist}, vmax={vmax}, dur={dur_str}")

    return sessions


# ─────────────────────────────────────────────────────────────────────────────
# PARSER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def parse_gps_pdf(pdf_source):
    """
    pdf_source : chemin (str/Path) OU objet BytesIO.
    Retourne : {sessions, semaines, progression, meta}
    """
    all_lines  = []
    all_tables = []
    athlete_name = "Athlète"

    # ── Extraction PDF ────────────────────────────────────────────────────────
    with pdfplumber.open(pdf_source) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            # Nom de l'athlète — plusieurs patterns
            for pat in [
                r'BILAN\s+([A-ZÉÈÊÀÙÛÜa-zéèêàùûü\s\-]{2,40})',
                r'SEANCE\s+([A-ZÉÈÊÀÙÛÜa-zéèêàùûü\s\-]{2,40})',
                r'Player[:\s]+([A-Z][A-Za-z\s\-]{1,40})',
                r'Athlete[:\s]+([A-Z][A-Za-z\s\-]{1,40})',
                r'Joueur[:\s]+([A-Z][A-Za-z\s\-]{1,40})',
            ]:
                m = re.search(pat, text)
                if m:
                    candidate = m.group(1).strip().title()
                    if 2 < len(candidate) < 50:
                        athlete_name = candidate
                        break

            all_lines.extend(text.split('\n'))

            try:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
                    print(f"[GPS] Page {page.page_number}: {len(tables)} table(s)")
            except Exception as e:
                print(f"[GPS] extract_tables page {page.page_number}: {e}")

    print(f"[GPS] Texte brut : {len(all_lines)} lignes | Tables : {len(all_tables)}")

    # ── Passe 1 : lignes de texte ─────────────────────────────────────────────
    sessions = _extract_from_text_lines(all_lines)
    print(f"[GPS] Passe 1 (texte)   -> {len(sessions)} session(s)")

    # ── Passe 2 : tables pdfplumber ──────────────────────────────────────────
    if not sessions and all_tables:
        sessions = _extract_from_tables(all_tables)
        print(f"[GPS] Passe 2 (tables)  -> {len(sessions)} session(s)")

    # ── Passe 3 : fallback brut ───────────────────────────────────────────────
    if not sessions:
        sessions = _extract_raw_fallback(all_lines)
        print(f"[GPS] Passe 3 (fallback)-> {len(sessions)} session(s)")

    # ── Dédoublonnage + tri chronologique ────────────────────────────────────
    seen   = set()
    unique = []
    for s in sessions:
        if s['date'] not in seen:
            seen.add(s['date'])
            unique.append(s)
    sessions = sorted(unique, key=lambda s: _to_dt(s['date']) or datetime.min)

    # ── Agrégation par semaine ────────────────────────────────────────────────
    NUM_COLS = [
        "distance_m", "vmax_kmh",
        "d_15_18", "d_18_21", "d_21_24", "d_sup24",
        "metrage_min",
        "acc_b1_effs", "acc_b1_dist",
        "acc_b2_effs", "acc_b2_dist",
        "acc_b3_effs", "acc_b3_dist",
        "max_acc",
        "decel_b1", "decel_b2", "decel_b3",
    ]

    raw_weeks = {}
    for s in sessions:
        wk = _week_key(s['date'])
        if wk not in raw_weeks:
            raw_weeks[wk] = {"dates": []}
            for c in NUM_COLS:
                raw_weeks[wk][c] = []
        raw_weeks[wk]["dates"].append(s['date'])
        for c in NUM_COLS:
            if s.get(c) is not None:
                raw_weeks[wk][c].append(s[c])

    def _sum(lst): return round(sum(lst), 1) if lst else None
    def _max(lst): return round(max(lst), 1) if lst else None
    def _avg(lst): return round(sum(lst) / len(lst), 1) if lst else None

    semaines = {}
    for wk in sorted(raw_weeks.keys()):
        d     = raw_weeks[wk]
        dates = sorted(d["dates"], key=lambda x: _to_dt(x) or datetime.min)
        d15   = _sum(d["d_15_18"])
        d18   = _sum(d["d_18_21"])
        d21   = _sum(d["d_21_24"])
        d24   = _sum(d["d_sup24"])
        semaines[wk] = {
            "label":      f"Semaine {wk.split('-W')[1]}  ({dates[0]} au {dates[-1]})",
            "n_sessions": len(dates),
            "dates":      dates,
            "distance_m":  _sum(d["distance_m"]),
            "vmax_kmh":    _max(d["vmax_kmh"]),
            "d_15_18":     d15,
            "d_18_21":     d18,
            "d_21_24":     d21,
            "d_sup24":     d24,
            "d_hsr":       round((d18 or 0) + (d21 or 0) + (d24 or 0), 1) or None,
            "metrage_min": _avg(d["metrage_min"]),
            "acc_b1_effs": _sum(d["acc_b1_effs"]),
            "acc_b1_dist": _sum(d["acc_b1_dist"]),
            "acc_b2_effs": _sum(d["acc_b2_effs"]),
            "acc_b2_dist": _sum(d["acc_b2_dist"]),
            "acc_b3_effs": _sum(d["acc_b3_effs"]),
            "acc_b3_dist": _sum(d["acc_b3_dist"]),
            "max_acc":     _max(d["max_acc"]),
            "decel_b1":    _sum(d["decel_b1"]),
            "decel_b2":    _sum(d["decel_b2"]),
            "decel_b3":    _sum(d["decel_b3"]),
        }

    # ── Progression globale ───────────────────────────────────────────────────
    wk_keys    = list(semaines.keys())
    progression = {}
    if len(wk_keys) >= 2:
        first = semaines[wk_keys[0]]
        last  = semaines[wk_keys[-1]]
        for col in ["distance_m", "vmax_kmh", "d_hsr", "d_18_21", "d_21_24",
                    "d_sup24", "metrage_min",
                    "acc_b1_effs", "acc_b2_effs", "acc_b3_effs",
                    "max_acc", "decel_b1", "decel_b2", "decel_b3"]:
            v0, v1 = first.get(col), last.get(col)
            if v0 and v1 and v0 != 0:
                progression[col] = round((v1 - v0) / abs(v0) * 100, 1)

    meta = {
        "athlete":    athlete_name,
        "n_sessions": len(sessions),
        "n_semaines": len(semaines),
        "periode":    (f"{sessions[0]['date']} > {sessions[-1]['date']}"
                       if sessions else "-"),
    }

    result = {
        "sessions":    sessions,
        "semaines":    semaines,
        "progression": progression,
        "meta":        meta,
    }

    # ── Dump console pour diagnostic en direct ────────────────────────────────
    try:
        print("DUMP GPS DATA:", json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except UnicodeEncodeError:
        print("DUMP GPS DATA:", json.dumps(result, indent=2, ensure_ascii=True, default=str))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSE TEXTUELLE (conservée pour compatibilité CLI)
# ─────────────────────────────────────────────────────────────────────────────

def analyser_progression(result):
    semaines = result["semaines"]
    prog     = result["progression"]
    meta     = result["meta"]

    SEP = "=" * 72
    sep = "-" * 72

    lines = [
        SEP,
        f"  RAPPORT GPS CATAPULT OPENFIELD - {meta['athlete'].upper()}",
        f"  Periode : {meta['periode']}  |  {meta['n_sessions']} sessions  |  {meta['n_semaines']} semaines",
        SEP,
    ]

    for wk_key, s in semaines.items():
        lines.append(f"\n{sep}")
        lines.append(f"  {s['label']}  -  {s['n_sessions']} session(s)")
        lines.append(sep)

        def row(label, val, unit=""):
            if val is None:
                v = "-"
            elif isinstance(val, int):
                v = f"{val:,}".replace(",", " ")
            else:
                v = f"{val:.1f}"
            return f"  {label:<38} {(v + ' ' + unit).strip():>14}"

        lines.append(row("Distance totale",              s["distance_m"],  "m"))
        lines.append(row("Vitesse maximale",             s["vmax_kmh"],    "km/h"))
        lines.append(row("Metrage / minute",             s["metrage_min"], "m/min"))
        lines.append(row("Distance HSR (>18 km/h)",      s["d_hsr"],       "m"))
        if s.get("d_15_18") is not None:
            lines.append(row("  15-18 km/h",             s["d_15_18"],     "m"))
        lines.append(row("  18-21 km/h",                 s["d_18_21"],     "m"))
        lines.append(row("  21-24 km/h",                 s["d_21_24"],     "m"))
        lines.append(row("  >24 km/h",                   s["d_sup24"],     "m"))
        lines.append(row("Acc B1 (2-3 m/s2) effs",       s["acc_b1_effs"], "effs"))
        lines.append(row("Acc B1 (2-3 m/s2) dist",       s["acc_b1_dist"], "m"))
        lines.append(row("Acc B2 (3-4 m/s2) effs",       s["acc_b2_effs"], "effs"))
        lines.append(row("Acc B2 (3-4 m/s2) dist",       s["acc_b2_dist"], "m"))
        lines.append(row("Acc B3 (>4 m/s2) effs",        s["acc_b3_effs"], "effs"))
        lines.append(row("Acc B3 (>4 m/s2) dist",        s["acc_b3_dist"], "m"))
        lines.append(row("Acceleration max",              s["max_acc"],     "m/s2"))
        lines.append(row("Decelerations B1",              s["decel_b1"],    "effs"))
        lines.append(row("Decelerations B2",              s["decel_b2"],    "effs"))
        lines.append(row("Decelerations B3",              s["decel_b3"],    "effs"))

    labels = {
        "distance_m":  "Distance totale",
        "vmax_kmh":    "Vitesse maximale",
        "d_hsr":       "Distance HSR (>18 km/h)",
        "d_18_21":     "Distance 18-21 km/h",
        "d_21_24":     "Distance 21-24 km/h",
        "d_sup24":     "Distance >24 km/h",
        "metrage_min": "Metrage/minute",
        "acc_b1_effs": "Acc B1 efforts",
        "acc_b2_effs": "Acc B2 efforts",
        "acc_b3_effs": "Acc B3 efforts",
        "max_acc":     "Acceleration max",
        "decel_b1":    "Decelerations B1",
        "decel_b2":    "Decelerations B2",
        "decel_b3":    "Decelerations B3",
    }
    lines.append(f"\n{SEP}")
    lines.append("  TENDANCES GLOBALES - 1re semaine > derniere semaine")
    lines.append(SEP)
    for k, label in labels.items():
        if k in prog:
            p     = prog[k]
            arrow = "+ PROGRESSION" if p > 0 else ("- REGRESSION " if p < 0 else "= STABLE    ")
            lines.append(f"  {arrow}  {label:<35}  {p:+.1f}%")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gps_parser.py fichier.pdf [--json]")
        sys.exit(1)

    path    = sys.argv[1]
    as_json = "--json" in sys.argv

    result = parse_gps_pdf(path)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print("\nSESSIONS BRUTES :")
        header = ["date", "distance_m", "duree", "vmax_kmh",
                  "d_15_18", "d_18_21", "d_21_24", "d_sup24",
                  "metrage_min", "acc_b1_effs", "acc_b1_dist",
                  "acc_b2_effs", "acc_b2_dist", "acc_b3_effs", "acc_b3_dist",
                  "max_acc", "decel_b1", "decel_b2", "decel_b3"]
        print("  " + " | ".join(f"{h:>12}" for h in header))
        for s in result["sessions"]:
            vals = [str(s.get(h) or "-") for h in header]
            print("  " + " | ".join(f"{v:>12}" for v in vals))
        print()
        print(analyser_progression(result))
