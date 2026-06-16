"""
generate_rapport.py — v7
========================
Rapport Isocinétique CERS Capbreton

EXPORT PDF :
  - Windows : pdfkit + wkhtmltopdf (PDF avec couleurs)
  - Linux   : WeasyPrint (PDF avec couleurs)

INSTALLATION WINDOWS (une seule fois) :
  1. Télécharger wkhtmltopdf : https://wkhtmltopdf.org/downloads.html
     → Choisir "Windows (MSVC 2015) 64-bit"
     → Installer dans C:\\Program Files\\wkhtmltopdf\\

  2. Dans le terminal VSCode :
     pip install pdfkit

  3. Lancer l'app :
     streamlit run app.py
"""

import os
import sys
import platform
import base64
import re
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Force UTF-8 on Windows terminals (prevents cp1252 charmap crash on emojis/box chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from biodex_parser import parse_biodex_pdf, comparer_tests, couleur_deficit, couleur_progression, parse_excentrique_pdf, PatientBiodex
from graphiques import graphique_en_base64, generer_graphiques_progression, generer_graphiques_excentrique


# ════════════════════════════════════════════════════════════════
# 1. STRUCTURES DE DONNÉES
# ════════════════════════════════════════════════════════════════

@dataclass
class LigneMetrique:
    entree_sain_d:          Optional[float] = None
    entree_lese_g:          Optional[float] = None
    sortie_sain_d:          Optional[float] = None
    sortie_lese_g:          Optional[float] = None
    entree_deficit_pct:     Optional[float] = None
    sortie_deficit_pct:     Optional[float] = None
    progression_sain:       Optional[float] = None
    progression_pct:        Optional[float] = None
    couleur_deficit_entree: str = "gray"
    couleur_deficit:        str = "gray"
    couleur_prog_sain:      str = "gray"
    couleur_prog:           str = "gray"
    interpretation:         str = "—"


@dataclass
class SerieMeta:
    ratio_sain_entree:  Optional[float] = None
    ratio_lese_entree:  Optional[float] = None
    ratio_sain_sortie:  Optional[float] = None
    ratio_lese_sortie:  Optional[float] = None
    ratio_coul_entree:  str = "gray"
    ratio_coul_sortie:  str = "gray"
    ratio_prog:         Optional[float] = None
    ratio_prog_couleur: str = "gray"


@dataclass
class SerieTemplate:
    ext_moment_max:    LigneMetrique = field(default_factory=LigneMetrique)
    ext_moment_poids:  LigneMetrique = field(default_factory=LigneMetrique)
    ext_travail_total: LigneMetrique = field(default_factory=LigneMetrique)
    ext_puissance_max: LigneMetrique = field(default_factory=LigneMetrique)
    ext_ratio_poids:   LigneMetrique = field(default_factory=LigneMetrique)
    flex_moment_max:    LigneMetrique = field(default_factory=LigneMetrique)
    flex_moment_poids:  LigneMetrique = field(default_factory=LigneMetrique)
    flex_travail_total: LigneMetrique = field(default_factory=LigneMetrique)
    flex_puissance_max: LigneMetrique = field(default_factory=LigneMetrique)


# ════════════════════════════════════════════════════════════════
# 2. UTILITAIRES
# ════════════════════════════════════════════════════════════════

def calc_prog(a, b):
    if a is not None and b is not None and a != 0:
        return round(((b - a) / abs(a)) * 100, 1)
    return None


# ── Utilitaires VALD ForceDecks ──────────────────────────────────────────────

def calculer_deficit(sain, lese):
    """Retourne |sain - lese| / sain * 100, arrondi à 1 décimale. None si données manquantes."""
    if sain is None or lese is None or sain == 0:
        return None
    return round(abs(sain - lese) / sain * 100, 1)


def calculer_progression(avant, apres):
    """Retourne (apres - avant) / avant * 100, arrondi à 1 décimale. None si manquant."""
    if avant is None or apres is None or avant == 0:
        return None
    return round((apres - avant) / avant * 100, 1)


def couleur_lsi(deficit):
    """Retourne couleur hex selon seuils LSI."""
    if deficit is None:
        return "#888888"
    if deficit < 10:
        return "#27ae60"   # vert  — symétrie normale
    elif deficit <= 15:
        return "#f39c12"   # orange — déficit modéré
    else:
        return "#e74c3c"   # rouge  — déficit important


def couleur_progression_hex(prog):
    """Retourne couleur hex selon la progression (positif=vert, négatif=rouge)."""
    if prog is None:
        return "#888888"
    if prog > 0:
        return "#27ae60"
    elif prog < 0:
        return "#e74c3c"
    return "#888888"


def couleur_ratio(ratio: Optional[float]) -> str:
    if ratio is None: return "gray"
    r = ratio / 100 if ratio > 1 else ratio
    if 0.50 <= r <= 0.70:                          return "green"
    elif 0.45 <= r < 0.50 or 0.70 < r <= 0.75:    return "orange"
    return "red"


def format_ratio(value) -> str:
    if value is None: return "—"
    r = value / 100 if value > 1 else value
    return f"{r:.2f}".replace('.', ',')


def interpreter_deficit(deficit: Optional[float], mouvement: str) -> str:
    if deficit is None: return "—"
    mv = mouvement.lower()
    if deficit > 0:     return f"{mv.capitalize()} — lesé plus fort"
    a = abs(deficit)
    if a <= 10:         return f"{mv.capitalize()} — dans la norme"
    elif a <= 20:       return f"{mv.capitalize()} — déficit modéré"
    else:               return f"{mv.capitalize()} — déficit important"


def _sanitiser_emojis(texte: str) -> str:
    """Remplace les emojis non-BMP (invisibles sous WeasyPrint) par des spans HTML colorés."""
    remplacements = [
        ("🟠", '<span style="color:#e07b00;font-weight:bold;">&#9888;</span>'),
        ("✅", '<span style="color:#2a8a36;font-weight:bold;">&#10003;</span>'),
        ("📈", '<span style="color:#1c3f6e;font-weight:bold;">&#8593;</span>'),
        ("🔴", '<span style="color:#c0392b;font-weight:bold;">&#9679;</span>'),
        ("🟢", '<span style="color:#2a8a36;font-weight:bold;">&#9679;</span>'),
        ("🟡", '<span style="color:#d97000;font-weight:bold;">&#9679;</span>'),
        ("⚠️", '<span style="color:#e07b00;font-weight:bold;">&#9888;</span>'),
    ]
    for emoji, html in remplacements:
        texte = texte.replace(emoji, html)
    return texte


def encoder_image(path: str) -> Optional[str]:
    if not path or not os.path.exists(path): return None
    ext  = path.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "image/png")
    with open(path, "rb") as f:
        raw = f.read()
    if not raw: return None
    data = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{data}"


# ════════════════════════════════════════════════════════════════
# 3. PARSER COMPARATIF BIODEX
# ════════════════════════════════════════════════════════════════

def _parse_comparatif_pdf(pdf_path: str, label: str) -> dict:
    """Parse générique d'un PDF de progrès Biodex (même format lésé et sain)."""
    import pdfplumber
    result = {}

    def _nums(line):
        nums = []
        for tok in re.findall(r'-?[\d,]+(?:\.\d+)?(?:\(Rep\s*\d+\))?', line):
            clean = re.sub(r'\(Rep\s*\d+\)', '', tok).replace(',', '.').strip()
            try: nums.append(float(clean))
            except: pass
        return nums

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                vitesse = "60" if i == 0 else "240"
                data = {}
                for line in text.split('\n'):
                    ll = line.lower().replace(' ', '')
                    nums = _nums(line)
                    if 'momentmax/poids' in ll and len(nums) >= 4:
                        data['ext_moment_poids_sortie']  = nums[0]
                        data['ext_moment_poids_entree']  = nums[1]
                        data['flex_moment_poids_sortie'] = nums[2]
                        data['flex_moment_poids_entree'] = nums[3]
                    elif 'travailtotal' in ll and len(nums) >= 6:
                        data['ext_travail_total_sortie']  = nums[0]
                        data['ext_travail_total_entree']  = nums[1]
                        data['flex_travail_total_sortie'] = nums[3]
                        data['flex_travail_total_entree'] = nums[4]
                result[vitesse] = data
        print(f"  ✅ {label} parsé")
    except Exception as e:
        print(f"  ⚠️  {label} non disponible : {e}")
    return result


def parse_comparatif(pdf_path: str) -> dict:
    """Extrait Travail Total Lésé depuis le PDF comparatif Lésé Biodex."""
    return _parse_comparatif_pdf(pdf_path, "Comparatif lésé")


def parse_comparatif_sain(pdf_path: str) -> dict:
    """Extrait Travail Total Sain depuis le PDF comparatif Sain Biodex."""
    return _parse_comparatif_pdf(pdf_path, "Comparatif sain")


# ════════════════════════════════════════════════════════════════
# 4. CONSTRUCTION DU CONTEXTE JINJA2
# ════════════════════════════════════════════════════════════════

