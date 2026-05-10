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

PARAMS = {
    "entree_60_ext": {
        "titre": "Entrée 60°/s Extension (D vs G)",
        "sain":  {"moment_max": 316.9, "angle": 81,  "amplitude": 99},
        "lese":  {"moment_max": 313.6, "angle": 70,  "amplitude": 101},
        "ylim": (0, 350),
    },
    "sortie_60_ext": {
        "titre": "Sortie 60°/s Extension (D vs G)",
        "sain":  {"moment_max": 328.0, "angle": 68,  "amplitude": 88},
        "lese":  {"moment_max": 333.3, "angle": 66,  "amplitude": 92},
        "ylim": (0, 380),
    },
    "entree_60_flex": {
        "titre": "Entrée 60°/s Flexion (D vs G)",
        "sain":  {"moment_max": 173.0, "angle": 33,  "amplitude": 99},
        "lese":  {"moment_max": 153.9, "angle": 29,  "amplitude": 101},
        "ylim": (0, 210),
    },
    "sortie_60_flex": {
        "titre": "Sortie 60°/s Flexion (D vs G)",
        "sain":  {"moment_max": 195.4, "angle": 32,  "amplitude": 88},
        "lese":  {"moment_max": 162.0, "angle": 27,  "amplitude": 92},
        "ylim": (0, 230),
    },
}

