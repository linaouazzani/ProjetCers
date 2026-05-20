# graphiques.py — Génération des graphiques

## Vue d'ensemble

Toutes les fonctions retournent des images encodées en base64 PNG,
prêtes à être insérées dans le HTML via `src="data:image/png;base64,..."`.

Paramètre commun : `dpi=150` (Matplotlib, backend Agg).

## graphique_en_base64(label, biodex_data, mouvement) → str

Génère une courbe isocinétique D vs G (moment en fonction de l'angle).

Paramètres :
- `label` : str identifiant (ex: `"entree_60_ext"`, `"sortie_240_flex"`)
- `biodex_data` : `BiodexData` (entrée ou sortie)
- `mouvement` : `"ext"` ou `"flex"`

La courbe utilise les données simulées depuis les moments max et amplitudes.
Couleurs : `#1c3f6e` (sain D) et `#c0392b` (lésé G).

## generer_graphiques_progression(params_e60, params_s60, params_e240, params_s240) → dict

Génère 4 graphiques de progression (barres comparatives entrée/sortie) :

```python
{
    "prog_sain_60":  str,   # base64 PNG
    "prog_lese_60":  str,
    "prog_sain_240": str,
    "prog_lese_240": str,
}
```

Chaque `params_*` est un dict de forme :
```python
{
    'ext': {
        'sain': {'moment_max': float, 'angle': int, 'amplitude': int},
        'lese': {'moment_max': float, 'angle': int, 'amplitude': int},
    },
    'flex': { ... }
}
```

## generer_graphiques_excentrique(exc_ctx) → dict

Génère 2 graphiques excentrique si `exc_ctx` est fourni :

```python
{
    "exc_ext":  str,  # base64 PNG — Extension excentrique D vs G
    "exc_flex": str,  # base64 PNG — Flexion excentrique D vs G
}
```

`exc_ctx` : dict retourné par `parse_excentrique_pdf()` avec champs
`ext_sain`, `ext_lese`, `flex_sain`, `flex_lese`, etc.

## Utilisation dans generate_rapport.py

```python
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
graphs_prog = generer_graphiques_progression(
    params_e60, params_s60, params_e240, params_s240
)
graphs_exc = generer_graphiques_excentrique(exc_ctx) if exc_ctx else {}
```

Les clés du contexte Jinja2 `graphiques` mappent :
```python
"graphiques": {
    "entree_ext_60":  graphs_dvsg["entree_ext"],
    "sortie_ext_60":  graphs_dvsg["sortie_ext"],
    "entree_flex_60": graphs_dvsg["entree_flex"],
    "sortie_flex_60": graphs_dvsg["sortie_flex"],
    "entree_ext_240":  graphs_dvsg["entree_ext_240"],
    "sortie_ext_240":  graphs_dvsg["sortie_ext_240"],
    "entree_flex_240": graphs_dvsg["entree_flex_240"],
    "sortie_flex_240": graphs_dvsg["sortie_flex_240"],
    "prog_sain_60":  graphs_prog["prog_sain_60"],
    "prog_lese_60":  graphs_prog["prog_lese_60"],
    "prog_sain_240": graphs_prog["prog_sain_240"],
    "prog_lese_240": graphs_prog["prog_lese_240"],
    "exc_ext":  graphs_exc.get("exc_ext", ""),
    "exc_flex": graphs_exc.get("exc_flex", ""),
}
```

## Paramètres utilisés pour les graphiques progression

Dans `generate_rapport.py`, les paramètres sont construits depuis les BiodexData
avec `_v(serie, attr, subattr, default)` pour accès sécurisé :

```python
params_e60 = {
    'ext': {
        'sain': {'moment_max': _v(e60, 'ext_moment_max', 'sain_d', 316.9), 'angle': 81, 'amplitude': 99},
        'lese': {'moment_max': _v(e60, 'ext_moment_max', 'lese_g', 313.6), 'angle': 70, 'amplitude': 101}
    },
    'flex': {
        'sain': {'moment_max': _v(e60, 'flex_moment_max', 'sain_d', 173.0), 'angle': 33, 'amplitude': 99},
        'lese': {'moment_max': _v(e60, 'flex_moment_max', 'lese_g', 153.9), 'angle': 29, 'amplitude': 101}
    }
}
# Idem pour params_s60, params_e240, params_s240
```