def _generer_conclusion_auto(remarques, entree, sortie) -> str:
    """Génère un paragraphe de synthèse de progression à partir des données Biodex."""
    lignes = []

    # Lignes de progression positives depuis remarques
    for p in (remarques or {}).get("progression", [])[:6]:
        lignes.append(p)

    # Compléter avec des valeurs numériques si disponibles
    try:
        e60 = entree.serie_60
        s60p = sortie.serie_60
        if e60 and s60p:
            for attr, label in [
                ("ext_moment_max", "Extension 60°/s Moment Max"),
                ("flex_moment_max", "Flexion 60°/s Moment Max"),
            ]:
                e_val = getattr(getattr(e60, attr, None), "lese_g", None)
                s_val = getattr(getattr(s60p, attr, None), "lese_g", None)
                if e_val and s_val and e_val != 0:
                    p = round((s_val - e_val) / abs(e_val) * 100, 1)
                    if abs(p) >= 3:
                        signe = "+" if p >= 0 else ""
                        msg = f"{label} (Lésé) : {e_val:.0f} → {s_val:.0f} N·m ({signe}{p:.1f}%)"
                        if msg not in lignes:
                            lignes.append(msg)
    except Exception:
        pass

    try:
        e240 = entree.serie_240
        s240p = sortie.serie_240
        if e240 and s240p:
            for attr, label in [
                ("ext_moment_max", "Extension 240°/s Moment Max"),
                ("flex_moment_max", "Flexion 240°/s Moment Max"),
            ]:
                e_val = getattr(getattr(e240, attr, None), "lese_g", None)
                s_val = getattr(getattr(s240p, attr, None), "lese_g", None)
                if e_val and s_val and e_val != 0:
                    p = round((s_val - e_val) / abs(e_val) * 100, 1)
                    if abs(p) >= 3:
                        signe = "+" if p >= 0 else ""
                        msg = f"{label} (Lésé) : {e_val:.0f} → {s_val:.0f} N·m ({signe}{p:.1f}%)"
                        if msg not in lignes:
                            lignes.append(msg)
    except Exception:
        pass

    if not lignes:
        return ""
    return " · ".join(lignes[:8])


def _generer_remarques_vitesse(serie_e, serie_s, vitesse_label: str) -> dict:
    """Génère les remarques clés (déficits, progressions) pour une vitesse donnée."""
    attention, positif = [], []
    if serie_e is None or serie_s is None:
        return {"attention": [], "positif": [], "vitesse": vitesse_label}
    for attr, label in [
        ("ext_moment_max",    "Ext. Moment Max"),
        ("flex_moment_max",   "Flex. Moment Max"),
        ("ext_puissance_max", "Ext. Puissance"),
        ("flex_puissance_max","Flex. Puissance"),
    ]:
        try:
            lese_s = getattr(getattr(serie_s, attr, None), "lese_g", None)
            sain_s = getattr(getattr(serie_s, attr, None), "sain_d", None)
            lese_e = getattr(getattr(serie_e, attr, None), "lese_g", None)
            if lese_s and sain_s and sain_s != 0:
                deficit = (lese_s - sain_s) / abs(sain_s) * 100
                if deficit < -15:
                    attention.append(f"{label} : déficit {abs(deficit):.1f}% (L={lese_s:.0f} vs S={sain_s:.0f} N·m)")
                elif -10 <= deficit <= 5 and lese_s > 0:
                    positif.append(f"{label} : symétrie {abs(deficit):.1f}%")
            if lese_e and lese_s and lese_e != 0:
                prog = (lese_s - lese_e) / abs(lese_e) * 100
                if prog >= 5:
                    positif.append(f"{label} lésé : +{prog:.1f}% ({lese_e:.0f}→{lese_s:.0f} N·m)")
        except Exception:
            pass
    return {"attention": attention[:3], "positif": positif[:3], "vitesse": vitesse_label}


