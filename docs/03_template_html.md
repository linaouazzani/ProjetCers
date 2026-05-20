# templates/rapport.html — Template Jinja2

## Structure des pages (ordre dans le fichier)

| Position | Contenu | Classe/Style |
|----------|---------|--------------|
| 0 | Page de garde | `<div style="height:297mm; width:210mm; ...">` |
| 1 | Données Biodex 60°/s + 240°/s | `<div class="page">` — PAGE 1 |
| 2 | Graphiques isocinétiques | `<div class="page">` — PAGE 2 |
| 3 | Progression + remarques médicales | `<div class="page">` — PAGE 3 |
| 4 | VALD ForceDecks (conditionnel) | `<div class="page">` — PAGE 4 |
| 5 | GPS Catapult (placeholder) | `<div class="page">` — PAGE GPS |

## CSS globals (en tête du fichier)

```css
@page { size: A4; margin: 0mm; }

body { margin:0; padding:0; width:210mm; font-family:Arial,Helvetica,sans-serif; }

.page {
    width: 210mm; max-width: 210mm; height: 297mm;
    margin: 0; padding: 0; overflow: hidden;
    box-sizing: border-box; position: relative;
    background: #ffffff;
    display: flex; flex-direction: column;
}
.page + .page { page-break-before: always; }

@media print {
    body { margin: 0 !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
```

### Classes CSS importantes

```css
/* En-tête commune à toutes les pages */
.header-global        /* display:table, background:#1c3f6e */
.hg-left/.hg-center/.hg-right  /* cellules de l'en-tête */

/* Page content */
.page-content         /* flex:1, padding:0 8mm 6mm 8mm */

/* Tableaux Biodex */
.mt                   /* table principale, table-layout:fixed */
.mt th.h-entree       /* fond #1c3f6e */
.mt th.h-sortie       /* fond #2176c7 */
.mt th.h-prog-sain    /* fond #5b9bd5 */
.mt th.h-prog-lese    /* fond #8ab4d9 */
.mt th.hm             /* colonne métrique, largeur 76px */
.mt td.cm             /* cellule métrique gauche, fond #e8eef5 */
.mt tr.alt td         /* lignes alternées #eef3fa */
.mt tr.grp td         /* groupes (Extension/Flexion) #dce6f2 */

/* Couleurs déficit (fond coloré, texte blanc) */
.dg    /* vert  #2a8a36 — dans norme (<10%) */
.do    /* orange #e07b00 — déficit modéré (10-20%) */
.dr    /* rouge #c0392b — déficit important (>20%) */
.dw    /* gris  #999999 — non disponible */
.dn    /* bleu  #1c3f6e — lésé plus fort */

/* Couleurs VALD (texte seul) */
.vc-g  /* vert  #2a8a36 */
.vc-o  /* orange #e07b00 */
.vc-r  /* rouge #c0392b */
.vc-w  /* gris  #888888 */

/* Progression */
.pg    /* vert  #2a8a36 */
.pr    /* rouge #c0392b */
.pn    /* gris  #888888 */

/* Divers */
.bilan-title   /* barre titre section, background:#1c3f6e */
.interp        /* colonne interprétation, font-size:6.5px */
.rem-block     /* bloc remarques */
.acl-block     /* score ACL-RSI */
.med-block     /* remarques médecin */
.footer        /* display:flex, border-top, margin-top:auto */
```

## Macros Jinja2

### anon(nom) — Anonymisation RGPD
```jinja
{% macro anon(nom) -%}
  {%- if nom -%}
    {%- set parts = nom.strip().split(' ') -%}
    {%- if parts|length >= 2 -%}
      {{ parts[0][0] }}. {{ parts[1:] | join(' ') }}
    {%- else -%}{{ nom[0] }}.{%- endif -%}
  {%- else -%}—{%- endif -%}
{%- endmacro %}
```
Exemple : "DELLA SCHIAVA Noé" → "N. DELLA SCHIAVA"

### tableau(s, meta, titre, date_e, date_s, vitesse_num=60)
Macro pour les tableaux Biodex concentrique.
Paramètres :
- `s` : `SerieTemplate` (s60 ou s240)
- `meta` : `SerieMeta` (serie60_meta ou serie240_meta)
- `titre` : str (ex: "60°/s — Concentrique")
- `vitesse_num` : 60 ou 240 (pour normes Ratio/Poids et I/Q)

## Page de garde (structure)

