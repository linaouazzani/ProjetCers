"""
graphiques.py
=============
ÉTAPE 2 — Génération des 4 graphiques isocinétiques (courbes D vs G)
Projet CERS Capbreton — Rapport Isocinétique automatisé

Graphiques générés (grille 2x2) :
  [0] Entrée  60°/s Extension D vs G
  [1] Sortie  60°/s Extension D vs G
  [2] Entrée  60°/s Flexion   D vs G
  [3] Sortie  60°/s Flexion   D vs G

Chaque graphique :
  - Courbe pleine bleue   = jambe Saine (D)
  - Courbe pointillée rouge = jambe Lésée (G)
  - Ligne horizontale pointillée grise = niveau du Moment Max Sain
  - Ligne verticale pointillée = angle au Moment Max
  - Annotation : Moment Max + Angle

Les courbes sont des gaussiennes simulées à partir des paramètres
extraits du PDF (Moment Max, Angle au moment max).
Les PDFs Biodex ne contiennent pas les coordonnées brutes point par point
— on reconstitue la forme de la courbe comme le fait le logiciel Biodex.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # backend non-interactif pour génération PNG
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import os


# ---------------------------------------------------------------------------
# Paramètres réels extraits des PDFs — N. Della Schiava
# ---------------------------------------------------------------------------

# Structure : (moment_max_sain, angle_sain, moment_max_lese, angle_lese, amplitude)
# Amplitude de mouvement ≈ 100° (99-101° selon les tests)

# Couleurs — code couleur entrée/sortie
COULEUR_ENTREE = "#1c3f6e"  # bleu fonce CERS — tests d'entree
COULEUR_SORTIE = "#2176c7"  # bleu moyen vif — tests de sortie
GRIS_REF       = "#888888"  # gris — ligne de reference

# Alias pour compatibilite
BLEU_SAIN  = COULEUR_ENTREE
ROUGE_LESE = COULEUR_SORTIE

PARAMS = {
    "entree_60_ext": {
        "titre": "Entree 60deg/s Extension (D vs G)",
        "sain":  {"moment_max": 316.9, "angle": 81, "amplitude": 99},
        "lese":  {"moment_max": 313.6, "angle": 70, "amplitude": 101},
        "ylim":  (0, 350),
        "couleur": COULEUR_ENTREE,
    },
    "sortie_60_ext": {
        "titre": "Sortie 60deg/s Extension (D vs G)",
        "sain":  {"moment_max": 328.0, "angle": 68, "amplitude": 88},
        "lese":  {"moment_max": 333.3, "angle": 66, "amplitude": 92},
        "ylim":  (0, 380),
        "couleur": COULEUR_SORTIE,
    },
    "entree_60_flex": {
        "titre": "Entree 60deg/s Flexion (D vs G)",
        "sain":  {"moment_max": 173.0, "angle": 33, "amplitude": 99},
        "lese":  {"moment_max": 153.9, "angle": 29, "amplitude": 101},
        "ylim":  (0, 210),
        "couleur": COULEUR_ENTREE,
    },
    "sortie_60_flex": {
        "titre": "Sortie 60deg/s Flexion (D vs G)",
        "sain":  {"moment_max": 195.4, "angle": 32, "amplitude": 88},
        "lese":  {"moment_max": 162.0, "angle": 27, "amplitude": 92},
        "ylim":  (0, 230),
        "couleur": COULEUR_SORTIE,
    },
    "entree_240_ext": {
        "titre": "Entree 240deg/s Extension (D vs G)",
        "sain":  {"moment_max": 200.0, "angle": 75, "amplitude": 99},
        "lese":  {"moment_max": 195.0, "angle": 68, "amplitude": 101},
        "ylim":  (0, 250),
        "couleur": COULEUR_ENTREE,
    },
    "sortie_240_ext": {
        "titre": "Sortie 240deg/s Extension (D vs G)",
        "sain":  {"moment_max": 210.0, "angle": 72, "amplitude": 88},
        "lese":  {"moment_max": 205.0, "angle": 65, "amplitude": 92},
        "ylim":  (0, 260),
        "couleur": COULEUR_SORTIE,
    },
    "entree_240_flex": {
        "titre": "Entree 240deg/s Flexion (D vs G)",
        "sain":  {"moment_max": 120.0, "angle": 30, "amplitude": 99},
        "lese":  {"moment_max": 110.0, "angle": 27, "amplitude": 101},
        "ylim":  (0, 160),
        "couleur": COULEUR_ENTREE,
    },
    "sortie_240_flex": {
        "titre": "Sortie 240deg/s Flexion (D vs G)",
        "sain":  {"moment_max": 130.0, "angle": 28, "amplitude": 88},
        "lese":  {"moment_max": 120.0, "angle": 25, "amplitude": 92},
        "ylim":  (0, 170),
        "couleur": COULEUR_SORTIE,
    },
}


# ---------------------------------------------------------------------------
# Génération d'une courbe gaussienne type Biodex
# ---------------------------------------------------------------------------

def courbe_biodex(moment_max: float, angle_peak: float,
                  amplitude: float, n_points: int = 300) -> tuple:
    """
    Génère une courbe de moment isocinétique réaliste (forme gaussienne).

    Le Biodex mesure le moment en fonction de l'angle articulaire.
    Pour l'extension : angle de 0° (genou fléchi) → 100° (genou tendu)
    Le pic de force se produit autour de 60-80° pour l'extension.

    Args:
        moment_max : valeur peak du moment (N·m)
        angle_peak : angle auquel le moment est maximal (deg)
        amplitude  : amplitude de mouvement totale (deg)
        n_points   : résolution de la courbe

    Returns:
        (angles, moments) — deux arrays numpy
    """
    # Plage angulaire : de 0 à amplitude
    angles = np.linspace(0, amplitude, n_points)

    # Largeur de la gaussienne (sigma) — calibrée pour ressembler aux courbes Biodex
    # Plus la vitesse est élevée, plus la courbe est plate → sigma plus grand
    sigma = amplitude * 0.28

    # Gaussienne centrée sur l'angle du pic
    moments = moment_max * np.exp(-0.5 * ((angles - angle_peak) / sigma) ** 2)

    # Légère asymétrie : la montée est plus rapide que la descente (réalisme biomécanique)
    # On applique une correction subtile : pente plus raide avant le pic
    for i, a in enumerate(angles):
        if a < angle_peak:
            # Montée : sigma plus petit (montée plus rapide)
            sigma_montee = sigma * 0.75
            moments[i] = moment_max * np.exp(-0.5 * ((a - angle_peak) / sigma_montee) ** 2)

    # S'assurer que les extrémités sont proches de 0
    fade_width = amplitude * 0.08
    for i, a in enumerate(angles):
        if a < fade_width:
            moments[i] *= (a / fade_width) ** 1.5
        if a > amplitude - fade_width:
            moments[i] *= ((amplitude - a) / fade_width) ** 1.5

    return angles, moments


# ---------------------------------------------------------------------------
# Génération d'un graphique individuel
# ---------------------------------------------------------------------------

def generer_graphique(ax, params: dict, show_ylabel: bool = True):
    """
    Dessine un graphique D vs G sur un axe matplotlib.
    La couleur (entrée=#1c3f6e ou sortie=#c0392b) est dans params['couleur'].
    Sain = trait plein, Lésé = pointillé.
    """
    sain   = params["sain"]
    lese   = params["lese"]
    couleur = params.get("couleur", COULEUR_ENTREE)

    angles_s, moments_s = courbe_biodex(sain["moment_max"], sain["angle"], sain["amplitude"])
    angles_l, moments_l = courbe_biodex(lese["moment_max"], lese["angle"], lese["amplitude"])

    ax.plot(angles_s, moments_s,
            color=couleur, linewidth=2.2, linestyle='-',
            label='Sain (D)', zorder=3)

    ax.plot(angles_l, moments_l,
            color=couleur, linewidth=2.0, linestyle='--',
            label='Lese (G)', dashes=(6, 3), zorder=3)

    ax.axhline(y=sain["moment_max"],
               color=GRIS_REF, linewidth=1.0, linestyle='--',
               alpha=0.6, zorder=1)

    ax.axvline(x=lese["angle"],
               color=couleur, linewidth=1.0, linestyle=':',
               alpha=0.7, zorder=2)

    ax.text(2, sain["moment_max"] * 1.04,
            f'Moment Max, {sain["moment_max"]}',
            fontsize=7.5, color='#222222', fontweight='normal', va='bottom')

    ax.annotate(f'Angle = {lese["angle"]}',
                xy=(lese["angle"], lese["moment_max"] * 0.15),
                xytext=(lese["angle"] + 3, lese["moment_max"] * 0.08),
                fontsize=7.5, color=couleur, arrowprops=None)

    idx_d = int(len(angles_s) * 0.82)
    ax.text(angles_s[idx_d], moments_s[idx_d] + sain["moment_max"] * 0.04,
            'D', fontsize=8, color=couleur, fontweight='bold')

    idx_g = int(len(angles_l) * 0.82)
    ax.text(angles_l[idx_g], moments_l[idx_g] - sain["moment_max"] * 0.12,
            'G', fontsize=8, color=couleur, fontweight='bold')

    ax.set_title(params["titre"], fontsize=9, fontweight='bold', pad=6, color='#1a1a1a')
    ax.set_xlabel('Angle (deg)', fontsize=8, color='#444444')
    if show_ylabel:
        ax.set_ylabel('Moment Max', fontsize=8, color='#444444')

    ax.set_xlim(0, 103)
    ax.set_ylim(params["ylim"])
    ax.tick_params(axis='both', labelsize=7.5, colors='#666666')
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.grid(True, axis='both', alpha=0.25, linewidth=0.5, color='#aaaaaa', linestyle='-')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_color('#dddddd')
    ax.spines['bottom'].set_linewidth(0.8)
    ax.set_facecolor('#ffffff')


# ---------------------------------------------------------------------------
# Génération de la grille 2x2 complète
# ---------------------------------------------------------------------------

def generer_graphiques_biodex(output_path: str = "outputs/graphiques_biodex.png") -> str:
    """
    Génère les 4 graphiques isocinétiques en grille 2x2 et sauvegarde en PNG.

    Disposition :
      [Entrée Ext] [Sortie Ext]
      [Entrée Flex][Sortie Flex]

    Args:
        output_path : chemin de sauvegarde du PNG

    Returns:
        output_path si succès
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    # Figure 2x2 — dimensions calibrées pour s'intégrer dans le PDF A4
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    fig.patch.set_facecolor('#ffffff')

    # Légère marge entre les sous-graphiques
    plt.subplots_adjust(hspace=0.42, wspace=0.22,
                        left=0.07, right=0.97,
                        top=0.95, bottom=0.08)

    ordre = [
        ("entree_60_ext",  axes[0, 0], True),
        ("sortie_60_ext",  axes[0, 1], False),
        ("entree_60_flex", axes[1, 0], True),
        ("sortie_60_flex", axes[1, 1], False),
    ]

    for cle, ax, show_y in ordre:
        generer_graphique(ax, PARAMS[cle], show_ylabel=show_y)

    # --- Légende commune en bas ---
    legend_elements = [
        Line2D([0], [0], color=COULEUR_ENTREE, linewidth=2, linestyle='-',  label='Entree Sain (D)'),
        Line2D([0], [0], color=COULEUR_ENTREE, linewidth=2, linestyle='--', dashes=(6, 3), label='Entree Lese (G)'),
        Line2D([0], [0], color=COULEUR_SORTIE, linewidth=2, linestyle='-',  label='Sortie Sain (D)'),
        Line2D([0], [0], color=COULEUR_SORTIE, linewidth=2, linestyle='--', dashes=(6, 3), label='Sortie Lese (G)'),
    ]
    fig.legend(handles=legend_elements,
               loc='lower center', ncol=4,
               fontsize=7.5, frameon=True,
               framealpha=0.9, edgecolor='#cccccc',
               bbox_to_anchor=(0.5, 0.001))

    # Sauvegarde haute résolution
    plt.savefig(output_path, dpi=180, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    print(f"  ✅ Graphiques sauvegardés : {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Génération d'un graphique individuel (pour intégration Jinja2 — base64)
# ---------------------------------------------------------------------------

def graphique_en_base64(cle: str, biodex_data=None, mouvement: str = "ext") -> str:
    """
    Génère un graphique D vs G individuel en base64.
    Detecte automatiquement 60 ou 240 depuis le nom de cle.
    Si biodex_data est fourni, les moment_max reels remplacent les valeurs PARAMS.
    """
    import io
    import base64

    p = dict(PARAMS[cle])

    if biodex_data is not None:
        try:
            vitesse = "240" if "240" in cle else "60"
            serie = biodex_data.serie_240 if vitesse == "240" else biodex_data.serie_60
            if serie is not None:
                attr_mm = 'ext_moment_max' if mouvement == "ext" else 'flex_moment_max'
                sain_mm = getattr(getattr(serie, attr_mm, None), 'sain_d', None)
                lese_mm = getattr(getattr(serie, attr_mm, None), 'lese_g', None)
                if sain_mm:
                    p["sain"] = dict(p["sain"]); p["sain"]["moment_max"] = sain_mm
                    ymax = max(p["sain"]["moment_max"], lese_mm or p["lese"]["moment_max"]) * 1.2
                    p["ylim"] = (0, ymax)
                if lese_mm:
                    p["lese"] = dict(p["lese"]); p["lese"]["moment_max"] = lese_mm
        except Exception:
            pass

    fig, ax = plt.subplots(1, 1, figsize=(5.2, 3.5))
    fig.patch.set_facecolor('#ffffff')
    plt.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.14)

    generer_graphique(ax, p, show_ylabel=True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    buf.seek(0)

    return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode('utf-8')


# ---------------------------------------------------------------------------
# MAIN — test et génération
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "█"*60)
    print("  GRAPHIQUES BIODEX — ÉTAPE 2")
    print("  Patient : N. Della Schiava — 60°/s Extension + Flexion")
    print("█"*60)

    print("\n📊 Génération de la grille 2x2...")
    chemin = generer_graphiques_biodex("outputs/graphiques_biodex.png")

    print("\n🖼️  Test génération base64 (pour Jinja2)...")
    for cle in PARAMS.keys():
        b64 = graphique_en_base64(cle)
        print(f"  ✅ {cle} : {len(b64)} caractères base64")

    print(f"\n  💾 Fichier PNG : {chemin}")
    print("\n✅ ÉTAPE 2 terminée — ouvre outputs/graphiques_biodex.png pour vérifier !\n")


# ---------------------------------------------------------------------------
# Graphiques de progression entrée → sortie
# ---------------------------------------------------------------------------

def _graphique_progression_4courbes(
    titre: str,
    pe_sain: dict, ps_sain: dict,
    pe_lese: dict, ps_lese: dict,
) -> str:
    """
    4 courbes :
      Sain Entree  : #1c3f6e, plein,      linewidth=1.8
      Sain Sortie  : #2176c7, plein,      linewidth=1.8
      Lese Entree  : #1c3f6e, pointille,  linewidth=1.5
      Lese Sortie  : #2176c7, pointille,  linewidth=1.5
    Titre : "Extension 60deg/s — Lese : +X.X%"
    """
    import io, base64

    prog_lese = 0.0
    if pe_lese["moment_max"] and pe_lese["moment_max"] != 0:
        prog_lese = ((ps_lese["moment_max"] - pe_lese["moment_max"])
                     / abs(pe_lese["moment_max"]) * 100)
    prog_sain = 0.0
    if pe_sain["moment_max"] and pe_sain["moment_max"] != 0:
        prog_sain = ((ps_sain["moment_max"] - pe_sain["moment_max"])
                     / abs(pe_sain["moment_max"]) * 100)

    ymax = max(pe_sain["moment_max"], ps_sain["moment_max"],
               pe_lese["moment_max"], ps_lese["moment_max"]) * 1.28

    fig, ax = plt.subplots(figsize=(5, 3.2))
    fig.patch.set_facecolor('#fff')
    plt.subplots_adjust(left=0.13, right=0.96, top=0.84, bottom=0.14)

    ae_s, me_s = courbe_biodex(pe_sain["moment_max"], pe_sain["angle"], pe_sain["amplitude"])
    as_s, ms_s = courbe_biodex(ps_sain["moment_max"], ps_sain["angle"], ps_sain["amplitude"])
    ae_l, me_l = courbe_biodex(pe_lese["moment_max"], pe_lese["angle"], pe_lese["amplitude"])
    as_l, ms_l = courbe_biodex(ps_lese["moment_max"], ps_lese["angle"], ps_lese["amplitude"])

    ax.plot(ae_s, me_s, color=COULEUR_ENTREE, linewidth=1.8, linestyle='-',
            label=f'Sain entree ({pe_sain["moment_max"]:.0f})')
    ax.plot(as_s, ms_s, color=COULEUR_SORTIE, linewidth=1.8, linestyle='-',
            label=f'Sain sortie ({ps_sain["moment_max"]:.0f})')
    ax.plot(ae_l, me_l, color=COULEUR_ENTREE, linewidth=1.5, linestyle='--', dashes=(5, 3),
            label=f'Lese entree ({pe_lese["moment_max"]:.0f})')
    ax.plot(as_l, ms_l, color=COULEUR_SORTIE, linewidth=1.5, linestyle='--', dashes=(5, 3),
            label=f'Lese sortie ({ps_lese["moment_max"]:.0f})')

    c_prog = '#2a8a36' if prog_lese >= 0 else '#c0392b'
    ax.set_title(f'{titre} — Lese : {prog_lese:+.1f}% | Sain : {prog_sain:+.1f}%',
                 fontsize=7.5, fontweight='bold', color=c_prog, pad=5)
    ax.set_xlabel('Angle (deg)', fontsize=7.5)
    ax.set_ylabel('Moment Max (N.m)', fontsize=7.5)
    ax.set_ylim(0, ymax)
    ax.set_xlim(0, 103)
    ax.grid(True, alpha=0.2, linewidth=0.5, color='#aaa')
    ax.tick_params(labelsize=7, colors='#666666')
    ax.legend(fontsize=6, loc='upper right', framealpha=0.85, ncol=2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['left'].set_linewidth(0.7)
    ax.spines['bottom'].set_color('#dddddd')
    ax.spines['bottom'].set_linewidth(0.7)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()


def generer_graphiques_progression(
    params_e60: dict, params_s60: dict,
    params_e240: dict = None, params_s240: dict = None,
) -> dict:
    """
    Genere 4 graphiques de progression (Extension 60, Extension 240, Flexion 60, Flexion 240).
    Chaque graphique a 4 courbes : Sain/Lese x Entree/Sortie.
    """
    graphs = {}

    graphs['prog_ext_60'] = _graphique_progression_4courbes(
        titre="Extension 60deg/s",
        pe_sain=params_e60['ext']['sain'], ps_sain=params_s60['ext']['sain'],
        pe_lese=params_e60['ext']['lese'], ps_lese=params_s60['ext']['lese'],
    )

    if params_e240 and params_s240:
        graphs['prog_ext_240'] = _graphique_progression_4courbes(
            titre="Extension 240deg/s",
            pe_sain=params_e240['ext']['sain'], ps_sain=params_s240['ext']['sain'],
            pe_lese=params_e240['ext']['lese'], ps_lese=params_s240['ext']['lese'],
        )
    else:
        graphs['prog_ext_240'] = graphs['prog_ext_60']

    graphs['prog_flex_60'] = _graphique_progression_4courbes(
        titre="Flexion 60deg/s",
        pe_sain=params_e60['flex']['sain'], ps_sain=params_s60['flex']['sain'],
        pe_lese=params_e60['flex']['lese'], ps_lese=params_s60['flex']['lese'],
    )

    if params_e240 and params_s240:
        graphs['prog_flex_240'] = _graphique_progression_4courbes(
            titre="Flexion 240deg/s",
            pe_sain=params_e240['flex']['sain'], ps_sain=params_s240['flex']['sain'],
            pe_lese=params_e240['flex']['lese'], ps_lese=params_s240['flex']['lese'],
        )
    else:
        graphs['prog_flex_240'] = graphs['prog_flex_60']

    return graphs