def construire_contexte(
    entree, sortie, df_comp,
    comparatif_data: dict = None,
    comparatif_sain_data: dict = None,
    nom_club: str = "—",
    logo_club_path: Optional[str] = None,
    logo_club_b64_direct: Optional[str] = None,
    photo_patient_path: Optional[str] = None,
    sport: str = "",
    date_naissance: str = "",
    date_operation: str = "",
    type_blessure: str = "",
    cote_opere: str = "",
    acl_rsi_score: Optional[int] = None,
    remarques_medecin: str = "",
    excentrique_data=None,
    slj_entree_data=None,
    slj_sortie_data=None,
    cmj_entree_data=None,
    cmj_sortie_data=None,
    vald_entree=None,
    vald_sortie=None,
    slj_data=None,
    cmj_data=None,
    cr_data: Optional[dict] = None,
    titre_rapport: str = "",
    notes_seance: str = "",
    diagnostic_override: str = "",
    intervention_override: str = "",
    resume_override: str = "",
    include_excentrique: bool = True,
    include_vald: bool = True,
    include_progression: bool = True,
    programme_kine: str = "",
    programme_prepa: str = "",
    conclusion_sortie: str = "",
    gps_data: dict = None,
    vald_manual: dict = None,
    has_biodex: bool = True,
    nom_prenom: str = "",
    poids_override: Optional[float] = None,
    taille_cm: Optional[float] = None,
    date_entree_cers: str = "",
    date_sortie_cers: str = "",
    medecin_responsable: str = "",
    cote_sain: str = "",
    delai_postop_override: str = "",
) -> dict:

    poids          = entree.poids_kg or sortie.poids_kg or 101.0
    _poids_display = poids_override if poids_override is not None else poids
    _nom_patient   = (nom_prenom
                      or getattr(sortie, 'nom', None)
                      or getattr(entree, 'nom', None)
                      or "—")

    def _calc_def(sain, lese):
        """Calcule le déficit (lese-sain)/sain*100 si les deux valeurs sont disponibles."""
        if sain and lese and sain != 0:
            return round((lese - sain) / sain * 100, 1)
        return None

    comp60       = (comparatif_data      or {}).get("60",  {})
    comp240      = (comparatif_data      or {}).get("240", {})
    comp60_sain  = (comparatif_sain_data or {}).get("60",  {})
    comp240_sain = (comparatif_sain_data or {}).get("240", {})

    def get_row(vitesse, mouvement, metrique):
        mask = ((df_comp["vitesse"] == vitesse) &
                (df_comp["mouvement"] == mouvement) &
                (df_comp["metrique"] == metrique))
        rows = df_comp[mask]
        return rows.iloc[0].to_dict() if not rows.empty else {}

    def make_ligne(vitesse, mouvement, metrique) -> LigneMetrique:
        r = get_row(vitesse, mouvement, metrique)
        if not r: return LigneMetrique()
        de = r.get("entree_deficit_pct")
        ds = r.get("sortie_deficit_pct")
        pl = r.get("progression_pct")
        ps = calc_prog(r.get("entree_sain_d"), r.get("sortie_sain_d"))
        return LigneMetrique(
            entree_sain_d=r.get("entree_sain_d"),
            entree_lese_g=r.get("entree_lese_g"),
            sortie_sain_d=r.get("sortie_sain_d"),
            sortie_lese_g=r.get("sortie_lese_g"),
            entree_deficit_pct=de, sortie_deficit_pct=ds,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree=couleur_deficit(de),
            couleur_deficit=couleur_deficit(ds),
            couleur_prog_sain=couleur_progression(ps),
            couleur_prog=couleur_progression(pl),
            interpretation=interpreter_deficit(ds, mouvement),
        )

    def make_ligne_moment_poids_sain(serie_e, serie_s, mouvement: str) -> LigneMetrique:
        attr = 'ext_moment_max' if mouvement == "Extension" else 'flex_moment_max'
        e_sain = getattr(getattr(serie_e, attr, None), 'sain_d', None)
        s_sain = getattr(getattr(serie_s, attr, None), 'sain_d', None)
        e_lese = getattr(getattr(serie_e, attr, None), 'lese_g', None)
        s_lese = getattr(getattr(serie_s, attr, None), 'lese_g', None)
        e_sain_p = round(e_sain / poids * 100, 1) if e_sain else None
        s_sain_p = round(s_sain / poids * 100, 1) if s_sain else None
        e_lese_p = round(e_lese / poids * 100, 1) if e_lese else None
        s_lese_p = round(s_lese / poids * 100, 1) if s_lese else None
        ps = calc_prog(e_sain_p, s_sain_p)
        pl = calc_prog(e_lese_p, s_lese_p)
        e_def = _calc_def(e_sain_p, e_lese_p)
        s_def = _calc_def(s_sain_p, s_lese_p)
        return LigneMetrique(
            entree_sain_d=e_sain_p, entree_lese_g=e_lese_p,
            sortie_sain_d=s_sain_p, sortie_lese_g=s_lese_p,
            entree_deficit_pct=e_def, sortie_deficit_pct=s_def,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree=couleur_deficit(e_def),
            couleur_deficit=couleur_deficit(s_def),
            couleur_prog_sain=couleur_progression(ps),
            couleur_prog=couleur_progression(pl),
            interpretation="Moment normalisé au poids",
        )

    def make_ligne_travail_total(comp: dict, comp_sain: dict, cle: str, mouvement: str, serie_e=None, serie_s=None) -> LigneMetrique:
        attr = f"{cle}_travail_total"
        e_lese = comp.get(f"{cle}_travail_total_entree")
        s_lese = comp.get(f"{cle}_travail_total_sortie")
        e_sain = comp_sain.get(f"{cle}_travail_total_entree") if comp_sain else None
        s_sain = comp_sain.get(f"{cle}_travail_total_sortie") if comp_sain else None
        # Fallback depuis les PDFs individuels si comparatif absent
        if serie_e:
            m = getattr(serie_e, attr, None)
            if m and m.lese_g is not None and e_lese is None: e_lese = m.lese_g
            if m and m.sain_d is not None and e_sain is None: e_sain = m.sain_d
        if serie_s:
            m = getattr(serie_s, attr, None)
            if m and m.lese_g is not None and s_lese is None: s_lese = m.lese_g
            if m and m.sain_d is not None and s_sain is None: s_sain = m.sain_d
        pl = calc_prog(e_lese, s_lese)
        ps = calc_prog(e_sain, s_sain)
        e_def = _calc_def(e_sain, e_lese)
        s_def = _calc_def(s_sain, s_lese)
        return LigneMetrique(
            entree_sain_d=e_sain, sortie_sain_d=s_sain,
            entree_lese_g=e_lese, sortie_lese_g=s_lese,
            entree_deficit_pct=e_def, sortie_deficit_pct=s_def,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree=couleur_deficit(e_def),
            couleur_deficit=couleur_deficit(s_def),
            couleur_prog_sain=couleur_progression(ps),
            couleur_prog=couleur_progression(pl),
            interpretation=interpreter_deficit(s_def, mouvement),
        )

    def make_ratio_poids(serie_e, serie_s, mouvement: str) -> LigneMetrique:
        attr = 'ext_moment_max' if mouvement == "Extension" else 'flex_moment_max'
        es = getattr(getattr(serie_e, attr, None), 'sain_d', None)
        ss = getattr(getattr(serie_s, attr, None), 'sain_d', None)
        el = getattr(getattr(serie_e, attr, None), 'lese_g', None)
        sl = getattr(getattr(serie_s, attr, None), 'lese_g', None)
        to_r = lambda v: round(v / poids, 2) if v else None
        e_sr = to_r(es); s_sr = to_r(ss); e_lr = to_r(el); s_lr = to_r(sl)
        ps = calc_prog(e_sr, s_sr); pl = calc_prog(e_lr, s_lr)
        e_def = _calc_def(e_sr, e_lr)
        s_def = _calc_def(s_sr, s_lr)
        return LigneMetrique(
            entree_sain_d=e_sr, entree_lese_g=e_lr,
            sortie_sain_d=s_sr, sortie_lese_g=s_lr,
            entree_deficit_pct=e_def, sortie_deficit_pct=s_def,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree=couleur_deficit(e_def),
            couleur_deficit=couleur_deficit(s_def),
            couleur_prog_sain=couleur_progression(ps),
            couleur_prog=couleur_progression(pl),
            interpretation="Moment max / poids (N·m/kg)",
        )

    e60 = entree.serie_60;   s60p = sortie.serie_60
    e240 = entree.serie_240; s240p = sortie.serie_240

    s60 = SerieTemplate(
        ext_moment_max    = make_ligne("60°/s", "Extension", "Moment Max"),
        ext_moment_poids  = make_ligne_moment_poids_sain(e60, s60p, "Extension"),
        ext_travail_total = make_ligne_travail_total(comp60, comp60_sain, "ext", "Extension", e60, s60p),
        ext_puissance_max = make_ligne("60°/s", "Extension", "Puissance Max"),
        ext_ratio_poids   = make_ratio_poids(e60, s60p, "Extension"),
        flex_moment_max    = make_ligne("60°/s", "Flexion", "Moment Max"),
        flex_moment_poids  = make_ligne_moment_poids_sain(e60, s60p, "Flexion"),
        flex_travail_total = make_ligne_travail_total(comp60, comp60_sain, "flex", "Flexion", e60, s60p),
        flex_puissance_max = make_ligne("60°/s", "Flexion", "Puissance Max"),
    )
    s240 = SerieTemplate(
        ext_moment_max    = make_ligne("240°/s", "Extension", "Moment Max"),
        ext_moment_poids  = make_ligne_moment_poids_sain(e240, s240p, "Extension"),
        ext_travail_total = make_ligne_travail_total(comp240, comp240_sain, "ext", "Extension", e240, s240p),
        ext_puissance_max = make_ligne("240°/s", "Extension", "Puissance Max"),
        ext_ratio_poids   = make_ratio_poids(e240, s240p, "Extension"),
        flex_moment_max    = make_ligne("240°/s", "Flexion", "Moment Max"),
        flex_moment_poids  = make_ligne_moment_poids_sain(e240, s240p, "Flexion"),
        flex_travail_total = make_ligne_travail_total(comp240, comp240_sain, "flex", "Flexion", e240, s240p),
        flex_puissance_max = make_ligne("240°/s", "Flexion", "Puissance Max"),
    )

    def serie_meta(se, ss) -> SerieMeta:
        re_s = getattr(se, 'ratio_sain_d', None) if se else None
        re_l = getattr(se, 'ratio_lese_g', None) if se else None
        rs_s = getattr(ss, 'ratio_sain_d', None) if ss else None
        rs_l = getattr(ss, 'ratio_lese_g', None) if ss else None
        prog = calc_prog(re_l, rs_l)
        return SerieMeta(
            ratio_sain_entree=re_s, ratio_lese_entree=re_l,
            ratio_sain_sortie=rs_s, ratio_lese_sortie=rs_l,
            ratio_coul_entree=couleur_ratio(re_l),
            ratio_coul_sortie=couleur_ratio(rs_l),
            ratio_prog=prog, ratio_prog_couleur=couleur_progression(prog),
        )

    serie60_meta  = serie_meta(e60,  s60p)
    serie240_meta = serie_meta(e240, s240p)

    # Remarques — attention + progression
    att, prog_list = [], []
    for _, row in df_comp.iterrows():
        if row["metrique"] == "Ratio I/Q": continue
        c = row.get("couleur_deficit_sortie", "gray")
        d = row.get("sortie_deficit_pct"); p = row.get("progression_pct")
        label = f"{row['mouvement']} {row['metrique']} ({row['vitesse']})"
        label_d = f"{label} : {d:.1f}%" if d is not None else label
        if c == "red":    att.append(f"Déficit important — {label_d}")
        elif c == "orange": att.append(f"Déficit modéré — {label_d}")
        if p is not None and p > 0:
            prog_list.append(f"{row['mouvement']} {row['metrique']} ({row['vitesse']}) : +{p:.1f}%")

    # Points satisfaisants : déficit sortie < 10% OU déficit entrée < 10% si pas de sortie
    pos = []
    for _, row in df_comp.iterrows():
        if row["metrique"] == "Ratio I/Q":
            continue
        ds = row.get("sortie_deficit_pct")
        if ds is not None and ds > -10:
            label = f"{row['mouvement']} {row['metrique']} ({row['vitesse']})"
            pos.append(f"{label} : {ds:.1f}%")
        elif ds is None:
            de = row.get("entree_deficit_pct")
            if de is not None and de > -10:
                label = f"{row['mouvement']} {row['metrique']}"
                pos.append(f"{label} : {de:.1f}%")

    remarques = {
        "points_attention": [_sanitiser_emojis(p) for p in att[:5]],
        "points_positifs":  [_sanitiser_emojis(p) for p in pos[:5]],
        "progression":      [_sanitiser_emojis(p) for p in prog_list[:5]],
    }

    # Contexte excentrique (doit être construit AVANT la génération des graphiques)
    # excentrique_data est maintenant un dict plat retourné par parse_excentrique_pdf()
    exc_ctx = None
    ratio_mixte = None
    if excentrique_data:
        exc_ctx = dict(excentrique_data)
        # Ajouter les couleurs pré-calculées pour le template
        for _fld in ['ext_deficit', 'flex_deficit',
                     'ext_travail_deficit', 'flex_travail_deficit',
                     'ext_puissance_deficit', 'flex_puissance_deficit']:
            exc_ctx[_fld + '_coul'] = couleur_deficit(exc_ctx.get(_fld))
        # Ratio mixte : Exc Flex Lésé / Conc Ext Lésé 240°/s (sortie)
        try:
            exc_fl = exc_ctx.get('flex_lese')
            con_el = s240p.ext_moment_max.lese_g if s240p else None
            if exc_fl and con_el and con_el != 0:
                ratio_mixte = round(exc_fl / con_el, 2)
        except Exception:
            pass
    print("DEBUG exc_ctx:", exc_ctx)
    print("DEBUG ratio_mixte:", ratio_mixte)

    # Graphiques
    print("  🖼️  Génération des 12 graphiques...")
    graphs_dvsg = {
        "entree_ext":      graphique_en_base64("entree_60_ext",   entree, "ext"),
        "sortie_ext":      graphique_en_base64("sortie_60_ext",   sortie, "ext"),
        "entree_flex":     graphique_en_base64("entree_60_flex",  entree, "flex"),
        "sortie_flex":     graphique_en_base64("sortie_60_flex",  sortie, "flex"),
        "entree_ext_240":  graphique_en_base64("entree_240_ext",  entree, "ext"),
        "sortie_ext_240":  graphique_en_base64("sortie_240_ext",  sortie, "ext"),
        "entree_flex_240": graphique_en_base64("entree_240_flex", entree, "flex"),
        "sortie_flex_240": graphique_en_base64("sortie_240_flex", sortie, "flex"),
    }
    def _v(serie, attr, subattr, default):
        """Acces securise a serie.attr.subattr avec fallback."""
        try:
            v = getattr(getattr(serie, attr, None), subattr, None)
            return v if v else default
        except Exception:
            return default

    params_e60 = {
        'ext':  {'sain': {'moment_max': _v(e60, 'ext_moment_max', 'sain_d',  316.9), 'angle': 81, 'amplitude': 99},
                 'lese': {'moment_max': _v(e60, 'ext_moment_max', 'lese_g',  313.6), 'angle': 70, 'amplitude': 101}},
        'flex': {'sain': {'moment_max': _v(e60, 'flex_moment_max', 'sain_d', 173.0), 'angle': 33, 'amplitude': 99},
                 'lese': {'moment_max': _v(e60, 'flex_moment_max', 'lese_g', 153.9), 'angle': 29, 'amplitude': 101}},
    }
    params_s60 = {
        'ext':  {'sain': {'moment_max': _v(s60p, 'ext_moment_max', 'sain_d',  328.0), 'angle': 68, 'amplitude': 88},
                 'lese': {'moment_max': _v(s60p, 'ext_moment_max', 'lese_g',  333.3), 'angle': 66, 'amplitude': 92}},
        'flex': {'sain': {'moment_max': _v(s60p, 'flex_moment_max', 'sain_d', 195.4), 'angle': 32, 'amplitude': 88},
                 'lese': {'moment_max': _v(s60p, 'flex_moment_max', 'lese_g', 162.0), 'angle': 27, 'amplitude': 92}},
    }
    params_e240 = {
        'ext':  {'sain': {'moment_max': _v(e240, 'ext_moment_max', 'sain_d',  200.0), 'angle': 56, 'amplitude': 99},
                 'lese': {'moment_max': _v(e240, 'ext_moment_max', 'lese_g',  195.0), 'angle': 54, 'amplitude': 101}},
        'flex': {'sain': {'moment_max': _v(e240, 'flex_moment_max', 'sain_d', 120.0), 'angle': 29, 'amplitude': 99},
                 'lese': {'moment_max': _v(e240, 'flex_moment_max', 'lese_g', 110.0), 'angle': 27, 'amplitude': 101}},
    }
    params_s240 = {
        'ext':  {'sain': {'moment_max': _v(s240p, 'ext_moment_max', 'sain_d',  210.0), 'angle': 56, 'amplitude': 88},
                 'lese': {'moment_max': _v(s240p, 'ext_moment_max', 'lese_g',  205.0), 'angle': 54, 'amplitude': 92}},
        'flex': {'sain': {'moment_max': _v(s240p, 'flex_moment_max', 'sain_d', 130.0), 'angle': 29, 'amplitude': 88},
                 'lese': {'moment_max': _v(s240p, 'flex_moment_max', 'lese_g', 120.0), 'angle': 27, 'amplitude': 92}},
    }
    graphs_prog = generer_graphiques_progression(params_e60, params_s60, params_e240, params_s240)
    graphs_exc  = generer_graphiques_excentrique(exc_ctx) if exc_ctx else {}
    print(f"  ✅ {len(graphs_dvsg) + len(graphs_prog) + len(graphs_exc)} graphiques generés")
    print("  Cles graphiques:", sorted(list(graphs_dvsg.keys()) + list(graphs_prog.keys())))

    # Logos
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_cers = encoder_image(os.path.join(_base_dir, "assets", "logo_cers.png"))
    # Priorité : data URI directe (depuis DB/JS, sans fichier temporaire) > fichier uploadé
    logo_club = logo_club_b64_direct or (encoder_image(logo_club_path) if logo_club_path else None)
    photo     = encoder_image(photo_patient_path) if photo_patient_path else None

    # Calcul délai post-opératoire (auto si date_operation fournie)
    delai_post_op = ""
    if date_operation:
        try:
            from datetime import datetime
            d_op = datetime.strptime(date_operation, "%Y-%m-%d")
            d_test = datetime.strptime(entree.date_test, "%d/%m/%Y")
            delta = (d_test - d_op).days
            if delta >= 0:
                delai_post_op = f"{delta} jours"
        except Exception:
            pass
    # Override manuel si renseigné
    if delai_postop_override:
        delai_post_op = delai_postop_override

    print("DEBUG ctx excentrique:", exc_ctx)

    # Contexte VALD ForceDecks
    def _prog_vald(data_e, data_s, key):
        if data_e and data_s and data_e.get(key) and data_s.get(key):
            e, s = data_e[key], data_s[key]
            if e != 0:
                return round((s - e) / abs(e) * 100, 1)
        return None

    # ── Compat : construire les dicts entrée/sortie séparés depuis le nouveau format ──
    # parse_slj_pdf() retourne {slj_hauteur_g_ent, slj_hauteur_g_sort, …}
    # On reconstruit des dicts "entrée" et "sortie" compatibles avec l'ancien code.
    slj_e = slj_entree_data
    slj_s = slj_sortie_data
    cmj_e = cmj_entree_data
    cmj_s = cmj_sortie_data

    if slj_data and not slj_e:
        _dh_e = calculer_deficit(slj_data.get("slj_hauteur_d_ent"), slj_data.get("slj_hauteur_g_ent"))
        _dr_e = calculer_deficit(slj_data.get("rsi_d_ent"),         slj_data.get("rsi_g_ent"))
        slj_e = {
            "slj_hauteur_g": slj_data.get("slj_hauteur_g_ent"),
            "slj_hauteur_d": slj_data.get("slj_hauteur_d_ent"),
            "rsi_g":         slj_data.get("rsi_g_ent"),
            "rsi_d":         slj_data.get("rsi_d_ent"),
            "deficit_hauteur": _dh_e,
            "deficit_rsi":     _dr_e,
        }
        _dh_s = calculer_deficit(slj_data.get("slj_hauteur_d_sort"), slj_data.get("slj_hauteur_g_sort"))
        _dr_s = calculer_deficit(slj_data.get("rsi_d_sort"),          slj_data.get("rsi_g_sort"))
        slj_s = {
            "slj_hauteur_g": slj_data.get("slj_hauteur_g_sort"),
            "slj_hauteur_d": slj_data.get("slj_hauteur_d_sort"),
            "rsi_g":         slj_data.get("rsi_g_sort"),
            "rsi_d":         slj_data.get("rsi_d_sort"),
            "deficit_hauteur": _dh_s,
            "deficit_rsi":     _dr_s,
        }

    if cmj_data and not cmj_e:
        cmj_e = {"cmj_hauteur": cmj_data.get("cmj_hauteur_ent"), "cmj_rsi": None}
        cmj_s = {"cmj_hauteur": cmj_data.get("cmj_hauteur_sort"), "cmj_rsi": None}

    def _vald_cls(pct):
        if pct is None: return "vc-w"
        if pct < 10:    return "vc-g"
        if pct <= 15:   return "vc-o"
        return "vc-r"

    vald_ctx = None
    if slj_e or slj_s or cmj_e or cmj_s:
        _def_slj_e = slj_e["deficit_hauteur"] if slj_e else None
        _def_slj_s = slj_s["deficit_hauteur"] if slj_s else None
        _def_rsi_e = slj_e["deficit_rsi"] if slj_e else None
        _def_rsi_s = slj_s["deficit_rsi"] if slj_s else None
        vald_ctx = {
            # SLJ Hauteur
            "slj_eg":     slj_e["slj_hauteur_g"] if slj_e else None,
            "slj_ed":     slj_e["slj_hauteur_d"] if slj_e else None,
            "slj_sg":     slj_s["slj_hauteur_g"] if slj_s else None,
            "slj_sd":     slj_s["slj_hauteur_d"] if slj_s else None,
            "def_slj_e":  _def_slj_e,
            "def_slj_s":  _def_slj_s,
            "col_slj_e":  _vald_cls(_def_slj_e),
            "col_slj_s":  _vald_cls(_def_slj_s),
            "prog_slj_g": _prog_vald(slj_e, slj_s, "slj_hauteur_g"),
            "prog_slj_d": _prog_vald(slj_e, slj_s, "slj_hauteur_d"),
            # RSI SLJ
            "rsi_eg":     slj_e["rsi_g"] if slj_e else None,
            "rsi_ed":     slj_e["rsi_d"] if slj_e else None,
            "rsi_sg":     slj_s["rsi_g"] if slj_s else None,
            "rsi_sd":     slj_s["rsi_d"] if slj_s else None,
            "def_rsi_e":  _def_rsi_e,
            "def_rsi_s":  _def_rsi_s,
            "col_rsi_e":  _vald_cls(_def_rsi_e),
            "col_rsi_s":  _vald_cls(_def_rsi_s),
            "prog_rsi_g": _prog_vald(slj_e, slj_s, "rsi_g"),
            "prog_rsi_d": _prog_vald(slj_e, slj_s, "rsi_d"),
            # CMJ bilatéral
            "cmj_he":     cmj_e["cmj_hauteur"] if cmj_e else None,
            "cmj_hs":     cmj_s["cmj_hauteur"] if cmj_s else None,
            "cmj_re":     cmj_e["cmj_rsi"] if cmj_e else None,
            "cmj_rs":     cmj_s["cmj_rsi"] if cmj_s else None,
            "prog_cmj_h": _prog_vald(cmj_e, cmj_s, "cmj_hauteur"),
            "prog_cmj_r": _prog_vald(cmj_e, cmj_s, "cmj_rsi"),
            "has_data":   True,
        }

    has_vald = bool(vald_ctx)

    # ── vald_tableau : tableau clinique complet (page dédiée) ────────────────────
    # Priorité 1 : nouveau format slj_data/cmj_data (parse_slj_pdf + parse_cmj_pdf)
    # Priorité 2 : ancien format vald_entree/vald_sortie (parse_vald_pdf)
    # Priorité 3 : anciens dicts séparés slj_entree_data/cmj_entree_data (legacy)

    vald_tableau = None

    if slj_data or cmj_data:
        # ── Nouveau format : les clés contiennent déjà _ent / _sort ──
        _slj = slj_data or {}
        _cmj = cmj_data or {}

        slj_hg_e = _slj.get("slj_hauteur_g_ent")
        slj_hd_e = _slj.get("slj_hauteur_d_ent")
        slj_hg_s = _slj.get("slj_hauteur_g_sort")
        slj_hd_s = _slj.get("slj_hauteur_d_sort")
        def_slj_e = calculer_deficit(slj_hd_e, slj_hg_e)   # sain=D, lésé=G
        def_slj_s = calculer_deficit(slj_hd_s, slj_hg_s)

        rsi_g_e = _slj.get("rsi_g_ent")
        rsi_d_e = _slj.get("rsi_d_ent")
        rsi_g_s = _slj.get("rsi_g_sort")
        rsi_d_s = _slj.get("rsi_d_sort")
        def_rsi_e = calculer_deficit(rsi_d_e, rsi_g_e)
        def_rsi_s = calculer_deficit(rsi_d_s, rsi_g_s)

        cmj_h_e = _cmj.get("cmj_hauteur_ent")
        cmj_h_s = _cmj.get("cmj_hauteur_sort")
        cmj_r_e = None  # RSI CMJ non disponible dans le nouveau parser
        cmj_r_s = None

        # ── Helper : largeur barre (% relatif au max des 2 valeurs) ──
        def _bw(a, b):
            """Retourne (pct_a, pct_b) pour barres horizontales relatives."""
            if a is None or b is None:
                return None, None
            ma = max(abs(a), abs(b))
            if ma == 0:
                return 50, 50
            return round(abs(a) / ma * 100), round(abs(b) / ma * 100)

        # ── Helper : largeur barre 4 valeurs — proportionnelles au max global ──
        def _bw4(a, b, c, d, scale=80):
            """Retourne (pct_a, pct_b, pct_c, pct_d) relatives au max de toutes les valeurs.
            scale = largeur max en % du conteneur (default 80)."""
            vals = [v for v in [a, b, c, d] if v is not None]
            if not vals:
                return None, None, None, None
            m = max(abs(v) for v in vals)
            if m == 0:
                return (round(scale/2),) * 4
            def _p(v):
                return round(abs(v) / m * scale) if v is not None else None
            return _p(a), _p(b), _p(c), _p(d)

        # ── Helper : largeur barre 2 valeurs ──
        def _bw2(a, b, scale=80):
            vals = [v for v in [a, b] if v is not None]
            if not vals:
                return None, None
            m = max(abs(v) for v in vals)
            if m == 0:
                return round(scale/2), round(scale/2)
            def _p(v):
                return round(abs(v) / m * scale) if v is not None else None
            return _p(a), _p(b)

        _slj_hg_bw_e, _slj_hd_bw_e = _bw(slj_hg_e, slj_hd_e)
        _slj_hg_bw_s, _slj_hd_bw_s = _bw(slj_hg_s, slj_hd_s)
        _rsi_g_bw_e,  _rsi_d_bw_e  = _bw(rsi_g_e,  rsi_d_e)
        _rsi_g_bw_s,  _rsi_d_bw_s  = _bw(rsi_g_s,  rsi_d_s)
        _flt_g_bw_e,  _flt_d_bw_e  = _bw(_slj.get("slj_flight_g_ent"), _slj.get("slj_flight_d_ent"))
        _flt_g_bw_s,  _flt_d_bw_s  = _bw(_slj.get("slj_flight_g_sort"), _slj.get("slj_flight_d_sort"))
        _cmj_h_bw_e,  _cmj_h_bw_s  = _bw(cmj_h_e, cmj_h_s)

        # ── Barres 4 valeurs — proportionnelles à toutes les sessions ──
        _b4_slj_ge, _b4_slj_de, _b4_slj_gs, _b4_slj_ds = _bw4(slj_hg_e, slj_hd_e, slj_hg_s, slj_hd_s)
        _b4_rsi_ge, _b4_rsi_de, _b4_rsi_gs, _b4_rsi_ds = _bw4(rsi_g_e, rsi_d_e, rsi_g_s, rsi_d_s)
        _flt_ge = _slj.get("slj_flight_g_ent");  _flt_de = _slj.get("slj_flight_d_ent")
        _flt_gs = _slj.get("slj_flight_g_sort"); _flt_ds = _slj.get("slj_flight_d_sort")
        _b4_flt_ge, _b4_flt_de, _b4_flt_gs, _b4_flt_ds = _bw4(_flt_ge, _flt_de, _flt_gs, _flt_ds)
        _b2_cmj_e, _b2_cmj_s = _bw2(cmj_h_e, cmj_h_s)

        # is_single_session : pas de date_sortie dans le PDF → 1 seule session
        _is_single = (_slj.get("date_sortie") is None and _cmj.get("date_sortie") is None)

        vald_tableau = {
            # SLJ Hauteur (G=Lésé, D=Sain)
            "slj_hauteur_g_ent":       slj_hg_e,
            "slj_hauteur_d_ent":       slj_hd_e,
            "slj_hauteur_g_sort":      slj_hg_s,
            "slj_hauteur_d_sort":      slj_hd_s,
            "def_slj_haut_ent":        def_slj_e,
            "def_slj_haut_sort":       def_slj_s,
            "prog_slj_haut_g":         calculer_progression(slj_hg_e, slj_hg_s),
            "prog_slj_haut_d":         calculer_progression(slj_hd_e, slj_hd_s),
            "color_def_slj_haut_ent":  couleur_lsi(def_slj_e),
            "color_def_slj_haut_sort": couleur_lsi(def_slj_s),
            "bar_slj_g_ent": _slj_hg_bw_e, "bar_slj_d_ent": _slj_hd_bw_e,
            "bar_slj_g_sort": _slj_hg_bw_s, "bar_slj_d_sort": _slj_hd_bw_s,
            # SLJ barres 4-valeurs (proportionnelles au max de toutes les sessions)
            "b4_slj_ge": _b4_slj_ge, "b4_slj_de": _b4_slj_de,
            "b4_slj_gs": _b4_slj_gs, "b4_slj_ds": _b4_slj_ds,
            # RSI SLJ
            "rsi_g_ent":               rsi_g_e,
            "rsi_d_ent":               rsi_d_e,
            "rsi_g_sort":              rsi_g_s,
            "rsi_d_sort":              rsi_d_s,
            "def_rsi_ent":             def_rsi_e,
            "def_rsi_sort":            def_rsi_s,
            "prog_rsi_g":              calculer_progression(rsi_g_e, rsi_g_s),
            "prog_rsi_d":              calculer_progression(rsi_d_e, rsi_d_s),
            "color_def_rsi_ent":       couleur_lsi(def_rsi_e),
            "color_def_rsi_sort":      couleur_lsi(def_rsi_s),
            "bar_rsi_g_ent": _rsi_g_bw_e, "bar_rsi_d_ent": _rsi_d_bw_e,
            "bar_rsi_g_sort": _rsi_g_bw_s, "bar_rsi_d_sort": _rsi_d_bw_s,
            # RSI barres 4-valeurs
            "b4_rsi_ge": _b4_rsi_ge, "b4_rsi_de": _b4_rsi_de,
            "b4_rsi_gs": _b4_rsi_gs, "b4_rsi_ds": _b4_rsi_ds,
            # Flight Time SLJ
            "slj_flight_g_ent":        _flt_ge,
            "slj_flight_g_sort":       _flt_gs,
            "slj_flight_d_ent":        _flt_de,
            "slj_flight_d_sort":       _flt_ds,
            "def_flight_ent":          calculer_deficit(_flt_de, _flt_ge),
            "def_flight_sort":         calculer_deficit(_flt_ds, _flt_gs),
            "prog_flight_g":           calculer_progression(_flt_ge, _flt_gs),
            "prog_flight_d":           calculer_progression(_flt_de, _flt_ds),
            "color_def_flight_ent":    couleur_lsi(calculer_deficit(_flt_de, _flt_ge)),
            "color_def_flight_sort":   couleur_lsi(calculer_deficit(_flt_ds, _flt_gs)),
            "bar_flt_g_ent": _flt_g_bw_e, "bar_flt_d_ent": _flt_d_bw_e,
            "bar_flt_g_sort": _flt_g_bw_s, "bar_flt_d_sort": _flt_d_bw_s,
            # Flight Time barres 4-valeurs
            "b4_flt_ge": _b4_flt_ge, "b4_flt_de": _b4_flt_de,
            "b4_flt_gs": _b4_flt_gs, "b4_flt_ds": _b4_flt_ds,
            # Peak Force Asymmetry SLJ
            "peak_force_asym_ent":     _slj.get("peak_force_asym_ent"),
            "peak_force_asym_sort":    _slj.get("peak_force_asym_sort"),
            # CMJ bilatéral — hauteur
            "cmj_hauteur_ent":         cmj_h_e,
            "cmj_hauteur_sort":        cmj_h_s,
            "cmj_rsi_ent":             cmj_r_e,
            "cmj_rsi_sort":            cmj_r_s,
            "prog_cmj_haut":           calculer_progression(cmj_h_e, cmj_h_s),
            "prog_cmj_rsi":            None,
            "bar_cmj_e": _cmj_h_bw_e, "bar_cmj_s": _cmj_h_bw_s,
            # CMJ barres 2-valeurs (proportionnelles aux 2 sessions)
            "b2_cmj_e": _b2_cmj_e, "b2_cmj_s": _b2_cmj_s,
            # CMJ — asymétrie force concentrique
            "cmj_conc_asym_ent":       _cmj.get("cmj_conc_asym_ent"),
            "cmj_conc_asym_sort":      _cmj.get("cmj_conc_asym_sort"),
            "cmj_conc_asym_side_ent":  _cmj.get("cmj_conc_asym_side_ent"),
            "cmj_conc_asym_side_sort": _cmj.get("cmj_conc_asym_side_sort"),
            "prog_cmj_conc_asym":      calculer_progression(
                                           _cmj.get("cmj_conc_asym_ent"),
                                           _cmj.get("cmj_conc_asym_sort")),
            # CMJ — landing asymmetry
            "cmj_landing_asym_ent":    _cmj.get("cmj_landing_asym_ent"),
            "cmj_landing_asym_sort":   _cmj.get("cmj_landing_asym_sort"),
            "cmj_landing_side_ent":    _cmj.get("cmj_landing_side_ent"),
            "cmj_landing_side_sort":   _cmj.get("cmj_landing_side_sort"),
            "prog_cmj_landing_asym":   calculer_progression(
                                           _cmj.get("cmj_landing_asym_ent"),
                                           _cmj.get("cmj_landing_asym_sort")),
            # CMJ — vitesse excentrique
            "cmj_ecc_vel_ent":         _cmj.get("cmj_ecc_vel_ent"),
            "cmj_ecc_vel_sort":        _cmj.get("cmj_ecc_vel_sort"),
            "prog_cmj_ecc_vel":        calculer_progression(
                                           _cmj.get("cmj_ecc_vel_ent"),
                                           _cmj.get("cmj_ecc_vel_sort")),
            # CMJ — RFD
            "cmj_rfd_ent":             _cmj.get("cmj_rfd_ent"),
            "cmj_rfd_sort":            _cmj.get("cmj_rfd_sort"),
            "prog_cmj_rfd":            calculer_progression(
                                           _cmj.get("cmj_rfd_ent"),
                                           _cmj.get("cmj_rfd_sort")),
            # Méta
            "date_entree":             _slj.get("date_entree") or _cmj.get("date_entree"),
            "date_sortie":             _slj.get("date_sortie") or _cmj.get("date_sortie"),
            "is_single_session":       _is_single,
        }

    else:
        # ── Fallback ancien format (vald_entree/vald_sortie ou dicts séparés) ──
        _ve = dict(vald_entree) if vald_entree else {}
        _vs = dict(vald_sortie) if vald_sortie else {}
        if not _ve:
            if slj_entree_data:
                _ve.update({k: v for k, v in slj_entree_data.items() if k not in _ve})
            if cmj_entree_data:
                _ve.update({k: v for k, v in cmj_entree_data.items() if k not in _ve})
        if not _vs:
            if slj_sortie_data:
                _vs.update({k: v for k, v in slj_sortie_data.items() if k not in _vs})
            if cmj_sortie_data:
                _vs.update({k: v for k, v in cmj_sortie_data.items() if k not in _vs})

        if _ve or _vs:
            slj_hg_e = _ve.get("slj_hauteur_g")
            slj_hd_e = _ve.get("slj_hauteur_d")
            slj_hg_s = _vs.get("slj_hauteur_g")
            slj_hd_s = _vs.get("slj_hauteur_d")
            def_slj_e = calculer_deficit(slj_hd_e, slj_hg_e)
            def_slj_s = calculer_deficit(slj_hd_s, slj_hg_s)

            rsi_g_e = _ve.get("rsi_g"); rsi_d_e = _ve.get("rsi_d")
            rsi_g_s = _vs.get("rsi_g"); rsi_d_s = _vs.get("rsi_d")
            def_rsi_e = calculer_deficit(rsi_d_e, rsi_g_e)
            def_rsi_s = calculer_deficit(rsi_d_s, rsi_g_s)

            cmj_h_e = _ve.get("cmj_hauteur"); cmj_h_s = _vs.get("cmj_hauteur")
            cmj_r_e = _ve.get("cmj_rsi");     cmj_r_s = _vs.get("cmj_rsi")

            # Détecte si on a des données sortie (pour is_single_session)
            _has_sortie = any(v is not None for v in [slj_hg_s, slj_hd_s, rsi_g_s, rsi_d_s, cmj_h_s])

            # Barres de largeur relative (None si données manquantes)
            def _bw_fb(a, b):
                if a is None or b is None: return None, None
                ma = max(abs(a), abs(b))
                if ma == 0: return 50, 50
                return round(abs(a) / ma * 100), round(abs(b) / ma * 100)

            def _bw4_fb(a, b, c, d, scale=80):
                vals = [v for v in [a, b, c, d] if v is not None]
                if not vals: return None, None, None, None
                m = max(abs(v) for v in vals)
                if m == 0: return (round(scale/2),) * 4
                def _p(v): return round(abs(v) / m * scale) if v is not None else None
                return _p(a), _p(b), _p(c), _p(d)

            def _bw2_fb(a, b, scale=80):
                vals = [v for v in [a, b] if v is not None]
                if not vals: return None, None
                m = max(abs(v) for v in vals)
                if m == 0: return round(scale/2), round(scale/2)
                def _p(v): return round(abs(v) / m * scale) if v is not None else None
                return _p(a), _p(b)

            _slj_hg_bw_e, _slj_hd_bw_e = _bw_fb(slj_hg_e, slj_hd_e)
            _slj_hg_bw_s, _slj_hd_bw_s = _bw_fb(slj_hg_s, slj_hd_s)
            _rsi_g_bw_e,  _rsi_d_bw_e  = _bw_fb(rsi_g_e,  rsi_d_e)
            _rsi_g_bw_s,  _rsi_d_bw_s  = _bw_fb(rsi_g_s,  rsi_d_s)
            _cmj_h_bw_e,  _cmj_h_bw_s  = _bw_fb(cmj_h_e,  cmj_h_s)
            _fb_slj_ge, _fb_slj_de, _fb_slj_gs, _fb_slj_ds = _bw4_fb(slj_hg_e, slj_hd_e, slj_hg_s, slj_hd_s)
            _fb_rsi_ge, _fb_rsi_de, _fb_rsi_gs, _fb_rsi_ds = _bw4_fb(rsi_g_e, rsi_d_e, rsi_g_s, rsi_d_s)
            _fb_cmj_e, _fb_cmj_s = _bw2_fb(cmj_h_e, cmj_h_s)

            vald_tableau = {
                # SLJ Hauteur
                "slj_hauteur_g_ent":       slj_hg_e,
                "slj_hauteur_d_ent":       slj_hd_e,
                "slj_hauteur_g_sort":      slj_hg_s,
                "slj_hauteur_d_sort":      slj_hd_s,
                "def_slj_haut_ent":        def_slj_e,
                "def_slj_haut_sort":       def_slj_s,
                "prog_slj_haut_g":         calculer_progression(slj_hg_e, slj_hg_s),
                "prog_slj_haut_d":         calculer_progression(slj_hd_e, slj_hd_s),
                "color_def_slj_haut_ent":  couleur_lsi(def_slj_e),
                "color_def_slj_haut_sort": couleur_lsi(def_slj_s),
                "bar_slj_g_ent": _slj_hg_bw_e, "bar_slj_d_ent": _slj_hd_bw_e,
                "bar_slj_g_sort": _slj_hg_bw_s, "bar_slj_d_sort": _slj_hd_bw_s,
                # SLJ barres 4-valeurs
                "b4_slj_ge": _fb_slj_ge, "b4_slj_de": _fb_slj_de,
                "b4_slj_gs": _fb_slj_gs, "b4_slj_ds": _fb_slj_ds,
                # RSI SLJ
                "rsi_g_ent":               rsi_g_e, "rsi_d_ent":    rsi_d_e,
                "rsi_g_sort":              rsi_g_s, "rsi_d_sort":   rsi_d_s,
                "def_rsi_ent":             def_rsi_e, "def_rsi_sort": def_rsi_s,
                "prog_rsi_g":              calculer_progression(rsi_g_e, rsi_g_s),
                "prog_rsi_d":              calculer_progression(rsi_d_e, rsi_d_s),
                "color_def_rsi_ent":       couleur_lsi(def_rsi_e),
                "color_def_rsi_sort":      couleur_lsi(def_rsi_s),
                "bar_rsi_g_ent": _rsi_g_bw_e, "bar_rsi_d_ent": _rsi_d_bw_e,
                "bar_rsi_g_sort": _rsi_g_bw_s, "bar_rsi_d_sort": _rsi_d_bw_s,
                # RSI barres 4-valeurs
                "b4_rsi_ge": _fb_rsi_ge, "b4_rsi_de": _fb_rsi_de,
                "b4_rsi_gs": _fb_rsi_gs, "b4_rsi_ds": _fb_rsi_ds,
                # Flight Time SLJ (non disponible ancien format)
                "slj_flight_g_ent":        None, "slj_flight_g_sort": None,
                "slj_flight_d_ent":        None, "slj_flight_d_sort": None,
                "def_flight_ent":          None, "def_flight_sort":   None,
                "prog_flight_g":           None, "prog_flight_d":     None,
                "color_def_flight_ent":    "#888888", "color_def_flight_sort": "#888888",
                "bar_flt_g_ent":           None, "bar_flt_d_ent":  None,
                "bar_flt_g_sort":          None, "bar_flt_d_sort": None,
                # Flight Time barres 4-valeurs (toutes None ancien format)
                "b4_flt_ge": None, "b4_flt_de": None,
                "b4_flt_gs": None, "b4_flt_ds": None,
                # Peak Force Asymmetry SLJ
                "peak_force_asym_ent":     None, "peak_force_asym_sort": None,
                # CMJ bilatéral
                "cmj_hauteur_ent":         cmj_h_e, "cmj_hauteur_sort": cmj_h_s,
                "cmj_rsi_ent":             cmj_r_e, "cmj_rsi_sort":    cmj_r_s,
                "prog_cmj_haut":           calculer_progression(cmj_h_e, cmj_h_s),
                "prog_cmj_rsi":            calculer_progression(cmj_r_e, cmj_r_s),
                "bar_cmj_e": _cmj_h_bw_e, "bar_cmj_s": _cmj_h_bw_s,
                # CMJ barres 2-valeurs
                "b2_cmj_e": _fb_cmj_e, "b2_cmj_s": _fb_cmj_s,
                # CMJ asymétries (non disponibles ancien format)
                "cmj_conc_asym_ent":       None, "cmj_conc_asym_sort":      None,
                "cmj_conc_asym_side_ent":  None, "cmj_conc_asym_side_sort": None,
                "cmj_landing_asym_ent":    None, "cmj_landing_asym_sort":   None,
                "cmj_landing_side_ent":    None, "cmj_landing_side_sort":   None,
                "cmj_ecc_vel_ent":         None, "cmj_ecc_vel_sort":        None,
                "cmj_rfd_ent":             None, "cmj_rfd_sort":            None,
                # Progressions CMJ
                "prog_cmj_conc_asym":      None,
                "prog_cmj_landing_asym":   None,
                "prog_cmj_ecc_vel":        None,
                "prog_cmj_rfd":            None,
                # Méta
                "date_entree": None, "date_sortie": None,
                "is_single_session": not _has_sortie,
            }

    # ── Remarques par vitesse (calculées avant le return pour all_progressions) ──
    rem60_data  = _generer_remarques_vitesse(e60,  s60p,  "60°/s")
    rem240_data = _generer_remarques_vitesse(e240, s240p, "240°/s")

    # ── all_progressions : construit depuis toutes les sources disponibles
    #    Visible sur page de garde même sans comparatifs ni sortie ────────
    all_progressions = []

    # Source 1 : df_comp (progressions calculées entrée→sortie, valeur brute > 0)
    if df_comp is not None and not df_comp.empty:
        for _, row in df_comp.iterrows():
            if row.get("metrique") == "Ratio I/Q":
                continue
            p = row.get("progression_pct")
            if p is not None and p > 0:
                label = f"{row['mouvement']} {row['metrique']} ({row['vitesse']})"
                all_progressions.append(f"{label} : +{p:.1f}%")

    # Source 2 : remarques.progression (déjà calculé ci-dessus)
    if not all_progressions and remarques:
        all_progressions.extend(remarques.get("progression", []))

    # Source 3 : points_positifs (déficits faibles = points satisfaisants)
    if not all_progressions and remarques:
        all_progressions.extend(remarques.get("points_positifs", [])[:3])

    # Source 4 : déficits d'entrée dans la norme si aucune autre source disponible
    if not all_progressions and df_comp is not None and not df_comp.empty:
        for _, row in df_comp.iterrows():
            d = row.get("entree_deficit_pct")
            if d is not None and d > -10:
                label = f"{row['mouvement']} {row['metrique']}"
                all_progressions.append(f"{label} : dans la norme ({d:.1f}%)")
                if len(all_progressions) >= 3:
                    break

    all_progressions = [_sanitiser_emojis(p) for p in all_progressions[:8]]

    return {
        "patient": sortie, "entree": entree, "sortie": sortie,
        "s60": s60, "s240": s240,
        "serie60_meta": serie60_meta, "serie240_meta": serie240_meta,
        "remarques": remarques,
        "excentrique": exc_ctx,
        "ratio_mixte": ratio_mixte,
        "graphiques": {
            "entree_ext_60":  graphs_dvsg.get("entree_ext", ""),
            "sortie_ext_60":  graphs_dvsg.get("sortie_ext", ""),
            "entree_flex_60": graphs_dvsg.get("entree_flex", ""),
            "sortie_flex_60": graphs_dvsg.get("sortie_flex", ""),
            "entree_ext_240":  graphs_dvsg.get("entree_ext_240", ""),
            "sortie_ext_240":  graphs_dvsg.get("sortie_ext_240", ""),
            "entree_flex_240": graphs_dvsg.get("entree_flex_240", ""),
            "sortie_flex_240": graphs_dvsg.get("sortie_flex_240", ""),
            "prog_sain_60":  graphs_prog.get("prog_sain_60", ""),
            "prog_lese_60":  graphs_prog.get("prog_lese_60", ""),
            "prog_sain_240": graphs_prog.get("prog_sain_240", ""),
            "prog_lese_240": graphs_prog.get("prog_lese_240", ""),
            "exc_ext":  graphs_exc.get("exc_ext", ""),
            "exc_flex": graphs_exc.get("exc_flex", ""),
        },
        "logo_cers_b64":    logo_cers,
        "logo_club_b64":    logo_club,
        "photo_b64":        photo,
        "nom_club":         nom_club,
        "sport":            sport,
        # ── Identité patient (manual overrides > auto-parsed) ──────────
        "nom_patient":           _nom_patient,
        "poids_kg":              _poids_display,
        "taille_cm":             taille_cm,
        "date_naissance":        date_naissance,
        "date_entree_cers":      date_entree_cers,
        "date_sortie_cers":      date_sortie_cers,
        "medecin_responsable":   medecin_responsable,
        "cote_sain":             cote_sain,
        # ── Champs existants ───────────────────────────────────────────
        "date_operation":   date_operation,
        "type_blessure":    type_blessure,
        "cote_opere":       cote_opere,
        "acl_rsi_score":    acl_rsi_score,
        "remarques_medecin": remarques_medecin,
        "delai_post_op":    delai_post_op,
        "vald":             vald_ctx,
        "has_vald":         has_vald,
        "vald_tableau":     vald_tableau,
        "cr":               cr_data or {},
        "conclusion_auto":  _generer_conclusion_auto(remarques, entree, sortie),
        "remarques_60":     rem60_data,
        "remarques_240":    rem240_data,
        "all_progressions": all_progressions,
        "titre_rapport":    titre_rapport or "Bilan Complet du Patient",
        "notes_seance":     notes_seance,
        "diagnostic_override":    diagnostic_override,
        "intervention_override":  intervention_override,
        "resume_override":        resume_override,
        "include_excentrique":    include_excentrique,
        "include_vald":           include_vald,
        "include_progression":    include_progression,
        "programme_kine":         programme_kine,
        "programme_prepa":        programme_prepa,
        "conclusion_sortie":      conclusion_sortie,
        "gps":                    gps_data,
        "vald_manual":            vald_manual,
        "has_biodex":             has_biodex,
    }


