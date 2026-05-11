"""
biodex_parser.py
================
ÉTAPE 1 — Parser les PDFs Biodex (Biodex Advantage BX 5.3)
Projet CERS Capbreton — Rapport Isocinétique automatisé

Auteur : Stage FISE3 Informatique 2026
Patient test : N. Della Schiava (genou lésé Gauche)

Structure des PDFs Biodex :
  - Page 1 → série 60°/s  (force)
  - Page 2 → série 240°/s (puissance)
  - Chaque page contient Extension (D) + Flexion (G) côte à côte
  - Colonnes : Sain (D) | Lésé (G) | Déficit (%)

IMPORTANT : Le PDF entrée a les mots collés ("Nomdupatient:"),
le PDF sortie a des espaces normaux ("Nom du patient:").
Le parser gère les deux variantes.
"""

import re
import pdfplumber
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. Structures de données
# ---------------------------------------------------------------------------

@dataclass
class MetriqueIso:
    """Une ligne de mesure isocinétique : Sain(D) / Lésé(G) / Déficit(%)"""
    sain_d: Optional[float] = None
    lese_g: Optional[float] = None
    deficit_pct: Optional[float] = None

    def to_dict(self, prefix: str = "") -> dict:
        return {
            f"{prefix}sain_d": self.sain_d,
            f"{prefix}lese_g": self.lese_g,
            f"{prefix}deficit_pct": self.deficit_pct,
        }


@dataclass
class SerieIso:
    """
    Résultats d'une série isocinétique (60°/s ou 240°/s).
    Contient Extension et Flexion, chacun avec leurs métriques clés.
    """
    vitesse: str = ""   # "60" ou "240"

    # Extension
    ext_moment_max: MetriqueIso = field(default_factory=MetriqueIso)
    ext_travail_max: MetriqueIso = field(default_factory=MetriqueIso)
    ext_puissance_max: MetriqueIso = field(default_factory=MetriqueIso)

    # Flexion
    flex_moment_max: MetriqueIso = field(default_factory=MetriqueIso)
    flex_travail_max: MetriqueIso = field(default_factory=MetriqueIso)
    flex_puissance_max: MetriqueIso = field(default_factory=MetriqueIso)

    # Ratio I/Q (Flexion/Extension = Ratio AGON/ANTAG)
    ratio_sain_d: Optional[float] = None
    ratio_lese_g: Optional[float] = None

    def to_dict(self) -> dict:
        d = {"vitesse_deg_s": self.vitesse}
        d.update(self.ext_moment_max.to_dict("ext_moment_max_"))
        d.update(self.ext_travail_max.to_dict("ext_travail_max_"))
        d.update(self.ext_puissance_max.to_dict("ext_puissance_max_"))
        d.update(self.flex_moment_max.to_dict("flex_moment_max_"))
        d.update(self.flex_travail_max.to_dict("flex_travail_max_"))
        d.update(self.flex_puissance_max.to_dict("flex_puissance_max_"))
        d["ratio_iq_sain_d"] = self.ratio_sain_d
        d["ratio_iq_lese_g"] = self.ratio_lese_g
        return d


@dataclass
class PatientBiodex:
    """
    Toutes les données Biodex d'un patient :
    infos administratives + 2 séries (60°/s + 240°/s)
    """
    # Infos patient
    nom: str = ""
    age: Optional[int] = None
    poids_kg: Optional[float] = None
    taille_cm: Optional[int] = None
    sexe: str = ""
    lese: str = ""          # "Gauche" ou "Droit"
    date_test: str = ""     # "30/03/2026"
    articulation: str = ""  # "Genou"
    position: str = ""      # Renseigné par l'app (non présent dans le PDF)

    # Résultats
    serie_60: Optional[SerieIso] = None
    serie_240: Optional[SerieIso] = None

    def to_summary_dict(self) -> dict:
        """Retourne un dict plat résumant les métriques clés."""
        d = {
            "nom": self.nom,
            "age": self.age,
            "poids_kg": self.poids_kg,
            "taille_cm": self.taille_cm,
            "sexe": self.sexe,
            "lese": self.lese,
            "date_test": self.date_test,
            "articulation": self.articulation,
        }
        if self.serie_60:
            for k, v in self.serie_60.to_dict().items():
                d[f"s60_{k}"] = v
        if self.serie_240:
            for k, v in self.serie_240.to_dict().items():
                d[f"s240_{k}"] = v
        return d


