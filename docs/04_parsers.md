# Parsers PDF — biodex_parser.py, vald_parser.py, cr_parser.py

## biodex_parser.py

### parse_biodex_pdf(pdf_path: str) → BiodexData

Parse un PDF d'export Biodex concentrique (format isocinétique System 4).

**Retourne** `BiodexData` (dataclass) :
```python
@dataclass
class BiodexData:
    nom: str
    age: int | None
    poids_kg: float | None
    taille_cm: float | None
    sexe: str
    date_test: str           # format "DD/MM/YYYY"
    articulation: str        # ex: "Genou"
    lese: str                # "Gauche" ou "Droite"
    serie_60: SerieData | None
    serie_240: SerieData | None
    ratio_lese_g: float | None   # Ratio I/Q lésé
    ratio_sain_d: float | None   # Ratio I/Q sain

@dataclass
class SerieData:
    ext_moment_max: MesureBilat
    ext_moment_poids: MesureBilat
    ext_travail_total: MesureBilat
    ext_puissance_max: MesureBilat
    flex_moment_max: MesureBilat
    flex_moment_poids: MesureBilat
    flex_travail_total: MesureBilat
    flex_puissance_max: MesureBilat
    ratio_lese_g: float | None
    ratio_sain_d: float | None

@dataclass
class MesureBilat:
    lese_g: float | None   # côté gauche (lésé)
    sain_d: float | None   # côté droit (sain)
```

### comparer_tests(entree, sortie) → pd.DataFrame

Compare deux `BiodexData` et retourne un DataFrame avec colonnes :
```
vitesse, mouvement, metrique,
entree_sain_d, entree_lese_g, sortie_sain_d, sortie_lese_g,
entree_deficit_pct, sortie_deficit_pct, progression_pct,
couleur_deficit_sortie
```

### parse_excentrique_pdf(pdf_path: str) → dict | None

Parse un PDF excentrique 30°/s. Retourne dict plat :
```python
{
    "ext_sain", "ext_lese",           # Moment Max Extension
    "flex_sain", "flex_lese",         # Moment Max Flexion
    "ext_travail_sain", "ext_travail_lese",
    "flex_travail_sain", "flex_travail_lese",
    "ext_puissance_sain", "ext_puissance_lese",
    "flex_puissance_sain", "flex_puissance_lese",
    "ext_deficit", "flex_deficit",    # (lese-sain)/sain*100
    "ext_travail_deficit", "flex_travail_deficit",
    "ext_puissance_deficit", "flex_puissance_deficit",
    # + couleurs calculées dans generate_rapport.py :
    "ext_deficit_coul", "flex_deficit_coul", ...
}
```

### couleur_deficit(deficit_pct) → str

```python
# deficit_pct = (lese - sain) / sain * 100  (signé)
if deficit_pct is None:  return "gray"
if deficit_pct > 0:      return "navy"   # lésé plus fort = positif
a = abs(deficit_pct)
if a <= 10: return "green"
if a <= 20: return "orange"
return "red"
```

### couleur_progression(prog_pct) → str

```python
if prog_pct is None: return "gray"
if prog_pct > 0:     return "green"
return "red"
```

---

## vald_parser.py

Parser PDFs VALD ForceDecks (exportés Firefox HTML→PDF).

### Structure PDF SLJ (3 pages)

```
Page 1 : Header (date, reps, BW_kg)
Page 2 : Jump Height (Imp-Mom) (Left) [cm]
          → LEFT SIDE + RIGHT SIDE avec Range/Average/CoV/SD
Page 3 : RSI-modified (Imp-Mom) (Left) [m/s]
          → LEFT SIDE + RIGHT SIDE
```

### parse_vald_slj(pdf_source) → dict

`pdf_source` : chemin str OU `BytesIO`.