# ════════════════════════════════════════════════════════════════
# 5. RENDU HTML
# ════════════════════════════════════════════════════════════════

def generer_html(contexte: dict, template_dir: str = "templates") -> str:
    if not os.path.isabs(template_dir):
        base = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(base, template_dir)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    env.filters["fmt"] = lambda v, d=1: f"{v:.{d}f}" if v is not None else "—"
    env.filters["format_ratio"] = format_ratio
    env.filters["truncate40"] = lambda v: (v[:40] + "…") if v and len(v) > 40 else (v or "—")
    env.filters["couleur_progression"] = lambda prog: (
        "#27ae60" if prog is not None and prog > 0 else
        "#e74c3c" if prog is not None and prog < 0 else
        "#888888"
    )
    env.filters["abs"] = lambda v: abs(v) if v is not None else None
    env.filters["signe"] = lambda v: "+" if v is not None and v > 0 else ""
    env.filters["side_label"] = lambda s: (
        "D (droite)" if s in ("R", "D") else
        "G (gauche)" if s in ("L", "G") else (s or "—")
    )
    # bar_pct(a, b) → largeur % de a relativement au max(|a|,|b|)
    def _bar_pct(a, b):
        if a is None or b is None:
            return 0
        ma = max(abs(a), abs(b))
        return round(abs(a) / ma * 100) if ma != 0 else 50
    env.globals["bar_pct"] = _bar_pct
    return env.get_template("rapport.html").render(**contexte)


