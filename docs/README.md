# Documentation CERS Capbreton — ProjetCers

Application Streamlit de génération de rapports PDF de bilan isocinétique et fonctionnel.

## Index des fichiers de documentation

| Fichier | Contenu |
|---------|---------|
| [01_app.md](01_app.md) | Interface Streamlit — `app.py` : uploaders, parsing, génération |
| [02_generate_rapport.md](02_generate_rapport.md) | Pipeline de génération — `generate_rapport.py` |
| [03_template_html.md](03_template_html.md) | Template Jinja2 — `templates/rapport.html` : pages, macros, CSS |
| [04_parsers.md](04_parsers.md) | Parsers PDF — `biodex_parser.py`, `vald_parser.py`, `cr_parser.py` |
| [05_graphiques.md](05_graphiques.md) | Génération graphiques — `graphiques.py` |
| [06_clubs_database.md](06_clubs_database.md) | Base de données clubs et blessures — `clubs_database.py`, JSON |

## Stack technique

- **Frontend** : Streamlit
- **PDF export** : Windows → pdfkit + wkhtmltopdf ; Linux/Cloud → WeasyPrint
- **Template** : Jinja2
- **Parsing PDF** : pdfplumber
- **Graphiques** : Matplotlib (backend Agg, base64 inline)
- **Déploiement** : Streamlit Cloud (Linux/WeasyPrint)

## Contraintes WeasyPrint (à respecter dans rapport.html)

- Jamais `var()` CSS → couleurs hex en dur
- Jamais `flexbox` dans les tableaux → `display:table` + `display:table-cell`
- `-webkit-print-color-adjust:exact` sur tous les fonds colorés
- `@page { margin: 0mm; }` + `.page { width:210mm; height:297mm; }`
- `table-layout:fixed` sur toutes les `<table>`

## Lancement local

```bash
streamlit run app.py
```