```python
{
    "slj_hauteur_g": float | None,  # Jump Height LEFT avg (cm)
    "slj_hauteur_d": float | None,  # Jump Height RIGHT avg (cm)
    "rsi_g":         float | None,  # RSI-modified LEFT avg (m/s)
    "rsi_d":         float | None,  # RSI-modified RIGHT avg (m/s)
    "date":          str | None,    # "DD/MM/YYYY"
    "bw_kg":         float | None,
    "reps":          int | None,
    "deficit_hauteur": float | None,  # |D-G|/max(D,G)*100
    "deficit_rsi":     float | None,
    "lsi_hauteur":   float | None,   # G/D*100
    "lsi_rsi":       float | None,
    "color_hauteur": str,             # "green"|"orange"|"red"|"grey"
    "color_rsi":     str,
}
```

### parse_vald_cmj(pdf_source) → dict

```python
{
    "cmj_hauteur": float | None,  # Jump Height avg (cm) bilatéral
    "cmj_rsi":     float | None,  # RSI-modified avg (m/s) — None si page absente
    "date":        str | None,
    "bw_kg":       float | None,
    "reps":        int | None,
}
```

### Formules VALD

```python
def _deficit(a, b):
    # Asymétrie absolue (pas de signe)
    return round(abs(a - b) / max(a, b) * 100, 1)

def _color(deficit):
    # Seuils Maxime
    if deficit < 10:  return "green"
    if deficit <= 15: return "orange"
    return "red"
```

---

## cr_parser.py

Parser compte-rendu médical CERS Capbreton (PDF).

### parse_compte_rendu(pdf_source) → dict

`pdf_source` : chemin str OU `BytesIO`. Jamais d'exception — retourne `_empty_result()` si erreur.

```python
{
    # Identité
    "nom_complet":          str | None,
    "date_naissance":       str | None,  # "DD/MM/YYYY"
    "sexe":                 str | None,
    "medecin_responsable":  str | None,  # ex: "GARRIGOU Pierre"

    # Contexte sportif
    "sport":  str | None,
    "club":   str | None,
    "niveau": str | None,

    # Diagnostic
    "diagnostic":        str | None,  # ex: "Rupture LCA"
    "lesions_associees": str | None,
    "cote_lese":         str | None,  # "Gauche" ou "Droite"

    # Accident & intervention
    "date_accident":      str | None,  # "DD/MM/YYYY"
    "mecanisme":          str | None,
    "intervention":       str | None,
    "date_intervention":  str | None,  # "DD/MM/YYYY"
    "gestes_associes":    str | None,
    "delai_postop_jours": int | None,  # calculé: date_entree - date_intervention

    # Séjour
    "date_entree": str | None,
    "date_sortie": str | None,

    # Clinique
    "douleur_meca_entree":  str | None,
    "perimetre_rotulien_g": str | None,
    "perimetre_rotulien_d": str | None,
    "squat_sortie":         str | None,
    "saut_sortie":          str | None,

    # Antécédents
    "antecedents": list[str],   # liste de lignes, jamais None

    # Conclusion
    "conclusion": str | None,   # max 800 caractères
}
```

### Robustesse

Deux niveaux de try/except :
1. Ouverture PDF avec pdfplumber → `_empty_result()` si erreur
2. Tout le parsing → `_empty_result()` + traceback si erreur

La fonction `find()` interne :
```python
def find(pattern, text, group=1, flags=re.IGNORECASE):
    try:
        m = re.search(pattern, text, flags)
        if m is None: return None
        val = m.group(group)
        return val.strip() if val else None
    except Exception:
        return None
```

### Utilisation dans app.py

```python
cr_data = None
if pdf_cr:
    cr_data = parse_compte_rendu(io.BytesIO(pdf_cr.getvalue()))
    # Affiché dans st.success : diagnostic, club, médecin

# Passé à generer_rapport_biodex() comme cr_data=cr_data
# Dans le contexte Jinja2 : "cr": cr_data or {}
```
