# app.py — Interface Streamlit

## Structure générale

```
app.py
├── Imports & constantes
├── Fonctions utilitaires (clubs, blessures, logo SVG)
├── Configuration page Streamlit
├── CSS inline (hero, card, badge, club-selected...)
├── Hero banner
├── Layout 2 colonnes (col_left | col_right)
│   ├── col_left : tous les inputs
│   └── col_right : aperçu données + bouton génération
└── Footer
```

## Variables d'état session

```python
st.session_state.club_selectionne  # dict club actif
st.session_state.nom_club_cache    # str nom du club
st.session_state.rapport_bytes     # bytes du rapport généré
st.session_state.rapport_nom       # str nom fichier téléchargement
st.session_state.rapport_ext       # "pdf" ou "html"
```

## Constantes fichiers

```python
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
CLUBS_DB_PATH    = _APP_DIR / "clubs_db.json"
BLESSURES_DB_PATH = _APP_DIR / "blessures_db.json"
```

## col_left — Inputs (dans l'ordre)

### 1. Card PDFs Biodex
- `pdf_entree` : `st.file_uploader` key=`up_entree` (obligatoire)
- `pdf_sortie` : `st.file_uploader` key=`up_sortie` (obligatoire)

**Expander "PDFs optionnels"** (4 colonnes) :
- `pdf_comp` : Comparatif Lésé, key=`up_comp`
- `pdf_comp_sain` : Comparatif Sain, key=`up_comp_sain`
- `pdf_exc` : Excentrique 30°/s, key=`up_exc`
- `pdf_cr` : Compte-rendu médical, key=`up_cr`

**Badge row** (6 colonnes) : statut vert/orange/gris pour chaque PDF

### 2. Parsing compte-rendu (après la card Biodex)
```python
cr_data = None
if pdf_cr:
    cr_data = parse_compte_rendu(io.BytesIO(pdf_cr.getvalue()))
    # st.success avec diagnostic + club + médecin
```

### 3. Expander VALD ForceDecks
Variables parsées immédiatement à l'upload :
- `vald_slj_e` = `parse_vald_slj(io.BytesIO(pdf_slj_e_up.getvalue()))`
- `vald_slj_s` = `parse_vald_slj(...)`
- `vald_cmj_e` = `parse_vald_cmj(...)`
- `vald_cmj_s` = `parse_vald_cmj(...)`

### 4. Expander GPS Catapult
Placeholder — uploader CSV/XLSX non traité.

### 5. Expander Informations patient
- `sport` : selectbox (Rugby, Football, Basketball, Handball, Tennis, Natation, Athlétisme, Autre)
- `date_operation` : date_input
- `type_blessure` : selectbox depuis `charger_blessures()` + expander "Ajouter"
- `acl_rsi_score` : number_input 0-100
- `photo` : file_uploader PNG/JPG

### 6. Expander Club du joueur
Recherche locale → `clubs_db.json` → si absent, `search_clubs()` (DB nationale).
Formulaire d'ajout : nom, sport, logo → `sauvegarder_club_db()`.
Bandeau club toujours visible si `st.session_state.club_selectionne`.

## col_right — Aperçu + Génération

### Aperçu données
Parse les 2 PDFs Biodex pour afficher :
- Nom, âge, poids, taille, lésion
- Tableau préview : Moment Max, Ratio I/Q, Progression

### Bouton Génération
Erreurs bloquantes : PDF Entrée, PDF Sortie, Club.

#### Traitement logo club (priorité) :
1. `logo_club_upload` de la session → temp file
2. `club_selec["logo_b64"]` depuis clubs_db → decode base64 → temp file

#### Appel `generer_rapport_biodex()` :
```python
generer_rapport_biodex(
    pdf_entree=path_e, pdf_sortie=path_s,
    pdf_comparatif=path_comp, pdf_comparatif_sain=path_comp_sain,
    pdf_excentrique=path_exc,
    vald_slj_entree=vald_slj_e, vald_slj_sortie=vald_slj_s,
    vald_cmj_entree=vald_cmj_e, vald_cmj_sortie=vald_cmj_s,
    cr_data=cr_data,
    output_html=out_html, output_pdf=out_pdf,
    template_dir=os.path.join(_APP_DIR, "templates"),
    nom_club=nom_club, logo_club_path=path_logo_club,
    photo_patient_path=path_photo,
    sport=sport, date_naissance=..., date_operation=...,
    type_blessure=type_blessure, cote_opere=cote_opere,
    acl_rsi_score=acl_rsi_score, remarques_medecin=remarques_medecin,
)
```

Retourne le chemin du fichier `.pdf` (ou `.html` si pdfkit/WeasyPrint échoue).

## Fonctions utilitaires

```python
def charger_clubs_db() -> dict          # lit clubs_db.json
def sauvegarder_club_db(nom, data)      # écrit dans clubs_db.json
def charger_blessures() -> (list, list) # (tous, custom)
def sauvegarder_blessure_custom(str)    # ajoute dans blessures_db.json
def generer_logo_svg(nom, couleur) -> str  # SVG base64 initiales
def get_logo(nom, couleur) -> str          # cache @st.cache_data TTL=1h
```

## BLESSURES_DEFAULT (28 pathologies)

```python
["Rupture LCA", "Rupture LCP", "Rupture LLE", "Rupture LLI",
 "Lésion ménisque interne", "Lésion ménisque externe",
 "Entorse cheville grade I/II/III", "Rupture tendon d'Achille",
 "Tendinopathie rotulienne/achilléenne",
 "Fracture tibia/péroné/métatarses", "Pubalgie",
 "Lésion musculaire ischio-jambiers grade I/II/III",
 "Lésion musculaire quadriceps grade I/II/III",
 "Lésion musculaire adducteurs",
 "Luxation épaule", "Rupture coiffe des rotateurs", "Fracture clavicule",
 "Contusion", "Autre"]
```

## CSS Streamlit (classes importantes)

```css
.hero               /* banner gradient bleu CERS */
.hero-badge         /* badge rond droite */
.card               /* conteneur blanc arrondi */
.card-title         /* titre section uppercase */
.badge / .badge-ok / .badge-wait / .badge-opt
.club-selected      /* bandeau club avec logo */
.info-box           /* box info bleue gauche */
.success-box        /* box succès verte */
.preview-table      /* tableau aperçu données */
```
