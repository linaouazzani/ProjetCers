"""
generate_rapport.py — v6
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
import platform
import base64
import re
from dataclasses import dataclass, field
from typing import Optional
from jinja2 import Environment, FileSystemLoader

from biodex_parser import parse_biodex_pdf, comparer_tests, couleur_deficit, couleur_progression
from graphiques import graphique_en_base64, generer_graphiques_progression


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
    a = abs(deficit)
    mv = mouvement.lower()
    if deficit < 0:  return f"{mv.capitalize()} — récupération complète"
    elif a <= 10:    return f"{mv.capitalize()} — dans la norme"
    elif a <= 20:    return f"{mv.capitalize()} — déficit modéré"
    else:            return f"{mv.capitalize()} — déficit important"


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

def construire_contexte(
    entree, sortie, df_comp,
    comparatif_data: dict = None,
    comparatif_sain_data: dict = None,
    nom_club: str = "—",
    logo_club_path: Optional[str] = None,
    photo_patient_path: Optional[str] = None,
    sport: str = "",
    date_naissance: str = "",
    date_operation: str = "",
    type_blessure: str = "",
    cote_opere: str = "",
    acl_rsi_score: Optional[int] = None,
    remarques_medecin: str = "",
) -> dict:

    poids        = entree.poids_kg or sortie.poids_kg or 101.0
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
        return LigneMetrique(
            entree_sain_d=e_sain_p, entree_lese_g=e_lese_p,
            sortie_sain_d=s_sain_p, sortie_lese_g=s_lese_p,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree="gray", couleur_deficit="gray",
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
        return LigneMetrique(
            entree_sain_d=e_sain, sortie_sain_d=s_sain,
            entree_lese_g=e_lese, sortie_lese_g=s_lese,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree="gray", couleur_deficit="gray",
            couleur_prog_sain=couleur_progression(ps),
            couleur_prog=couleur_progression(pl),
            interpretation=interpreter_deficit(None, mouvement),
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
        return LigneMetrique(
            entree_sain_d=e_sr, entree_lese_g=e_lr,
            sortie_sain_d=s_sr, sortie_lese_g=s_lr,
            progression_sain=ps, progression_pct=pl,
            couleur_deficit_entree="gray", couleur_deficit="gray",
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

    # Remarques
    att, pos, prog_list = [], [], []
    for _, row in df_comp.iterrows():
        if row["metrique"] == "Ratio I/Q": continue
        c = row.get("couleur_deficit_sortie", "gray")
        d = row.get("sortie_deficit_pct"); p = row.get("progression_pct")
        label = f"{row['mouvement']} {row['metrique']} ({row['vitesse']})"
        label_d = f"{label} : {d:.1f}%" if d is not None else label
        if c == "red":    att.append(f"Déficit important — {label_d}")
        elif c == "orange": att.append(f"Déficit modéré — {label_d}")
        elif c == "green" and d is not None: pos.append(f"{label} : {abs(d):.1f}%")
        if p is not None and p > 0:
            prog_list.append(f"{row['mouvement']} {row['metrique']} ({row['vitesse']}) : +{p:.1f}%")
    remarques = {
        "points_attention": [_sanitiser_emojis(p) for p in att[:5]],
        "points_positifs":  [_sanitiser_emojis(p) for p in pos[:5]],
        "progression":      [_sanitiser_emojis(p) for p in prog_list[:5]],
    }

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
    print(f"  ✅ {len(graphs_dvsg) + len(graphs_prog)} graphiques generés")
    print("  Cles graphiques:", sorted(list(graphs_dvsg.keys()) + list(graphs_prog.keys())))

    # Logos
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_cers = encoder_image(os.path.join(_base_dir, "assets", "logo_cers.png"))
    logo_club = encoder_image(logo_club_path) if logo_club_path else None
    photo     = encoder_image(photo_patient_path) if photo_patient_path else None

    # Calcul délai post-opératoire
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

    return {
        "patient": sortie, "entree": entree, "sortie": sortie,
        "s60": s60, "s240": s240,
        "serie60_meta": serie60_meta, "serie240_meta": serie240_meta,
        "remarques": remarques,
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
        },
        "logo_cers_b64":    logo_cers,
        "logo_club_b64":    logo_club,
        "photo_b64":        photo,
        "nom_club":         nom_club,
        "sport":            sport,
        "date_naissance":   date_naissance,
        "date_operation":   date_operation,
        "type_blessure":    type_blessure,
        "cote_opere":       cote_opere,
        "acl_rsi_score":    acl_rsi_score,
        "remarques_medecin": remarques_medecin,
        "delai_post_op":    delai_post_op,
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
    output_html:         str = "outputs/rapport_biodex.html",
    output_pdf:          str = "outputs/rapport_biodex.pdf",
    template_dir:        str = "templates",
    nom_club:            str = "—",
    logo_club_path:      Optional[str] = None,
    photo_patient_path:  Optional[str] = None,
    sport:               str = "",
    date_naissance:      str = "",
    date_operation:      str = "",
    type_blessure:       str = "",
    cote_opere:          str = "",
    acl_rsi_score:       Optional[int] = None,
    remarques_medecin:   str = "",
) -> str:

    print("\n" + "█" * 60)
    print("  RAPPORT BIODEX v6 — PDF avec couleurs")
    print("  Plateforme : " + platform.system())
    print("█" * 60)

    print("\n📄 Parsing PDFs...")
    entree = parse_biodex_pdf(pdf_entree)
    sortie = parse_biodex_pdf(pdf_sortie)
    print(f"  ✅ {entree.nom}  |  {entree.date_test} → {sortie.date_test}")

    comparatif_data = {}
    if pdf_comparatif and os.path.exists(pdf_comparatif):
        print("\n📋 Parsing comparatif lésé...")
        comparatif_data = parse_comparatif(pdf_comparatif)

    comparatif_sain_data = {}
    if pdf_comparatif_sain and os.path.exists(pdf_comparatif_sain):
        print("\n📋 Parsing comparatif sain...")
        comparatif_sain_data = parse_comparatif_sain(pdf_comparatif_sain)

    print("\n📊 Calcul progressions...")
    df_comp = comparer_tests(entree, sortie)
    print(f"  ✅ {len(df_comp)} métriques calculées")

    print("\n🏗️  Assemblage contexte...")
    ctx = construire_contexte(
        entree, sortie, df_comp,
        comparatif_data=comparatif_data,
        comparatif_sain_data=comparatif_sain_data,
        nom_club=nom_club,
        logo_club_path=logo_club_path,
        photo_patient_path=photo_patient_path,
        sport=sport,
        date_naissance=date_naissance,
        date_operation=date_operation,
        type_blessure=type_blessure,
        cote_opere=cote_opere,
        acl_rsi_score=acl_rsi_score,
        remarques_medecin=remarques_medecin,
    )
    print("  ✅ Contexte prêt")

    print("\n📝 Rendu HTML...")
    html = generer_html(ctx, template_dir)
    sauvegarder_html(html, output_html)

    print("\n📄 Export PDF...")
    chemin = exporter_pdf(html, output_pdf)

    print(f"\n{'=' * 60}")
    print(f"  🎉 RAPPORT GÉNÉRÉ : {chemin}")
    print(f"{'=' * 60}\n")

    return chemin


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