def sauvegarder_html(html: str, path: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(html)
    print(f"  💾 HTML : {path}")


# ════════════════════════════════════════════════════════════════
# 6. EXPORT PDF — Windows (pdfkit) + Linux (WeasyPrint)
# ════════════════════════════════════════════════════════════════

def exporter_pdf(html: str, output_path: str) -> str:
    """Génère le PDF — Windows: pdfkit, Linux: WeasyPrint"""
    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True
    )

    if platform.system() == "Windows":
        try:
            import pdfkit
            wk_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if not os.path.exists(wk_path):
                raise FileNotFoundError(f"wkhtmltopdf non trouvé : {wk_path}")

            config = pdfkit.configuration(wkhtmltopdf=wk_path)
            options = {
                'page-size':                'A4',
                'margin-top':               '0mm',
                'margin-bottom':            '0mm',
                'margin-left':              '0mm',
                'margin-right':             '0mm',
                'encoding':                 'UTF-8',
                'enable-local-file-access': None,
                'quiet':                    None,
                'no-outline':               None,
            }
            pdfkit.from_string(
                html, output_path,
                configuration=config,
                options=options,
                verbose=False,
            )
            print(f"  ✅ PDF généré : {output_path}")
            return output_path

        except Exception as e:
            print(f"  ⚠️  pdfkit erreur : {e}")
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            return html_path
    else:
        try:
            from weasyprint import HTML as WP_HTML
            WP_HTML(string=html, base_url=os.path.dirname(os.path.abspath(output_path))).write_pdf(output_path)
            print(f"  ✅ PDF : {output_path}")
            return output_path
        except Exception as e:
            print(f"  ⚠️  WeasyPrint erreur : {e}")
            return _fallback_html(html, output_path)