```
<div style="height:297mm; width:210mm; ...">
  ┌─ EN-TÊTE : table 3 cellules (logo CERS | Titre | logo Club + nom)
  ├─ ZONE HERO : table 2 cellules
  │   ├── Colonne photo (140px) : photo patient, badge RGPD, séjour, médecin
  │   └── Colonne infos : nom anonymisé, grille 2col (ddn/sport, poids/côté, délai/club)
  │       ├── Bloc diagnostic (rouge #c0392b)
  │       └── Bloc intervention (bleu #1c3f6e)
  ├─ RÉCAPITULATIF SÉJOUR : conclusion CR ou texte par défaut
  ├─ SOMMAIRE : 4 blocs (Biodex, VALD, Graphiques, GPS)
  └─ FOOTER : position:absolute; bottom:0; background:#1c3f6e; "Page 1"
</div>
```

## En-tête commune (pages 2-6)

```html
<div style="display:table;width:100%;background:#1c3f6e;...">
  <div style="display:table-cell;width:22%;padding:4px 8px;">
    <!-- logo CERS height:32px ou texte fallback -->
  </div>
  <div style="display:table-cell;width:56%;text-align:center;">
    <!-- Titre "CERS Capbreton — Bilan Complet Patient" 11pt -->
    <!-- Sous-titre "anon(patient.nom) · Entrée ... · Sortie ..." 7pt -->
  </div>
  <div style="display:table-cell;width:22%;text-align:right;overflow:hidden;word-break:break-word;">
    <!-- logo club height:28px -->
    <!-- nom_club 8pt white -->
  </div>
</div>
<div style="height:2px;background:#2176c7;margin-bottom:5px;"></div>
```

## Page 1 — Biodex (pages 2 du PDF)

Contenu dans `.page-content` :
1. `.bilan-title` : "BILAN ISOCINETIQUE — Genou {{ entree.lese }}"
2. `{% call tableau(s60, serie60_meta, "...", ..., vitesse_num=60) %}` → tableau 60°/s
3. `{% call tableau(s240, serie240_meta, "...", ..., vitesse_num=240) %}` → tableau 240°/s
4. Section Excentrique : `{% if excentrique %}` → table excentrique + ratio mixte
5. Footer : Page 2 / 5 ou 6

## Page 2 — Graphiques

8 graphiques D vs G (Extension/Flexion × 60°/240°/s × Entrée/Sortie) + 4 graphiques progression.
Conditionnel : `{% if graphiques.exc_ext or graphiques.exc_flex %}` → 2 graphiques excentrique.
Footer : Page 3 / 5 ou 6

## Page 3 — Progression + remarques

Sections :
1. Banner "Progression globale"
2. Graphiques progression (prog_sain_60, prog_lese_60, prog_sain_240, prog_lese_240)
3. Bloc remarques auto (`.rem-block`) : Points d'attention | Points positifs | Progression
4. Bloc ACL-RSI : `{% if acl_rsi_score %}`
5. Bloc remarques médecin : `{% if remarques_medecin %}`
Footer : Page 4 / 5 ou 6

## Page 4 — VALD (conditionnel)

```jinja
{% if vald and vald.has_data %}
```
Contenu :
1. Banner "Section 2 — Bilan Sauts VALD ForceDecks"
2. Tableau SLJ Hauteur (cols : ENT.D / ENT.G / DÉF.ENTRÉE / SORT.D / SORT.G / DÉF.SORTIE / PROG.G / PROG.D)
3. Tableau RSI SLJ (même structure)
4. Tableau CMJ (ENTRÉE | SORTIE | PROGRESSION) width:55%
Footer : Page 5 / 6

## Page GPS — Placeholder

Toujours présente, contient juste un message "Section en cours de développement".
Footer : "Annexe — GPS Catapult"

## Variables Jinja2 disponibles dans le template

```
patient, entree, sortie   : BiodexData
s60, s240                 : SerieTemplate
serie60_meta, serie240_meta : SerieMeta
remarques                 : dict (points_attention, points_positifs, progression)
excentrique               : dict | None
ratio_mixte               : float | None
graphiques                : dict (14 clés base64)
logo_cers_b64             : str | None
logo_club_b64             : str | None
photo_b64                 : str | None
nom_club                  : str
sport, date_naissance, date_operation, type_blessure, cote_opere : str
acl_rsi_score             : int | None
remarques_medecin         : str
delai_post_op             : str
vald                      : dict | None
has_vald                  : bool
cr                        : dict (toujours présent, au moins {})
```
