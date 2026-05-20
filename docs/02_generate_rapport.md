# generate_rapport.py — Pipeline de génération PDF

## Vue d'ensemble

```
generer_rapport_biodex()
├── parse_biodex_pdf() × 2 (entrée + sortie)
├── parse_comparatif() si pdf_comparatif
├── parse_comparatif_sain() si pdf_comparatif_sain
├── parse_excentrique_pdf() si pdf_excentrique
├── comparer_tests(entree, sortie) → DataFrame
├── construire_contexte()
│   ├── calculs métriques (make_ligne, make_ratio...)
│   ├── graphiques (graphique_en_base64, progression, excentrique)
│   ├── contexte VALD (vald_ctx dict)
│   └── contexte CR (cr dict)
├── generer_html(contexte, template_dir)
└── exporter_pdf(html, output_path)
    ├── Windows : pdfkit + wkhtmltopdf
    └── Linux   : WeasyPrint
```

## Signature generer_rapport_biodex()

```python
def generer_rapport_biodex(
    pdf_entree: str,
    pdf_sortie: str,
    pdf_comparatif: Optional[str] = None,
    pdf_comparatif_sain: Optional[str] = None,
    pdf_excentrique: Optional[str] = None,
    vald_slj_entree: Optional[dict] = None,   # pré-parsé dans app.py
    vald_slj_sortie: Optional[dict] = None,
    vald_cmj_entree: Optional[dict] = None,
    vald_cmj_sortie: Optional[dict] = None,
    cr_data: Optional[dict] = None,           # pré-parsé dans app.py
    output_html: str = "outputs/rapport_biodex.html",
    output_pdf: str = "outputs/rapport_biodex.pdf",
    template_dir: str = "templates",
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
) -> str  # retourne le chemin du fichier généré
```

## Structures de données (dataclasses)

```python
@dataclass
class LigneMetrique:
    entree_sain_d, entree_lese_g         # float|None
    sortie_sain_d, sortie_lese_g         # float|None
    entree_deficit_pct, sortie_deficit_pct  # float|None
    progression_sain, progression_pct    # float|None
    couleur_deficit_entree, couleur_deficit  # "green"|"orange"|"red"|"navy"|"gray"
    couleur_prog_sain, couleur_prog      # "green"|"red"|"gray"
    interpretation: str

@dataclass
class SerieMeta:
    ratio_sain_entree, ratio_lese_entree  # float|None (Ratio I/Q)
    ratio_sain_sortie, ratio_lese_sortie
    ratio_coul_entree, ratio_coul_sortie  # str couleur
    ratio_prog, ratio_prog_couleur

@dataclass
class SerieTemplate:
    ext_moment_max, ext_moment_poids, ext_travail_total
    ext_puissance_max, ext_ratio_poids   # LigneMetrique
    flex_moment_max, flex_moment_poids, flex_travail_total
    flex_puissance_max                   # LigneMetrique
```

## construire_contexte() — Clés du contexte Jinja2

```python
{
    # Données patient
    "patient": sortie,          # BiodexData (poids, taille, nom, age...)
    "entree": entree,           # BiodexData
    "sortie": sortie,           # BiodexData

    # Tableaux isocinétiques
    "s60":  SerieTemplate,      # métriques 60°/s
    "s240": SerieTemplate,      # métriques 240°/s
    "serie60_meta":  SerieMeta,
    "serie240_meta": SerieMeta,

    # Remarques auto-générées
    "remarques": {
        "points_attention": [str, ...],  # max 5
        "points_positifs":  [str, ...],
        "progression":      [str, ...],
    },

    # Excentrique (si pdf_excentrique fourni)
    "excentrique": dict | None,
    "ratio_mixte": float | None,   # Exc Flex Lésé / Conc Ext Lésé 240°/s

    # Graphiques (base64 PNG)
    "graphiques": {
        "entree_ext_60", "sortie_ext_60",
        "entree_flex_60", "sortie_flex_60",
        "entree_ext_240", "sortie_ext_240",
        "entree_flex_240", "sortie_flex_240",
        "prog_sain_60", "prog_lese_60",
        "prog_sain_240", "prog_lese_240",
        "exc_ext", "exc_flex",
    },

    # Logos & photo
    "logo_cers_b64": str | None,   # depuis assets/logo_cers.png
    "logo_club_b64": str | None,   # depuis logo_club_path
    "photo_b64":     str | None,   # depuis photo_patient_path

    # Infos additionnelles
    "nom_club": str,
    "sport": str,
    "date_naissance": str,
    "date_operation": str,
    "type_blessure": str,
    "cote_opere": str,
    "acl_rsi_score": int | None,
    "remarques_medecin": str,
    "delai_post_op": str,          # calculé depuis date_operation vs entree.date_test

    # VALD ForceDecks
    "vald": dict | None,           # voir ci-dessous
    "has_vald": bool,

    # Compte-rendu médical
    "cr": dict,                    # cr_data or {} — jamais None
}
```

## Contexte VALD (vald_ctx)

```python
{
    # SLJ Hauteur (cm)
    "slj_eg", "slj_ed",    # entrée Gauche/Droite
    "slj_sg", "slj_sd",    # sortie Gauche/Droite
    "def_slj_e", "def_slj_s",      # déficit %
    "col_slj_e", "col_slj_s",      # "vc-g"|"vc-o"|"vc-r"|"vc-w"
    "prog_slj_g", "prog_slj_d",    # progression % entrée→sortie

    # RSI SLJ (m/s)
    "rsi_eg", "rsi_ed", "rsi_sg", "rsi_sd",
    "def_rsi_e", "def_rsi_s",
    "col_rsi_e", "col_rsi_s",
    "prog_rsi_g", "prog_rsi_d",

    # CMJ bilatéral
    "cmj_he", "cmj_hs",    # hauteur cm
    "cmj_re", "cmj_rs",    # RSI m/s (None si absent du PDF)
    "prog_cmj_h", "prog_cmj_r",

    "has_data": True,
}
```

## Couleurs déficit

```python
def couleur_deficit(deficit_pct):
    # deficit_pct = (lese - sain) / sain * 100  (signé)
    if deficit_pct is None: return "gray"
    if deficit_pct > 0:     return "navy"   # lésé plus fort
    a = abs(deficit_pct)
    if a <= 10:  return "green"
    if a <= 20:  return "orange"
    return "red"

def _vald_cls(pct):
    # pct = |D-G|/max(D,G)*100  (asymétrie absolue)
    if pct is None: return "vc-w"
    if pct < 10:    return "vc-g"
    if pct <= 15:   return "vc-o"
    return "vc-r"
```

## Export PDF

### Windows (pdfkit)
```python
wk_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
options = {'page-size': 'A4', 'margin-top': '0mm', ...}
pdfkit.from_string(html, output_path, configuration=config, options=options)
```

### Linux/Cloud (WeasyPrint)
```python
from weasyprint import HTML as WP_HTML
WP_HTML(string=html, base_url=...).write_pdf(output_path)
```

### Fallback
Si WeasyPrint échoue → sauvegarde HTML avec suffixe `_COULEURS.html`.

## Filtres Jinja2 enregistrés

```python
env.filters["fmt"] = lambda v, d=1: f"{v:.{d}f}" if v is not None else "—"
env.filters["format_ratio"] = format_ratio  # 0.65 → "0,65"
```