# Couleurs — style Biodex fidèle à l'image de référence
BLEU_SAIN  = "#1a5fa8"   # bleu foncé — jambe saine (D)
ROUGE_LESE = "#cc2200"   # rouge foncé — jambe lésée (G)
GRIS_REF   = "#888888"   # gris — ligne de référence


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

    Args:
        ax     : axe matplotlib sur lequel dessiner
        params : dict avec 'titre', 'sain', 'lese', 'ylim'
        show_ylabel : afficher le label Y (uniquement colonne gauche)
    """
    sain = params["sain"]
    lese = params["lese"]

    # --- Génération des courbes ---
    angles_s, moments_s = courbe_biodex(
        sain["moment_max"], sain["angle"], sain["amplitude"]
    )
    angles_l, moments_l = courbe_biodex(
        lese["moment_max"], lese["angle"], lese["amplitude"]
    )

    # --- Tracé des courbes ---
    ax.plot(angles_s, moments_s,
            color=BLEU_SAIN, linewidth=2.2, linestyle='-',
            label='Sain (D)', zorder=3)

    ax.plot(angles_l, moments_l,
            color=ROUGE_LESE, linewidth=2.0, linestyle='--',
            label='Lésé (G)', dashes=(6, 3), zorder=3)

    # --- Ligne horizontale : niveau du Moment Max Sain ---
    ax.axhline(y=sain["moment_max"],
               color=GRIS_REF, linewidth=1.0, linestyle='--',
               alpha=0.6, zorder=1)

    # --- Ligne verticale : angle du pic lésé ---
    ax.axvline(x=lese["angle"],
               color=ROUGE_LESE, linewidth=1.0, linestyle=':',
               alpha=0.7, zorder=2)

    # --- Annotations ---
    # Moment Max sain (coin haut gauche)
    ax.text(2, sain["moment_max"] * 1.04,
            f'Moment Max, {sain["moment_max"]}',
            fontsize=7.5, color='#222222', fontweight='normal',
            va='bottom')

    # Angle du pic lésé (annotation en bas à droite du marqueur)
    ax.annotate(f'Angle = {lese["angle"]}',
                xy=(lese["angle"], lese["moment_max"] * 0.15),
                xytext=(lese["angle"] + 3, lese["moment_max"] * 0.08),
                fontsize=7.5, color=ROUGE_LESE,
                arrowprops=None)

    # Label "D" sur la courbe saine (vers la fin de la courbe)
    idx_d = int(len(angles_s) * 0.82)
    ax.text(angles_s[idx_d], moments_s[idx_d] + sain["moment_max"] * 0.04,
            'D', fontsize=8, color=BLEU_SAIN, fontweight='bold')

    # Label "G" sur la courbe lésée
    idx_g = int(len(angles_l) * 0.82)
    ax.text(angles_l[idx_g], moments_l[idx_g] - sain["moment_max"] * 0.12,
            'G', fontsize=8, color=ROUGE_LESE, fontweight='bold')

    # --- Style des axes ---
    ax.set_title(params["titre"], fontsize=9, fontweight='bold',
                 pad=6, color='#1a1a1a')

    ax.set_xlabel('Angle (°)', fontsize=8, color='#444444')
    if show_ylabel:
        ax.set_ylabel('Moment Max', fontsize=8, color='#444444')

    ax.set_xlim(0, max(sain["amplitude"], lese["amplitude"]) + 2)
    ax.set_ylim(params["ylim"])

    # Graduations
    ax.tick_params(axis='both', labelsize=7.5, colors='#555555')
    ax.set_xticks(range(0, 110, 20))

    # Grille légère
    ax.grid(True, axis='both', alpha=0.25, linewidth=0.5,
            color='#aaaaaa', linestyle='-')
    ax.set_axisbelow(True)

    # Bordure fine
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color('#cccccc')

    # Fond blanc
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
        Line2D([0], [0], color=BLEU_SAIN,  linewidth=2, linestyle='-',
               label='Sain (D)'),
        Line2D([0], [0], color=ROUGE_LESE, linewidth=2, linestyle='--',
               dashes=(6, 3), label='Lésé (G)'),
    ]
    fig.legend(handles=legend_elements,
               loc='lower center', ncol=2,
               fontsize=8.5, frameon=True,
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

def graphique_en_base64(cle: str) -> str:
    """
    Génère un graphique individuel et le retourne en base64 (pour HTML inline).
    Utilisé par generate_rapport.py pour injecter les images dans le template.

    Args:
        cle : clé du graphique ('entree_60_ext', 'sortie_60_ext', etc.)

    Returns:
        string base64 de l'image PNG
    """
    import io
    import base64

    fig, ax = plt.subplots(1, 1, figsize=(5.2, 3.5))
    fig.patch.set_facecolor('#ffffff')
    plt.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.14)

    generer_graphique(ax, PARAMS[cle], show_ylabel=True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


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

def graphique_progression(
    titre: str,
    val_entree: float,
    val_sortie: float,
    angle_entree: float,
    angle_sortie: float,
    amplitude_entree: float,
    amplitude_sortie: float,
    ylim: tuple,
    couleur: str,
) -> str:
    """
    Génère un graphique de progression entrée→sortie pour un côté (sain ou lésé).
    Superpose les 2 courbes : entrée (pointillé) et sortie (plein).
    """
    import io, base64

    fig, ax = plt.subplots(figsize=(5, 3.2))
    fig.patch.set_facecolor('#fff')
    plt.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.14)

    ae, me = courbe_biodex(val_entree, angle_entree, amplitude_entree)
    as_, ms = courbe_biodex(val_sortie, angle_sortie, amplitude_sortie)

    # Courbes
    ax.plot(ae, me, color=couleur, linewidth=1.8, linestyle='--',
            alpha=0.55, dashes=(5, 3), label=f'Entrée ({val_entree:.0f})')
    ax.plot(as_, ms, color=couleur, linewidth=2.2, linestyle='-',
            label=f'Sortie ({val_sortie:.0f})')
    ax.fill_between(as_, 0, ms, alpha=0.06, color=couleur)

    # Ligne de référence entrée
    ax.axhline(y=val_entree, color='gray', linewidth=0.7, linestyle=':', alpha=0.5)

    # Annotation progression
    prog = round(((val_sortie - val_entree) / abs(val_entree)) * 100, 1) if val_entree else 0
    c_p = '#2a8a36' if prog >= 0 else '#c41a1a'
    ax.text(2, val_sortie * 1.06,
            f'Progression : {prog:+.1f}%',
            fontsize=8, color=c_p, fontweight='bold')

    ax.set_title(titre, fontsize=8.5, fontweight='bold', color='#1a1a1a', pad=5)
    ax.set_xlabel('Angle (°)', fontsize=7.5)
    ax.set_ylabel('Moment Max (N·m)', fontsize=7.5)
    ax.set_ylim(ylim)
    ax.set_xlim(0, max(amplitude_entree, amplitude_sortie) + 2)
    ax.grid(True, alpha=0.2, linewidth=0.5, color='#aaa')
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc='upper right', framealpha=0.8)
    for sp in ax.spines.values():
        sp.set_linewidth(0.7)
        sp.set_color('#cccccc')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()


def generer_graphiques_progression(params_entree: dict, params_sortie: dict) -> dict:
    """
    Génère les 4 graphiques de progression (Ext Sain, Ext Lésé, Flex Sain, Flex Lésé).

    params format :
    {
        'ext': {'sain': {'moment_max': X, 'angle': Y, 'amplitude': Z},
                'lese': {'moment_max': X, 'angle': Y, 'amplitude': Z}},
        'flex': { ... }
    }
    """
    BLEU_SAIN  = '#1c3f6e'
    ROUGE_LESE = '#cc2200'

    graphs = {}

    # Extension Sain
    graphs['prog_ext_sain'] = graphique_progression(
        titre="Extension — Sain (D)",
        val_entree=params_entree['ext']['sain']['moment_max'],
        val_sortie=params_sortie['ext']['sain']['moment_max'],
        angle_entree=params_entree['ext']['sain']['angle'],
        angle_sortie=params_sortie['ext']['sain']['angle'],
        amplitude_entree=params_entree['ext']['sain']['amplitude'],
        amplitude_sortie=params_sortie['ext']['sain']['amplitude'],
        ylim=(0, max(params_entree['ext']['sain']['moment_max'],
                     params_sortie['ext']['sain']['moment_max']) * 1.3),
        couleur=BLEU_SAIN,
    )

    # Extension Lésé
    graphs['prog_ext_lese'] = graphique_progression(
        titre="Extension — Lésé (G)",
        val_entree=params_entree['ext']['lese']['moment_max'],
        val_sortie=params_sortie['ext']['lese']['moment_max'],
        angle_entree=params_entree['ext']['lese']['angle'],
        angle_sortie=params_sortie['ext']['lese']['angle'],
        amplitude_entree=params_entree['ext']['lese']['amplitude'],
        amplitude_sortie=params_sortie['ext']['lese']['amplitude'],
        ylim=(0, max(params_entree['ext']['lese']['moment_max'],
                     params_sortie['ext']['lese']['moment_max']) * 1.3),
        couleur=ROUGE_LESE,
    )

    # Flexion Sain
    graphs['prog_flex_sain'] = graphique_progression(
        titre="Flexion — Sain (D)",
        val_entree=params_entree['flex']['sain']['moment_max'],
        val_sortie=params_sortie['flex']['sain']['moment_max'],
        angle_entree=params_entree['flex']['sain']['angle'],
        angle_sortie=params_sortie['flex']['sain']['angle'],
        amplitude_entree=params_entree['flex']['sain']['amplitude'],
        amplitude_sortie=params_sortie['flex']['sain']['amplitude'],
        ylim=(0, max(params_entree['flex']['sain']['moment_max'],
                     params_sortie['flex']['sain']['moment_max']) * 1.3),
        couleur=BLEU_SAIN,
    )

    # Flexion Lésé
    graphs['prog_flex_lese'] = graphique_progression(
        titre="Flexion — Lésé (G)",
        val_entree=params_entree['flex']['lese']['moment_max'],
        val_sortie=params_sortie['flex']['lese']['moment_max'],
        angle_entree=params_entree['flex']['lese']['angle'],
        angle_sortie=params_sortie['flex']['lese']['angle'],
        amplitude_entree=params_entree['flex']['lese']['amplitude'],
        amplitude_sortie=params_sortie['flex']['lese']['amplitude'],
        ylim=(0, max(params_entree['flex']['lese']['moment_max'],
                     params_sortie['flex']['lese']['moment_max']) * 1.3),
        couleur=ROUGE_LESE,
    )

    return graphs