# ---------------------------------------------------------------------------
# 2. Fonctions utilitaires
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """
    Normalise le texte extrait par pdfplumber.
    Gère les deux variantes :
      - PDF entrée : mots collés ("Nomdupatient:")
      - PDF sortie : espaces normaux ("Nom du patient:")
    Stratégie : on ne touche PAS aux espaces (ils sont déjà là ou pas),
    on travaille uniquement en regex flexibles.
    """
    # Supprimer les retours chariot, normaliser les espaces multiples
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text


def _parse_float(value_str: str) -> Optional[float]:
    """
    Convertit une chaîne française en float.
    Ex : "316,9" → 316.9  |  "-1,6" → -1.6  |  "11,1" → 11.1
    Gère aussi les valeurs avec parenthèses type "316,9(Rep3)" → 316.9
    """
    if not value_str:
        return None
    # Supprimer tout ce qui suit la première parenthèse (ex: "(Rep3)")
    value_str = re.sub(r'\(.*?\)', '', value_str).strip()
    # Remplacer virgule décimale française par point
    value_str = value_str.replace(',', '.')
    # Supprimer les espaces
    value_str = value_str.replace(' ', '')
    try:
        return float(value_str)
    except ValueError:
        return None


def _extract_metric_from_line(line: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Extrait (sain_d, lese_g, deficit_pct) depuis une ligne de texte Biodex.

    Exemples de lignes à parser :
      "Momentmax(N•m) 316,9(Rep3) 313,6(Rep2) 1,0 173,0(Rep2) 153,9(Rep2) 11,1"
      "Moment max (N•m) 328,0 (Rep 2) 333,3 (Rep 2) -1,6 195,4 (Rep 2) 162,0 (Rep 1) 17,1"
      "TravailMax(J) 379,3(Rep3) 386,8(Rep3) -2,0 239,2(Rep1) 184,9(Rep2) 22,7"

    Structure : label | EXT_sain | EXT_lese | EXT_deficit | FLEX_sain | FLEX_lese | FLEX_deficit
    On retourne EXT_sain, EXT_lese, EXT_deficit (les 3 premières valeurs numériques après le label).
    """
    # Regex : trouve tous les nombres (entiers ou décimaux, signés) dans la ligne
    # On ignore les contenus entre parenthèses (Rep N)
    line_clean = re.sub(r'\(Rep\s*\d+\)', '', line)
    # Trouver tous les nombres (accepte négatifs et virgules françaises)
    nums = re.findall(r'-?\d+[,.]?\d*', line_clean)
    floats = []
    for n in nums:
        v = _parse_float(n)
        if v is not None:
            floats.append(v)

    # Les valeurs utiles sont après le label (pas de numéro dans le label normalement)
    # On retourne (sain_d, lese_g, deficit) pour Extension, et pour Flexion
    return floats  # On retourne tout, l'appelant choisit les indices


# ---------------------------------------------------------------------------
# 3. Parser d'une page PDF Biodex
# ---------------------------------------------------------------------------

def _parse_page(page_text: str, vitesse: str) -> SerieIso:
    """
    Parse une page PDF Biodex et retourne une SerieIso.
    Chaque page contient Extension ET Flexion côte à côte.

    Structure de la ligne :
    [LABEL] [EXT_sain] [EXT_lese] [EXT_deficit] [FLEX_sain] [FLEX_lese] [FLEX_deficit]
    """
    serie = SerieIso(vitesse=vitesse)
    lines = page_text.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Nettoyer les "(Rep N)" pour faciliter l'extraction des nombres
        line_clean = re.sub(r'\(Rep\s*\d+\)', '', line_stripped)

        # Trouver tous les nombres dans la ligne
        nums = re.findall(r'-?\d+[,.]?\d*', line_clean)
        floats = []
        for n in nums:
            v = _parse_float(n)
            if v is not None:
                floats.append(v)

        # Si on a moins de 3 valeurs, pas assez pour une métrique
        if len(floats) < 3:
            continue

        # Détecte le type de ligne par mots-clés (flexibles : avec ou sans espaces)
        line_lower = line_stripped.lower().replace(' ', '')

        # --- MOMENT MAX ---
        if re.search(r'momentmax\(n', line_lower) and 'moy' not in line_lower and 'poids' not in line_lower:
            # floats : [EXT_sain, EXT_lese, EXT_deficit, FLEX_sain, FLEX_lese, FLEX_deficit]
            if len(floats) >= 3:
                serie.ext_moment_max = MetriqueIso(floats[0], floats[1], floats[2])
            if len(floats) >= 6:
                serie.flex_moment_max = MetriqueIso(floats[3], floats[4], floats[5])

        # --- TRAVAIL MAX ---
        elif re.search(r'travailmax\(j\)', line_lower):
            if len(floats) >= 3:
                serie.ext_travail_max = MetriqueIso(floats[0], floats[1], floats[2])
            if len(floats) >= 6:
                serie.flex_travail_max = MetriqueIso(floats[3], floats[4], floats[5])

        # --- PUISSANCE MAXIMALE ---
        elif re.search(r'puissancemaximale\(w\)', line_lower):
            if len(floats) >= 3:
                serie.ext_puissance_max = MetriqueIso(floats[0], floats[1], floats[2])
            if len(floats) >= 6:
                serie.flex_puissance_max = MetriqueIso(floats[3], floats[4], floats[5])

        # --- RATIO AGON/ANTAG ---
        elif re.search(r'ratioagon', line_lower):
            if len(floats) >= 2:
                serie.ratio_sain_d = floats[0]
                serie.ratio_lese_g = floats[1]

    return serie


# ---------------------------------------------------------------------------
# 4. Parser d'en-tête patient
# ---------------------------------------------------------------------------

def _parse_patient_header(page_text: str) -> dict:
    """
    Extrait les infos patient depuis l'en-tête du PDF.
    Gère les deux formats (mots collés ou avec espaces).
    """
    info = {}

    # Normaliser : supprimer espaces superflus mais garder les sauts de ligne
    text = page_text

    # NOM PATIENT — "Nomdupatient: N.DellaSchiava" OU "Nom du patient: N. Della Schiava"
    m = re.search(r'[Nn]om\s*du\s*patient\s*:\s*(.+?)(?:Date|Heure|$)', text, re.IGNORECASE)
    if m:
        info['nom'] = m.group(1).strip().rstrip()

    # DATE
    m = re.search(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    if m:
        info['date_test'] = m.group(1)

    # ÂGE
    m = re.search(r'[AÂ]ge\s*:\s*(\d+)', text)
    if m:
        info['age'] = int(m.group(1))

    # POIDS
    m = re.search(r'Poids\s*\(kg\)\s*:\s*([\d,]+)', text)
    if m:
        info['poids_kg'] = _parse_float(m.group(1))

    # TAILLE
    m = re.search(r'Taille\s*\(cm\)\s*:\s*([\d,]+)', text)
    if m:
        v = _parse_float(m.group(1))
        info['taille_cm'] = int(v) if v else None

    # SEXE
    m = re.search(r'Sexe\s*:\s*(\w+)', text)
    if m:
        info['sexe'] = m.group(1)

    # CÔTÉ LÉSÉ
    m = re.search(r'Lésé\s*:\s*(Gauche|Droit|gauche|droit)', text)
    if m:
        info['lese'] = m.group(1).capitalize()

    # ARTICULATION
    m = re.search(r'Articulation\s*:\s*(\w+)', text)
    if m:
        info['articulation'] = m.group(1)

    return info


# ---------------------------------------------------------------------------
# 5. Fonction principale : parse_biodex_pdf()
# ---------------------------------------------------------------------------

def parse_biodex_pdf(pdf_path: str) -> PatientBiodex:
    """
    Parse complet d'un PDF Biodex (2 pages : 60°/s + 240°/s).

    Args:
        pdf_path: chemin vers le PDF Biodex

    Returns:
        PatientBiodex avec toutes les données extraites

    Raises:
        FileNotFoundError si le fichier n'existe pas
        ValueError si le PDF ne ressemble pas à un Biodex valide
    """
    patient = PatientBiodex()

    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 1:
            raise ValueError(f"PDF vide : {pdf_path}")

        # --- PAGE 1 : 60°/s ---
        page1_text = pdf.pages[0].extract_text()
        if not page1_text:
            raise ValueError(f"Impossible d'extraire le texte de la page 1 : {pdf_path}")

        # En-tête patient (une seule fois, depuis page 1)
        header = _parse_patient_header(page1_text)
        patient.nom = header.get('nom', '')
        patient.age = header.get('age')
        patient.poids_kg = header.get('poids_kg')
        patient.taille_cm = header.get('taille_cm')
        patient.sexe = header.get('sexe', '')
        patient.lese = header.get('lese', '')
        patient.date_test = header.get('date_test', '')
        patient.articulation = header.get('articulation', '')

        # Série 60°/s
        patient.serie_60 = _parse_page(page1_text, vitesse="60")

        # --- PAGE 2 : 240°/s ---
        if len(pdf.pages) >= 2:
            page2_text = pdf.pages[1].extract_text()
            if page2_text:
                patient.serie_240 = _parse_page(page2_text, vitesse="240")

    return patient


# ---------------------------------------------------------------------------
# 6. Calcul des progressions entrée → sortie (ÉTAPE 2)
# ---------------------------------------------------------------------------

def couleur_deficit(deficit_pct: Optional[float]) -> str:
    """
    Retourne le code couleur selon la norme Biodex CERS.
    🟢 vert  : déficit < 10%
    🟠 orange: déficit 10-20%
    🔴 rouge : déficit > 20%
    """
    if deficit_pct is None:
        return "gray"
    abs_d = abs(deficit_pct)
    if abs_d < 10:
        return "green"
    elif abs_d <= 20:
        return "orange"
    else:
        return "red"


def couleur_progression(progression_pct: Optional[float]) -> str:
    """
    Retourne le code couleur de la progression entrée → sortie.
    ✅ vert  : amélioration (progression positive)
    ❌ rouge : dégradation (progression négative)
    """
    if progression_pct is None:
        return "gray"
    return "green" if progression_pct >= 0 else "red"


def calcul_progression(valeur_entree: Optional[float], valeur_sortie: Optional[float]) -> Optional[float]:
    """
    Calcule la progression en % entre entrée et sortie.
    Formule : ((sortie - entree) / |entree|) * 100
    """
    if valeur_entree is None or valeur_sortie is None:
        return None
    if valeur_entree == 0:
        return None
    return round(((valeur_sortie - valeur_entree) / abs(valeur_entree)) * 100, 1)


def comparer_tests(entree: PatientBiodex, sortie: PatientBiodex) -> pd.DataFrame:
    """
    Compare les données Biodex entrée et sortie.
    Retourne un DataFrame structuré avec toutes les métriques clés,
    leurs valeurs, déficits et progressions.

    Columns: vitesse | mouvement | metrique |
             entree_sain | entree_lese | entree_deficit |
             sortie_sain | sortie_lese | sortie_deficit |
             progression_pct | couleur_progression | couleur_deficit_sortie
    """
    rows = []

    def add_row(vitesse, mouvement, metrique, e_metric: MetriqueIso, s_metric: MetriqueIso, unite=""):
        prog = calcul_progression(e_metric.lese_g, s_metric.lese_g)
        rows.append({
            "vitesse": vitesse,
            "mouvement": mouvement,
            "metrique": metrique,
            "unite": unite,
            "entree_sain_d": e_metric.sain_d,
            "entree_lese_g": e_metric.lese_g,
            "entree_deficit_pct": e_metric.deficit_pct,
            "sortie_sain_d": s_metric.sain_d,
            "sortie_lese_g": s_metric.lese_g,
            "sortie_deficit_pct": s_metric.deficit_pct,
            "progression_pct": prog,
            "couleur_progression": couleur_progression(prog),
            "couleur_deficit_entree": couleur_deficit(e_metric.deficit_pct),
            "couleur_deficit_sortie": couleur_deficit(s_metric.deficit_pct),
        })

    # --- Série 60°/s ---
    if entree.serie_60 and sortie.serie_60:
        e60, s60 = entree.serie_60, sortie.serie_60
        add_row("60°/s", "Extension", "Moment Max", e60.ext_moment_max, s60.ext_moment_max, "N·m")
        add_row("60°/s", "Extension", "Travail Max", e60.ext_travail_max, s60.ext_travail_max, "J")
        add_row("60°/s", "Extension", "Puissance Max", e60.ext_puissance_max, s60.ext_puissance_max, "W")
        add_row("60°/s", "Flexion",   "Moment Max", e60.flex_moment_max, s60.flex_moment_max, "N·m")
        add_row("60°/s", "Flexion",   "Travail Max", e60.flex_travail_max, s60.flex_travail_max, "J")
        add_row("60°/s", "Flexion",   "Puissance Max", e60.flex_puissance_max, s60.flex_puissance_max, "W")

        # Ratio I/Q
        prog_ratio_sain = calcul_progression(e60.ratio_sain_d, s60.ratio_sain_d)
        prog_ratio_lese = calcul_progression(e60.ratio_lese_g, s60.ratio_lese_g)
        rows.append({
            "vitesse": "60°/s", "mouvement": "—", "metrique": "Ratio I/Q",
            "unite": "%",
            "entree_sain_d": e60.ratio_sain_d, "entree_lese_g": e60.ratio_lese_g,
            "entree_deficit_pct": None,
            "sortie_sain_d": s60.ratio_sain_d, "sortie_lese_g": s60.ratio_lese_g,
            "sortie_deficit_pct": None,
            "progression_pct": prog_ratio_lese,
            "couleur_progression": couleur_progression(prog_ratio_lese),
            "couleur_deficit_entree": None,
            "couleur_deficit_sortie": None,
        })

    # --- Série 240°/s ---
    if entree.serie_240 and sortie.serie_240:
        e240, s240 = entree.serie_240, sortie.serie_240
        add_row("240°/s", "Extension", "Moment Max", e240.ext_moment_max, s240.ext_moment_max, "N·m")
        add_row("240°/s", "Extension", "Travail Max", e240.ext_travail_max, s240.ext_travail_max, "J")
        add_row("240°/s", "Extension", "Puissance Max", e240.ext_puissance_max, s240.ext_puissance_max, "W")
        add_row("240°/s", "Flexion",   "Moment Max", e240.flex_moment_max, s240.flex_moment_max, "N·m")
        add_row("240°/s", "Flexion",   "Travail Max", e240.flex_travail_max, s240.flex_travail_max, "J")
        add_row("240°/s", "Flexion",   "Puissance Max", e240.flex_puissance_max, s240.flex_puissance_max, "W")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 7. Fonction de test / rapport terminal
# ---------------------------------------------------------------------------

def afficher_patient(patient: PatientBiodex, label: str = ""):
    """Affiche un résumé lisible du patient dans le terminal."""
    print(f"\n{'='*60}")
    print(f"  {label} — {patient.date_test}")
    print(f"{'='*60}")
    print(f"  Nom       : {patient.nom}")
    print(f"  Âge       : {patient.age} ans")
    print(f"  Poids     : {patient.poids_kg} kg  |  Taille : {patient.taille_cm} cm")
    print(f"  Sexe      : {patient.sexe}")
    print(f"  Lésé      : {patient.lese}")
    print(f"  Articul.  : {patient.articulation}")

    COULEURS = {"green": "🟢", "orange": "🟠", "red": "🔴", "gray": "⚪"}

    for serie in [patient.serie_60, patient.serie_240]:
        if not serie:
            continue
        print(f"\n  ── Vitesse {serie.vitesse}°/s {'(Force)' if serie.vitesse=='60' else '(Puissance)'}")
        print(f"  {'Mouvement':<12} {'Métrique':<15} {'Sain(D)':>8} {'Lésé(G)':>8} {'Déficit':>8}")
        print(f"  {'-'*55}")

        def ligne(mouvement, label, m: MetriqueIso):
            c = COULEURS.get(couleur_deficit(m.deficit_pct), "⚪")
            sd = f"{m.sain_d:>7.1f}" if m.sain_d is not None else "     N/A"
            lg = f"{m.lese_g:>7.1f}" if m.lese_g is not None else "     N/A"
            df = f"{m.deficit_pct:>6.1f}%" if m.deficit_pct is not None else "    N/A"
            print(f"  {mouvement:<12} {label:<15} {sd} {lg} {c} {df}")

        ligne("Extension", "Moment Max",   serie.ext_moment_max)
        ligne("Extension", "Travail Max",  serie.ext_travail_max)
        ligne("Extension", "Puissance Max",serie.ext_puissance_max)
        ligne("Flexion",   "Moment Max",   serie.flex_moment_max)
        ligne("Flexion",   "Travail Max",  serie.flex_travail_max)
        ligne("Flexion",   "Puissance Max",serie.flex_puissance_max)

        if serie.ratio_sain_d is not None:
            print(f"  {'Ratio I/Q':<28} {serie.ratio_sain_d:>7.1f}% {serie.ratio_lese_g:>7.1f}%")


def afficher_comparaison(df: pd.DataFrame):
    """Affiche le tableau de comparaison entrée/sortie dans le terminal."""
    print(f"\n{'='*80}")
    print("  COMPARAISON ENTRÉE → SORTIE")
    print(f"{'='*80}")

    COULEURS = {"green": "🟢", "orange": "🟠", "red": "🔴", "gray": "⚪"}
    FLECHES = {"green": "▲", "red": "▼", "gray": "—"}

    vitesse_courante = ""
    for _, row in df.iterrows():
        if row['vitesse'] != vitesse_courante:
            vitesse_courante = row['vitesse']
            print(f"\n  ── {vitesse_courante} {'(Force)' if '60' in vitesse_courante else '(Puissance)'}")
            print(f"  {'Mvt':<10} {'Métrique':<15} {'Ent.Sain':>8} {'Ent.Lésé':>8} {'Ent.Déf':>8}  "
                  f"{'Sor.Sain':>8} {'Sor.Lésé':>8} {'Sor.Déf':>8}  {'Prog':>7}")
            print(f"  {'-'*78}")

        if row['metrique'] == 'Ratio I/Q':
            print(f"  {'—':<10} {'Ratio I/Q':<15} "
                  f"{row['entree_sain_d']:>7.1f}% {row['entree_lese_g']:>7.1f}%          "
                  f"{row['sortie_sain_d']:>7.1f}% {row['sortie_lese_g']:>7.1f}%")
            continue

        c_ent = COULEURS.get(row['couleur_deficit_entree'], '⚪')
        c_sor = COULEURS.get(row['couleur_deficit_sortie'], '⚪')
        fleche = FLECHES.get(row['couleur_progression'], '—')
        prog_str = f"{fleche} {row['progression_pct']:+.1f}%" if row['progression_pct'] is not None else "    N/A"

        print(f"  {row['mouvement']:<10} {row['metrique']:<15} "
              f"{row['entree_sain_d']:>8.1f} {row['entree_lese_g']:>8.1f} "
              f"{c_ent}{row['entree_deficit_pct']:>5.1f}%  "
              f"{row['sortie_sain_d']:>8.1f} {row['sortie_lese_g']:>8.1f} "
              f"{c_sor}{row['sortie_deficit_pct']:>5.1f}%  "
              f"{prog_str:>10}")


# ---------------------------------------------------------------------------
# 8. Validation des données extraites contre les valeurs attendues
# ---------------------------------------------------------------------------

VALEURS_ATTENDUES = {
    "entree": {
        "60_ext_moment_max": (316.9, 313.6, 1.0),
        "60_flex_moment_max": (173.0, 153.9, 11.1),
        "60_ratio_sain": 54.6,
        "60_ratio_lese": 49.1,
        "240_ext_moment_max": (225.7, 201.7, 10.6),
        "240_flex_moment_max": (123.5, 114.6, 7.2),
    },
    "sortie": {
        "60_ext_moment_max": (328.0, 333.3, -1.6),
        "60_flex_moment_max": (195.4, 162.0, 17.1),
        "60_ratio_sain": 59.6,
        "60_ratio_lese": 48.6,
        "240_ext_moment_max": (234.1, 216.9, 7.4),
        "240_flex_moment_max": (139.0, 117.7, 15.3),
    }
}

def valider_patient(patient: PatientBiodex, label: str) -> bool:
    """Valide les valeurs extraites contre les données attendues du fichier MD."""
    attendus = VALEURS_ATTENDUES.get(label, {})
    ok = True
    erreurs = []

    def check(champ, valeur, attendue, tolerance=0.2):
        nonlocal ok
        if valeur is None:
            erreurs.append(f"  ❌ {champ}: NON EXTRAIT (attendu {attendue})")
            ok = False
        elif abs(valeur - attendue) > tolerance:
            erreurs.append(f"  ❌ {champ}: {valeur} ≠ {attendue}")
            ok = False
        else:
            print(f"  ✅ {champ}: {valeur} == {attendue}")

    if patient.serie_60:
        s60 = patient.serie_60
        exp = attendus.get("60_ext_moment_max", (None, None, None))
        check("60_Ext_MomentMax_SainD", s60.ext_moment_max.sain_d, exp[0])
        check("60_Ext_MomentMax_LeseG", s60.ext_moment_max.lese_g, exp[1])
        check("60_Ext_MomentMax_Deficit", s60.ext_moment_max.deficit_pct, exp[2])
        exp = attendus.get("60_flex_moment_max", (None, None, None))
        check("60_Flex_MomentMax_SainD", s60.flex_moment_max.sain_d, exp[0])
        check("60_Flex_MomentMax_LeseG", s60.flex_moment_max.lese_g, exp[1])
        check("60_Flex_MomentMax_Deficit", s60.flex_moment_max.deficit_pct, exp[2])
        check("60_Ratio_SainD", s60.ratio_sain_d, attendus.get("60_ratio_sain"))
        check("60_Ratio_LeseG", s60.ratio_lese_g, attendus.get("60_ratio_lese"))

    if patient.serie_240:
        s240 = patient.serie_240
        exp = attendus.get("240_ext_moment_max", (None, None, None))
        check("240_Ext_MomentMax_SainD", s240.ext_moment_max.sain_d, exp[0])
        check("240_Ext_MomentMax_LeseG", s240.ext_moment_max.lese_g, exp[1])
        check("240_Ext_MomentMax_Deficit", s240.ext_moment_max.deficit_pct, exp[2])
        exp = attendus.get("240_flex_moment_max", (None, None, None))
        check("240_Flex_MomentMax_SainD", s240.flex_moment_max.sain_d, exp[0])
        check("240_Flex_MomentMax_LeseG", s240.flex_moment_max.lese_g, exp[1])
        check("240_Flex_MomentMax_Deficit", s240.flex_moment_max.deficit_pct, exp[2])

    if erreurs:
        print(f"\n  ⚠️  Erreurs de validation pour {label} :")
        for e in erreurs:
            print(e)

    return ok


# ---------------------------------------------------------------------------
# 9. MAIN — test sur N. Della Schiava
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    PDF_ENTREE = "data/TEST CONC ENTREE.pdf"
    PDF_SORTIE = "data/TEST CONC SORTIE.pdf"

    print("\n" + "█"*60)
    print("  BIODEX PARSER — ÉTAPE 1")
    print("  Patient test : N. Della Schiava")
    print("█"*60)

    # --- Parse ---
    print("\n📄 Parsing PDF Entrée...")
    entree = parse_biodex_pdf(PDF_ENTREE)
    afficher_patient(entree, "ENTRÉE")

    print("\n📄 Parsing PDF Sortie...")
    sortie = parse_biodex_pdf(PDF_SORTIE)
    afficher_patient(sortie, "SORTIE")

    # --- Comparaison ---
    print("\n📊 Calcul des progressions...")
    df_comparaison = comparer_tests(entree, sortie)
    afficher_comparaison(df_comparaison)

    # --- Validation ---
    print(f"\n{'='*60}")
    print("  VALIDATION DES DONNÉES EXTRAITES")
    print(f"{'='*60}")
    print("\n  📋 Validation ENTRÉE :")
    ok_entree = valider_patient(entree, "entree")
    print("\n  📋 Validation SORTIE :")
    ok_sortie = valider_patient(sortie, "sortie")

    if ok_entree and ok_sortie:
        print("\n  🎉 Toutes les valeurs sont correctes ! Parser opérationnel.")
    else:
        print("\n  ⚠️  Des erreurs ont été détectées — voir ci-dessus.")

    # --- Export DataFrame ---
    print(f"\n{'='*60}")
    print("  DATAFRAME STRUCTURÉ (extrait)")
    print(f"{'='*60}")
    cols = ['vitesse', 'mouvement', 'metrique', 'entree_lese_g', 'sortie_lese_g',
            'entree_deficit_pct', 'sortie_deficit_pct', 'progression_pct',
            'couleur_deficit_sortie']
    print(df_comparaison[cols].to_string(index=False))

    # Sauvegarder le CSV pour inspection
    out_path = "outputs/biodex_della_schiava.csv"
    df_comparaison.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n  💾 DataFrame exporté : {out_path}")

    print("\n✅ ÉTAPE 1 terminée.\n")