def _fallback_html(html: str, output_path: str) -> str:
    """Fallback : sauvegarde le HTML si le PDF échoue."""
    html_path = output_path.replace(".pdf", "_COULEURS.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  💾 Fallback HTML sauvegardé : {html_path}")
    print(f"  👉 Ouvre dans Chrome → Ctrl+P → Enregistrer en PDF")
    return html_path


# ════════════════════════════════════════════════════════════════
# 7. PIPELINE PRINCIPAL
# ════════════════════════════════════════════════════════════════

def generer_rapport_biodex(
    pdf_entree:          str,
    pdf_sortie:          str,
    pdf_comparatif:      Optional[str] = None,
    pdf_comparatif_sain: Optional[str] = None,
    pdf_excentrique:     Optional[str] = None,
    vald_slj_entree:     Optional[dict] = None,
    vald_slj_sortie:     Optional[dict] = None,
    vald_cmj_entree:     Optional[dict] = None,
    vald_cmj_sortie:     Optional[dict] = None,
    vald_entree:         Optional[dict] = None,
    vald_sortie:         Optional[dict] = None,
    slj_data:            Optional[dict] = None,
    cmj_data:            Optional[dict] = None,
    cr_data:             Optional[dict] = None,
    output_html:         str = "outputs/rapport_biodex.html",
    output_pdf:              str = "outputs/rapport_biodex.pdf",
    template_dir:            str = "templates",
    nom_club:                str = "—",
    logo_club_path:          Optional[str] = None,
    logo_club_b64_direct:    Optional[str] = None,
    photo_patient_path:      Optional[str] = None,
    sport:                   str = "",
    date_naissance:          str = "",
    date_operation:          str = "",
    type_blessure:           str = "",
    cote_opere:              str = "",
    acl_rsi_score:           Optional[int] = None,
    remarques_medecin:       str = "",
    titre_rapport:           str = "",
    notes_seance:            str = "",
    diagnostic_override:     str = "",
    intervention_override:   str = "",
    resume_override:         str = "",
    include_excentrique:     bool = True,
    include_vald:            bool = True,
    include_progression:     bool = True,
    programme_kine:          str = "",
    programme_prepa:         str = "",
    conclusion_sortie:       str = "",
    gps_data:                dict = None,
    vald_manual:             dict = None,
    nom_prenom:              str = "",
    poids_override:          Optional[float] = None,
    taille_cm:               Optional[float] = None,
    date_entree_cers:        str = "",
    date_sortie_cers:        str = "",
    medecin_responsable:     str = "",
    cote_sain:               str = "",
    delai_postop_override:   str = "",
) -> dict:

    print("\n" + "=" * 60)
    print("  RAPPORT BIODEX v6 — PDF avec couleurs")
    print("  Plateforme : " + platform.system())
    print("=" * 60)

    # ── Parsing PDFs Biodex (tous optionnels) ──────────────────────────────
    has_biodex = bool(pdf_entree or pdf_sortie)

    _EMPTY_COLS = [
        "vitesse", "mouvement", "metrique", "unite",
        "entree_sain_d", "entree_lese_g", "entree_deficit_pct",
        "sortie_sain_d", "sortie_lese_g", "sortie_deficit_pct",
        "progression_pct", "couleur_progression",
        "couleur_deficit_entree", "couleur_deficit_sortie",
    ]

    if not pdf_entree and not pdf_sortie:
        print("  ℹ️  Aucun PDF Biodex — rapport sans données isocinétiques")
        entree = PatientBiodex(nom="—", date_test="—")
        sortie = PatientBiodex(nom="—", date_test="—")
        df_comp = pd.DataFrame(columns=_EMPTY_COLS)
    else:
        if not pdf_entree:
            pdf_entree = pdf_sortie
            print("  ⚠️  PDF Entrée absent — utilisation du PDF Sortie comme référence")
        elif not pdf_sortie:
            pdf_sortie = pdf_entree
            print("  ⚠️  PDF Sortie absent — utilisation du PDF Entrée comme référence")

        print("\n📄 Parsing PDFs...")
        entree = parse_biodex_pdf(pdf_entree)
        sortie = parse_biodex_pdf(pdf_sortie)
        print(f"  ✅ {entree.nom}  |  {entree.date_test} → {sortie.date_test}")

        print("\n📊 Calcul progressions...")
        df_comp = comparer_tests(entree, sortie)
        print(f"  ✅ {len(df_comp)} métriques calculées")

    comparatif_data = {}
    if pdf_comparatif and os.path.exists(pdf_comparatif):
        print("\n📋 Parsing comparatif lésé...")
        comparatif_data = parse_comparatif(pdf_comparatif)

    comparatif_sain_data = {}
    if pdf_comparatif_sain and os.path.exists(pdf_comparatif_sain):
        print("\n📋 Parsing comparatif sain...")
        comparatif_sain_data = parse_comparatif_sain(pdf_comparatif_sain)

    excentrique_data = None
    if pdf_excentrique and os.path.exists(pdf_excentrique):
        print("\n📋 Parsing test excentrique...")
        excentrique_data = parse_excentrique_pdf(pdf_excentrique)

    print("\n🏗️  Assemblage contexte...")
    ctx = construire_contexte(
        entree, sortie, df_comp,
        has_biodex=has_biodex,
        comparatif_data=comparatif_data,
        comparatif_sain_data=comparatif_sain_data,
        nom_club=nom_club,
        logo_club_path=logo_club_path,
        logo_club_b64_direct=logo_club_b64_direct,
        photo_patient_path=photo_patient_path,
        sport=sport,
        date_naissance=date_naissance,
        date_operation=date_operation,
        type_blessure=type_blessure,
        cote_opere=cote_opere,
        acl_rsi_score=acl_rsi_score,
        remarques_medecin=remarques_medecin,
        excentrique_data=excentrique_data,
        slj_entree_data=vald_slj_entree,
        slj_sortie_data=vald_slj_sortie,
        cmj_entree_data=vald_cmj_entree,
        cmj_sortie_data=vald_cmj_sortie,
        vald_entree=vald_entree,
        vald_sortie=vald_sortie,
        slj_data=slj_data,
        cmj_data=cmj_data,
        cr_data=cr_data,
        titre_rapport=titre_rapport,
        notes_seance=notes_seance,
        diagnostic_override=diagnostic_override,
        intervention_override=intervention_override,
        resume_override=resume_override,
        include_excentrique=include_excentrique,
        include_vald=include_vald,
        include_progression=include_progression,
        programme_kine=programme_kine,
        programme_prepa=programme_prepa,
        conclusion_sortie=conclusion_sortie,
        gps_data=gps_data,
        vald_manual=vald_manual,
        nom_prenom=nom_prenom,
        poids_override=poids_override,
        taille_cm=taille_cm,
        date_entree_cers=date_entree_cers,
        date_sortie_cers=date_sortie_cers,
        medecin_responsable=medecin_responsable,
        cote_sain=cote_sain,
        delai_postop_override=delai_postop_override,
    )
    print("  ✅ Contexte prêt")

    print("\n📝 Rendu HTML...")
    html = generer_html(ctx, template_dir)
    sauvegarder_html(html, output_html)

    print("\n📄 Export PDF...")
    html_bytes = html.encode("utf-8")
    chemin_pdf = exporter_pdf(html, output_pdf)

    pdf_bytes = None
    if chemin_pdf and chemin_pdf.endswith(".pdf") and os.path.exists(chemin_pdf):
        with open(chemin_pdf, "rb") as f:
            pdf_bytes = f.read()

    print(f"\n{'=' * 60}")
    print(f"  🎉 RAPPORT GÉNÉRÉ — PDF: {'oui' if pdf_bytes else 'non'}")
    print(f"{'=' * 60}\n")

    return {
        "html":       html,
        "html_bytes": html_bytes,
        "pdf_path":   chemin_pdf,
        "pdf_bytes":  pdf_bytes,
    }


# ════════════════════════════════════════════════════════════════
# MAIN — test direct
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    generer_rapport_biodex(
        pdf_entree     = "data/TEST CONC ENTREE.pdf",
        pdf_sortie     = "data/TEST CONC SORTIE.pdf",
        pdf_comparatif = "data/COMPARATIF_LESE.pdf",
        output_html    = "outputs/rapport_biodex.html",
        output_pdf     = "outputs/rapport_biodex.pdf",
        template_dir   = "templates",
        nom_club       = "ASM Clermont",
        sport          = "Rugby",
    )