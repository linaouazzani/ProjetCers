# Base de données clubs et blessures

## clubs_database.py — Base nationale

### search_clubs(query: str) → list[dict]

Recherche dans la base nationale de clubs sportifs.

Retourne une liste de dicts :
```python
{
    "nom":      str,   # ex: "ASM Clermont"
    "sport":    str,   # ex: "Rugby"
    "division": str,   # ex: "Top 14"
    "couleur":  str,   # hex couleur dominante, ex: "#ffd700"
}
```

Utilisée dans `app.py` quand le club n'est pas trouvé dans `clubs_db.json` local.

---

## clubs_db.json — Base locale persistante

Chemin : `{APP_DIR}/clubs_db.json`

Format :
```json
{
  "nom du club en minuscules": {
    "nom":      "Nom Officiel",
    "sport":    "Rugby",
    "division": "Pro D2",
    "couleur":  "#1c3f6e",
    "logo_b64": "data:image/png;base64,..."  // optionnel
  }
}
```

### API dans app.py

```python
def charger_clubs_db() -> dict:
    # Lit clubs_db.json, retourne {} si absent

def sauvegarder_club_db(nom: str, data: dict):
    # Ajoute/met à jour clubs_db.json (clé = nom.lower().strip())
```

### Gestion logo

Le logo est stocké en base64 dans `clubs_db.json`.
À la génération, il est re-décodé et écrit dans un fichier temp :
```python
if club_selec.get("logo_b64"):
    header_part, b64_str = logo_data.split(";base64,", 1)
    ext = "png" if "png" in header_part else "jpg"
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
        f.write(base64.b64decode(b64_str))
        path_logo_club = f.name
```

### Priorité logo (dans btn_gen)

1. `logo_club_upload` (session courante) → temp file direct
2. `club_selec["logo_b64"]` (depuis clubs_db.json) → decode b64 → temp file
3. `generer_logo_svg()` → SVG avec initiales (affiché dans Streamlit uniquement)

---

## blessures_db.json — Pathologies custom

Chemin : `{APP_DIR}/blessures_db.json`

Format :
```json
{
  "custom": ["Ostéite pubienne", "Ma pathologie custom"]
}
```

### 28 pathologies par défaut (BLESSURES_DEFAULT)

```
Rupture LCA/LCP/LLE/LLI
Lésion ménisque interne/externe
Entorse cheville grade I/II/III
Rupture tendon d'Achille
Tendinopathie rotulienne/achilléenne
Fracture tibia/péroné/métatarses
Pubalgie
Lésion musculaire ischio-jambiers grade I/II/III
Lésion musculaire quadriceps grade I/II/III
Lésion musculaire adducteurs
Luxation épaule
Rupture coiffe des rotateurs
Fracture clavicule
Contusion
Autre
```

### API dans app.py

```python
def charger_blessures() -> (list, list):
    # Retourne (tous, custom)
    # tous = BLESSURES_DEFAULT + custom (sans doublons, ordre préservé)

def sauvegarder_blessure_custom(nouvelle_blessure: str):
    # Ajoute dans blessures_db.json si pas déjà présente
```

### Utilisation dans l'interface

```python
blessures_liste, _ = charger_blessures()
type_blessure = st.selectbox(
    "Type de blessure (optionnel)",
    options=["— Sélectionner —"] + blessures_liste,
    key="blessure_select"
)
# Expander pour ajouter une blessure absente de la liste :
with st.expander("➕ Blessure absente de la liste ?"):
    nouvelle_blessure = st.text_input("Nom de la blessure")
    if st.button("Ajouter à la liste"):
        sauvegarder_blessure_custom(nouvelle_blessure)
        st.rerun()
```

---

## Logo CERS

Chemin : `assets/logo_cers.png`

Encodé en base64 dans `generate_rapport.py` :
```python
logo_cers = encoder_image(os.path.join(_base_dir, "assets", "logo_cers.png"))
```

Disponible dans le template Jinja2 comme `{{ logo_cers_b64 }}`.
Affiché dans l'en-tête de chaque page (height:32px) et
en grand dans la page de garde (height:58px).
