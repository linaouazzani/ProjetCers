"""
app.py — CERS Capbreton
=======================
Application Streamlit — Rapport Isocinétique Biodex
Lancement : streamlit run app.py
"""

import streamlit as st
import tempfile
import os
import base64
import datetime
import json
from clubs_database import search_clubs
from cr_parser import parse_compte_rendu
from gps_parser import parse_gps_pdf

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
CLUBS_DB_PATH    = os.path.join(_APP_DIR, "clubs_db.json")
BLESSURES_DB_PATH = os.path.join(_APP_DIR, "blessures_db.json")

BLESSURES_DEFAULT = [
    "Rupture LCA", "Rupture LCP", "Rupture LLE", "Rupture LLI",
    "Lésion ménisque interne", "Lésion ménisque externe",
    "Entorse cheville grade I", "Entorse cheville grade II", "Entorse cheville grade III",
    "Rupture tendon d'Achille",
    "Tendinopathie rotulienne", "Tendinopathie achilléenne",
    "Fracture tibia", "Fracture péroné", "Fracture métatarses",
    "Pubalgie",
    "Lésion musculaire ischio-jambiers grade I",
    "Lésion musculaire ischio-jambiers grade II",
    "Lésion musculaire ischio-jambiers grade III",
    "Lésion musculaire quadriceps grade I",
    "Lésion musculaire quadriceps grade II",
    "Lésion musculaire quadriceps grade III",
    "Lésion musculaire adducteurs",
    "Luxation épaule", "Rupture coiffe des rotateurs", "Fracture clavicule",
    "Contusion", "Autre",
]

def charger_blessures():
    if os.path.exists(BLESSURES_DB_PATH):
        with open(BLESSURES_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            tous = list(dict.fromkeys(BLESSURES_DEFAULT + data.get("custom", [])))
            return tous, data.get("custom", [])
    return list(BLESSURES_DEFAULT), []

def sauvegarder_blessure_custom(nouvelle_blessure: str):
    custom = []
    if os.path.exists(BLESSURES_DB_PATH):
        with open(BLESSURES_DB_PATH, "r", encoding="utf-8") as f:
            custom = json.load(f).get("custom", [])
    if nouvelle_blessure not in custom:
        custom.append(nouvelle_blessure)
    with open(BLESSURES_DB_PATH, "w", encoding="utf-8") as f:
        json.dump({"custom": custom}, f, ensure_ascii=False, indent=2)

st.set_page_config(
    page_title="CERS Capbreton — Bilan Isocinétique",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }
.stApp { background: #f0f4f8; }

.hero {
    background: linear-gradient(135deg, #1c3f6e 0%, #2176c7 100%);
    border-radius: 14px; padding: 20px 30px; margin-bottom: 20px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(28,63,110,0.25);
}
.hero h1 { color: white; font-size: 21px; font-weight: 800; margin: 0; }
.hero p  { color: #a8c4e0; font-size: 12px; margin: 3px 0 0 0; }
.hero-badge { background: rgba(255,255,255,0.15); color: white; border-radius: 8px; padding: 5px 12px; font-size: 11px; font-weight: 600; }

.card { background: white; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.card-title { font-size: 12px; font-weight: 700; color: #1c3f6e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; padding-bottom: 7px; border-bottom: 2px solid #e8eef5; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-ok   { background: #d4edda; color: #1a6b2a; }
.badge-wait { background: #fff3cd; color: #8a6200; }
.badge-opt  { background: #e2e8f0; color: #555; }

.club-selected { padding: 10px 14px; border-radius: 10px; border: 2px solid #1c3f6e; background: #eef3fa; display: flex; align-items: center; gap: 10px; font-weight: 600; color: #1c3f6e; }
.info-box { background: #eef3fa; border-left: 4px solid #1c3f6e; border-radius: 0 8px 8px 0; padding: 8px 12px; margin: 6px 0; font-size: 12px; color: #1c3f6e; }

.stButton > button { background: linear-gradient(135deg,#1c3f6e,#1a5fa8) !important; color: white !important; border: none !important; border-radius: 10px !important; padding: 12px 28px !important; font-size: 15px !important; font-weight: 700 !important; width: 100% !important; box-shadow: 0 4px 12px rgba(28,63,110,0.3) !important; }
.stDownloadButton > button { background: linear-gradient(135deg,#2a8a36,#237030) !important; color: white !important; border: none !important; border-radius: 10px !important; padding: 14px 28px !important; font-size: 16px !important; font-weight: 700 !important; width: 100% !important; box-shadow: 0 4px 12px rgba(42,138,54,0.3) !important; margin-top: 8px !important; }

.success-box { background: linear-gradient(135deg,#d4edda,#c3e6cb); border: 1.5px solid #28a745; border-radius: 12px; padding: 14px 18px; text-align: center; margin: 10px 0; }
.success-box h3 { color: #155724; margin: 0 0 3px 0; font-size: 16px; }
.success-box p  { color: #1e7e34; margin: 0; font-size: 11px; }

.preview-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.preview-table th { background: #1c3f6e; color: white; padding: 6px 10px; text-align: left; font-weight: 600; }
.preview-table td { padding: 5px 10px; border-bottom: 1px solid #e2e8f0; }
.preview-table tr:nth-child(even) td { background: #f8fafd; }
</style>
""", unsafe_allow_html=True)


# ── Fonctions utilitaires ─────────────────────────────────────────────────────

def generer_logo_svg(nom_club: str, couleur: str) -> str:
    mots = [m for m in nom_club.split() if len(m) > 2 and m[0].isupper()]
    initiales = "".join(m[0] for m in mots[:3]) if mots else nom_club[:3].upper()
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60" viewBox="0 0 80 60"><rect width="80" height="60" rx="8" fill="{couleur}"/><text x="40" y="38" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="white">{initiales}</text></svg>'
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


@st.cache_data(ttl=3600)
def get_logo(nom_club: str, couleur: str) -> str:
    return generer_logo_svg(nom_club, couleur)


def charger_clubs_db() -> dict:
    if os.path.exists(CLUBS_DB_PATH):
        with open(CLUBS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauvegarder_club_db(nom: str, data: dict):
    db = charger_clubs_db()
    db[nom.lower().strip()] = data
    with open(CLUBS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ── État session ──────────────────────────────────────────────────────────────

if "club_selectionne" not in st.session_state:
    st.session_state.club_selectionne = None
if "nom_club_cache" not in st.session_state:
    st.session_state.nom_club_cache = ""
if "rapport_html_bytes" not in st.session_state:
    st.session_state.rapport_html_bytes = None
if "rapport_pdf_bytes" not in st.session_state:
    st.session_state.rapport_pdf_bytes = None
if "rapport_nom_base" not in st.session_state:
    st.session_state.rapport_nom_base = None


# ── En-tête ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div>
    <h1>CERS Capbreton — Bilan Complet Patient</h1>
    <p>Rapport automatique · Isocinétique Biodex &nbsp;·&nbsp; Sauts VALD ForceDecks &nbsp;·&nbsp; GPS Catapult</p>
  </div>
  <div class="hero-badge">Suivi de progression · PDF A4</div>
</div>
""", unsafe_allow_html=True)


# ── Panneau personnalisation HTML ────────────────────────────────────────────

def _injecter_panneau_personnalisation(html: str) -> str:
    """Injecte un bandeau de contrôle interactif dans le HTML du rapport.
    Permet de cocher/décocher des pages ET des sous-sections.
    Disparaît à l'impression (@media print).
    """
    import re as _re

    def assigner_sections(html_text):
        # Assigner data-section aux div.page qui n'en ont pas encore
        # (ceux qui en ont déjà dans le template sont ignorés)
        sequential = [
            "page-garde", "bilan-60", "bilan-240", "analyse-clinique",
            "bilan-vald", "excentrique", "vald-tableau",
        ]
        pattern = r'(<div[^>]*class=["\'][^"\']*\bpage\b[^"\']*["\'][^>]*>)'
        parts = _re.split(pattern, html_text)
        result = []
        page_count = 0
        for part in parts:
            if _re.match(r'<div[^>]*class=["\'][^"\']*\bpage\b', part):
                if 'data-section' not in part:
                    sid = sequential[page_count] if page_count < len(sequential) \
                          else f"section-{page_count}"
                    part = part.rstrip('>')
                    part = part + f' data-section="{sid}">'
                page_count += 1
            result.append(part)
        return ''.join(result)

    html = assigner_sections(html)

    panneau = """
<style>
/* -- masquage universel : inline style ET classe .hidden -- */
.hidden { display: none !important; }

@media print {
    #ctrl-panel { display: none !important; }
    body { padding-top: 0 !important; margin-top: 0 !important; }
    .hidden { display: none !important; }
}
#ctrl-panel {
    position: fixed;
    top: 0; left: 0; right: 0;
    background: #1c3f6e;
    color: #fff;
    padding: 6px 14px;
    font-family: Arial, sans-serif;
    font-size: 11.5px;
    z-index: 99999;
    box-shadow: 0 3px 10px rgba(0,0,0,0.4);
}
.ctrl-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 8px;
    align-items: center;
    min-height: 34px;
}
.ctrl-sep {
    color: rgba(255,255,255,0.4);
    font-size: 10px;
    padding: 0 2px;
    white-space: nowrap;
}
.ctrl-group-title {
    font-size: 10px;
    font-weight: bold;
    color: rgba(255,255,255,0.6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}
.ctrl-label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    padding: 2px 8px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    user-select: none;
    white-space: nowrap;
}
.ctrl-label:hover { background: rgba(255,255,255,0.22); }
.ctrl-label input { cursor: pointer; width:12px; height:12px; accent-color:#2a8a36; }
.ctrl-label.unchecked { opacity: 0.45; text-decoration: line-through; }
.ctrl-label.sub { font-size: 10.5px; background: rgba(255,255,255,0.07); font-style: italic; }
#print-btn {
    background: #2a8a36;
    color: #fff;
    border: none;
    padding: 5px 16px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
    margin-left: auto;
    white-space: nowrap;
    flex-shrink: 0;
}
#print-btn:hover { background: #237030; }
body { padding-top: 72px; box-sizing: border-box; }
</style>

<div id="ctrl-panel">
  <!-- LIGNE 1 : pages entières -->
  <div class="ctrl-row">
    <span class="ctrl-group-title">Pages :</span>

    <label class="ctrl-label" id="lbl-page-garde">
      <input type="checkbox" checked onchange="toggle('page-garde',this)"> Page de garde
    </label>
    <label class="ctrl-label" id="lbl-bilan-60">
      <input type="checkbox" checked onchange="toggle('bilan-60',this)"> Bilan 60°/s
    </label>
    <label class="ctrl-label" id="lbl-bilan-240">
      <input type="checkbox" checked onchange="toggle('bilan-240',this)"> Bilan 240°/s
    </label>
    <label class="ctrl-label" id="lbl-analyse-clinique">
      <input type="checkbox" checked onchange="toggle('analyse-clinique',this)"> Analyse clinique
    </label>
    <label class="ctrl-label" id="lbl-bilan-vald">
      <input type="checkbox" checked onchange="toggle('bilan-vald',this)"> VALD (ancien)
    </label>
    <label class="ctrl-label" id="lbl-excentrique">
      <input type="checkbox" checked onchange="toggle('excentrique',this)"> Excentrique
    </label>
    <label class="ctrl-label" id="lbl-vald-tableau">
      <input type="checkbox" checked onchange="toggle('vald-tableau',this)"> VALD tableau
    </label>
    <label class="ctrl-label" id="lbl-vald-manuel">
      <input type="checkbox" checked onchange="toggle('vald-manuel',this)"> VALD ForceDecks
    </label>
    <label class="ctrl-label" id="lbl-gps-catapult">
      <input type="checkbox" checked onchange="toggle('gps-catapult',this)"> GPS Catapult
    </label>
    <label class="ctrl-label" id="lbl-conclusion-programme">
      <input type="checkbox" checked onchange="toggle('conclusion-programme',this)"> Synthèse / Conclusion
    </label>

    <button id="print-btn" onclick="window.print()">🖨 Imprimer / PDF</button>
  </div>

  <!-- LIGNE 2 : sous-sections -->
  <div class="ctrl-row" style="padding-top:3px;border-top:1px solid rgba(255,255,255,0.15);margin-top:3px;">
    <span class="ctrl-group-title">Sections :</span>

    <label class="ctrl-label sub" id="lbl-guard-fonctionnel">
      <input type="checkbox" checked onchange="toggle('guard-fonctionnel',this)"> Bilan fonctionnel
    </label>
    <label class="ctrl-label sub" id="lbl-guard-resume">
      <input type="checkbox" checked onchange="toggle('guard-resume',this)"> Résumé du séjour
    </label>
  </div>
</div>

<script>
// Initialisation : cacher les labels des pages absentes du rapport
document.addEventListener('DOMContentLoaded', function() {
    var allIds = [
        'page-garde','bilan-60','bilan-240','analyse-clinique',
        'bilan-vald','excentrique','vald-tableau',
        'vald-manuel','gps-catapult','conclusion-programme'
    ];
    allIds.forEach(function(sid) {
        var el  = document.querySelector('[data-section="'+sid+'"]');
        var lbl = document.getElementById('lbl-'+sid);
        if (!el && lbl) lbl.style.display = 'none';
    });
    // Sous-sections
    ['guard-fonctionnel','guard-resume'].forEach(function(sid) {
        var el  = document.querySelector('[data-subsection="'+sid+'"]');
        var lbl = document.getElementById('lbl-'+sid);
        if (!el && lbl) lbl.style.display = 'none';
    });
});

// toggle() gère PAGES (data-section) ET SOUS-SECTIONS (data-subsection)
function toggle(sid, checkbox) {
    var sel = '[data-section="'+sid+'"],[data-subsection="'+sid+'"]';
    var els = document.querySelectorAll(sel);
    var lbl = document.getElementById('lbl-'+sid);
    els.forEach(function(el) {
        if (checkbox.checked) {
            el.style.display = '';
            el.classList.remove('hidden');
        } else {
            el.style.display = 'none';
            el.classList.add('hidden');
        }
    });
    if (lbl) lbl.classList.toggle('unchecked', !checkbox.checked);
}
</script>
"""

    if '<body' in html:
        html = _re.sub(r'(<body[^>]*>)', r'\1\n' + panneau, html, count=1)
    else:
        html = panneau + html

    return html


# ── Layout ────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 1.1], gap="large")


# ╔══════════════════════════════════════╗
# ║       COLONNE GAUCHE — INPUTS       ║
# ╚══════════════════════════════════════╝
with col_left:

    # 1. PDFs Biodex
    st.markdown('<div class="card"><div class="card-title">📄 Fichiers Biodex</div>',
                unsafe_allow_html=True)

    col_e, col_s = st.columns(2)
    with col_e:
        pdf_entree = st.file_uploader(
            "📥 Test d'ENTRÉE (optionnel si Sortie fournie)", type=["pdf"], key="up_entree"
        )
    with col_s:
        pdf_sortie = st.file_uploader(
            "📤 Test de SORTIE (optionnel si Entrée fournie)", type=["pdf"], key="up_sortie"
        )

    if not pdf_entree and not pdf_sortie:
        st.info("💡 Fournissez au moins un PDF Biodex (Entrée **ou** Sortie) pour générer le rapport.")
    elif not pdf_entree:
        st.warning("⚠️ PDF Entrée absent — le PDF Sortie sera utilisé comme référence unique (progression = 0%).")
    elif not pdf_sortie:
        st.warning("⚠️ PDF Sortie absent — le PDF Entrée sera utilisé comme référence unique (progression = 0%).")

    with st.expander("📎 PDFs optionnels"):
        co1, co2, co3, co4 = st.columns(4)
        with co1:
            pdf_exc = st.file_uploader(
                "Excentrique 30°/s", type=["pdf"], key="up_exc"
            )
        with co2:
            pdf_comp = st.file_uploader(
                "Comparatif Lésé", type=["pdf"], key="up_comp"
            )
        with co3:
            pdf_comp_sain = st.file_uploader(
                "Comparatif Sain", type=["pdf"], key="up_comp_sain"
            )
        with co4:
            pdf_cr = st.file_uploader(
                "Compte-rendu médical",
                type=["pdf"], key="up_cr",
                help="PDF compte-rendu CERS — extrait diagnostic, intervention, bilan clinique"
            )

    cols_b = st.columns(6)
    statuts = [
        (pdf_entree,    "Entrée",      False),
        (pdf_sortie,    "Sortie",      False),
        (pdf_exc,       "Excentrique", False),
        (pdf_comp,      "Comp.Lésé",   False),
        (pdf_comp_sain, "Comp.Sain",   False),
        (pdf_cr,        "Compte-rendu",False),
    ]
    for col, (pdf, label, obligatoire) in zip(cols_b, statuts):
        with col:
            if pdf:
                cls, ico = "badge-ok", "✅"
            elif obligatoire:
                cls, ico = "badge-wait", "⏳"
            else:
                cls, ico = "badge-opt", "○"
            st.markdown(
                f'<span class="badge {cls}">{ico} {label}</span>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # 1b. VALD ForceDecks — saisie manuelle (3 tableaux)
    # Utilise st.number_input individuel par cellule (stable, pas de double-saisie)
    _VALD_TESTS = {
        "cmj": {
            "label": "CMJ",
            "inds": [
                "Jump Height (cm)",
                "Peak Power / BM (W/kg)",
                "RSI Modified (m/s)",
                "Concentric Impulse (%)",
                "Peak Landing Force (%)",
            ],
        },
        "dj": {
            "label": "Drop Jump",
            "inds": [
                "Jump Height (cm)",
                "Peak Power / BM (W/kg)",
                "RSI JH — Flight Time / Contact Time (m/s)",
                "Peak Landing Force (%)",
            ],
        },
        "slj": {
            "label": "SLJ",
            "inds": [
                "Max Jump Height (cm)",
                "RSI Modified (m/s)",
                "Eccentric Braking RFD / BM (N/s)",
            ],
        },
    }

    def _safe_float(s):
        if s is None or str(s).strip() == "":
            return None
        try:
            return float(str(s).replace(",", ".").strip())
        except (ValueError, TypeError):
            return None

    def _prog(e, s):
        ev, sv = _safe_float(e), _safe_float(s)
        if ev is None or sv is None or ev == 0:
            return None
        return round((sv - ev) / abs(ev) * 100, 1)

    def _delete_vald_row(test_key, idx):
        inds = st.session_state[f"vald_{test_key}_inds"]
        n = len(inds)
        for j in range(idx, n - 1):
            for sfx in ["e", "s"]:
                st.session_state[f"v_{test_key}_{sfx}_{j}"] = st.session_state.get(f"v_{test_key}_{sfx}_{j+1}", "")
        for sfx in ["e", "s"]:
            st.session_state.pop(f"v_{test_key}_{sfx}_{n-1}", None)
        inds.pop(idx)
        st.rerun()

    # Init listes d'indicateurs dans session_state
    for _tk, _tv in _VALD_TESTS.items():
        _sk = f"vald_{_tk}_inds"
        if _sk not in st.session_state:
            st.session_state[_sk] = list(_tv["inds"])

    def _render_vald_tab(test_key):
        inds = st.session_state[f"vald_{test_key}_inds"]

        hc = st.columns([3.0, 1.3, 1.3, 1.7, 0.45])
        hc[0].markdown("**Indicateur**")
        hc[1].markdown("**Entrée**")
        hc[2].markdown("**Sortie**")
        hc[3].markdown("**Progression**")
        st.markdown('<hr style="margin:2px 0 4px 0;border-color:#d0dae8;">', unsafe_allow_html=True)

        for i, ind in enumerate(inds):
            rc = st.columns([3.0, 1.3, 1.3, 1.7, 0.45])
            rc[0].write(ind)
            # text_input : compatible toutes versions Streamlit (pas de min_value/format)
            e_str = rc[1].text_input("", key=f"v_{test_key}_e_{i}",
                                     label_visibility="collapsed", placeholder="0.00")
            s_str = rc[2].text_input("", key=f"v_{test_key}_s_{i}",
                                     label_visibility="collapsed", placeholder="0.00")
            p = _prog(e_str, s_str)
            if p is not None:
                arrow = "↑" if p >= 0 else "↓"
                rc[3].markdown(
                    f'<span style="color:{"#1a7a30" if p>=0 else "#c0392b"};'
                    f'font-weight:700;font-size:13px;">{arrow} {abs(p):.1f} %</span>',
                    unsafe_allow_html=True,
                )
            else:
                rc[3].markdown('<span style="color:#aaa;">—</span>', unsafe_allow_html=True)
            if rc[4].button("🗑️", key=f"v_{test_key}_del_{i}", help="Supprimer cette ligne"):
                _delete_vald_row(test_key, i)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        ac = st.columns([3.5, 1.8])
        new_ind = ac[0].text_input("", key=f"v_{test_key}_new",
                                   label_visibility="collapsed",
                                   placeholder="Ajouter un indicateur...")
        if ac[1].button("＋ Ajouter", key=f"v_{test_key}_add"):
            if new_ind.strip():
                st.session_state[f"vald_{test_key}_inds"].append(new_ind.strip())
                st.session_state.pop(f"v_{test_key}_new", None)
                st.rerun()

    def _collect_vald_rows(test_key):
        inds = st.session_state.get(f"vald_{test_key}_inds", [])
        rows = []
        for i, ind in enumerate(inds):
            e = _safe_float(st.session_state.get(f"v_{test_key}_e_{i}", ""))
            s = _safe_float(st.session_state.get(f"v_{test_key}_s_{i}", ""))
            if e is not None or s is not None:
                rows.append({
                    "indicateur":  ind,
                    "entree":      e,
                    "sortie":      s,
                    "progression": _prog(e, s),
                })
        return rows

    slj_data, cmj_data = None, None   # compatibilité ascendante

    with st.expander("🏋️ VALD ForceDecks — Saisie manuelle (optionnel)", expanded=False):
        tab_cmj, tab_dj, tab_slj = st.tabs(["CMJ", "Drop Jump", "SLJ"])
        with tab_cmj:  _render_vald_tab("cmj")
        with tab_dj:   _render_vald_tab("dj")
        with tab_slj:  _render_vald_tab("slj")

        st.markdown("---")
        if st.button("↺ Réinitialiser tous les tableaux VALD", key="reset_vald"):
            for _tk, _tv in _VALD_TESTS.items():
                st.session_state[f"vald_{_tk}_inds"] = list(_tv["inds"])
                n = len(_tv["inds"]) + 5
                for i in range(n):
                    for sfx in ["e", "s"]:
                        st.session_state.pop(f"v_{_tk}_{sfx}_{i}", None)
                st.session_state.pop(f"v_{_tk}_new", None)
            st.rerun()

    vald_manual = {
        "cmj": _collect_vald_rows("cmj"),
        "dj":  _collect_vald_rows("dj"),
        "slj": _collect_vald_rows("slj"),
    }
    _has_vald_manual = any(vald_manual[k] for k in vald_manual)

    # Parsing compte-rendu médical
    cr_data = None
    if pdf_cr:
        try:
            import io as _io
            cr_data = parse_compte_rendu(_io.BytesIO(pdf_cr.getvalue()))
            infos = []
            if cr_data.get("diagnostic"):
                infos.append(f"Diagnostic : {cr_data['diagnostic']}")
            if cr_data.get("club"):
                infos.append(f"Club : {cr_data['club']}")
            if cr_data.get("medecin_responsable"):
                infos.append(f"Dr {cr_data['medecin_responsable']}")
            st.success("CR médical lu · " + " · ".join(infos[:3]))
        except Exception as _e:
            st.error(f"Erreur CR médical : {_e}")

    # Valeurs par défaut (accessibles même si les expanders ne sont pas ouverts)
    remarques_medecin = ""
    programme_kine    = ""
    programme_prepa   = ""
    conclusion_sortie = ""
    gps_data          = None   # doit être AVANT l'expander GPS

    # 1c. GPS Catapult — PDF OpenField
    with st.expander("📡 GPS Catapult — PDF OpenField (optionnel)"):
        pdf_gps = st.file_uploader(
            "Rapport GPS Catapult — PDF OpenField",
            type=["pdf"], key="up_gps"
        )
        if pdf_gps:
            try:
                import tempfile as _tmp
                with _tmp.NamedTemporaryFile(delete=False, suffix=".pdf") as _tf:
                    _tf.write(pdf_gps.read())
                    _gps_path = _tf.name
                gps_data = parse_gps_pdf(_gps_path)
                os.unlink(_gps_path)
                st.success(f"GPS chargé : {gps_data['meta']['n_sessions']} sessions · {gps_data['meta']['n_semaines']} semaines · {gps_data['meta']['periode']}")
            except Exception as _e:
                st.error(f"Erreur lecture GPS : {_e}")
                gps_data = None

    # 2. Informations complémentaires patient — A2 (placeholder mis à jour)
    with st.expander("⚙️ Informations complémentaires patient", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            sport = st.selectbox("Sport", [
                "— Sélectionner —", "Rugby", "Football", "Basketball",
                "Handball", "Tennis", "Natation", "Athlétisme", "Autre"
            ], key="sport_sel")
        with c2:
            date_operation = st.date_input(
                "Date d'opération (optionnel)",
                value=None,
                format="DD/MM/YYYY",
                key="date_op"
            )
        with c3:
            blessures_liste, _ = charger_blessures()
            type_blessure = st.selectbox(
                "Type de blessure (optionnel)",
                options=["— Sélectionner —"] + blessures_liste,
                key="blessure_select"
            )
            if type_blessure == "— Sélectionner —":
                type_blessure = ""
            with st.expander("➕ Blessure absente de la liste ?"):
                nouvelle_blessure = st.text_input(
                    "Nom de la blessure",
                    placeholder="Ex: Ostéite pubienne...",
                    key="nouvelle_blessure"
                )
                if st.button("Ajouter à la liste", key="btn_add_blessure"):
                    if nouvelle_blessure and nouvelle_blessure != "— Sélectionner —":
                        sauvegarder_blessure_custom(nouvelle_blessure)
                        st.success(f"'{nouvelle_blessure}' ajoutée !")
                        st.rerun()

        c4, c5, c6 = st.columns(3)
        with c4:
            acl_rsi_score = st.number_input(
                "Score ACL-RSI % (optionnel)",
                min_value=0, max_value=100, value=0, step=1, key="acl"
            )
        with c5:
            photo = st.file_uploader(
                "📸 Photo joueur (optionnel)",
                type=["png", "jpg", "jpeg"], key="up_photo"
            )
        with c6:
            pass

        remarques_medecin = st.text_area(
            "Remarques médicales (optionnel)",
            placeholder="Zone libre pour le professionnel de santé (médecin, kinésithérapeute...)...",
            height=70, key="remarques"
        )

        st.markdown("---")
        st.caption("📋 Programme de rééducation (optionnel — apparaît dans la dernière page du rapport)")
        ck, cp = st.columns(2)
        with ck:
            programme_kine = st.text_area(
                "Programme kinésithérapie",
                placeholder="Ex:\nSemaine 1-2 : Drainage, mobilisation passive, isométrique quadriceps\nSemaine 3-4 : Renforcement progressif, proprioception statique\nSemaine 5-8 : Renforcement dynamique, proprioception dynamique\nSemaine 8+ : Travail fonctionnel, course légère",
                height=100, key="prog_kine"
            )
        with cp:
            programme_prepa = st.text_area(
                "Programme préparation physique",
                placeholder="Ex:\nPhase 1 : Vélo, gainage statique, renforcement global\nPhase 2 : Pliométrie basse intensité, travail cardio\nPhase 3 : Course progressive, exercices sport-spécifiques\nPhase 4 : Intensification, retour au jeu",
                height=100, key="prog_prepa"
            )
        conclusion_sortie = st.text_area(
            "Conclusion de sortie / Recommandations (optionnel)",
            placeholder="Conclusion médicale personnalisée et recommandations pour la suite de la rééducation à domicile...",
            height=65, key="conclusion_sortie"
        )

    # Variables avec valeurs par défaut
    date_naissance = None
    cote_opere = ""

    # 3. Club du joueur — A1
    clubs_db_locale = charger_clubs_db()
    logo_club_upload = None  # sera défini dans l'expander

    with st.expander("🏆 Club du joueur", expanded=False):

        recherche_club = st.text_input(
            "Rechercher un club enregistré",
            placeholder="Ex: Oyonnax, Clermont...",
            key="search_club"
        )

        if recherche_club and len(recherche_club) >= 2:
            matches = {k: v for k, v in clubs_db_locale.items()
                       if recherche_club.lower() in k}
            if matches:
                for cle, cdata in list(matches.items())[:4]:
                    col_l, col_b = st.columns([1, 5])
                    with col_l:
                        if cdata.get("logo_b64"):
                            st.markdown(
                                f'<img src="{cdata["logo_b64"]}" style="height:32px;border-radius:4px;">',
                                unsafe_allow_html=True
                            )
                    with col_b:
                        if st.button(
                            f"{cdata.get('nom', cle)}  ·  {cdata.get('sport', '')}",
                            key=f"loc_{cle}", use_container_width=True
                        ):
                            st.session_state.club_selectionne = cdata
                            st.session_state.nom_club_cache = cdata.get("nom", cle)
                            st.rerun()
            else:
                resultats = search_clubs(recherche_club)
                for club in resultats[:4]:
                    logo_b64 = get_logo(club["nom"], club["couleur"])
                    col_l, col_b = st.columns([1, 5])
                    with col_l:
                        st.markdown(
                            f'<img src="{logo_b64}" style="height:32px;border-radius:4px;">',
                            unsafe_allow_html=True
                        )
                    with col_b:
                        if st.button(
                            f"{club['nom']}  ·  {club['sport']} — {club['division']}",
                            key=f"db_{club['nom']}", use_container_width=True
                        ):
                            st.session_state.club_selectionne = club
                            st.session_state.nom_club_cache = club["nom"]
                            st.rerun()
                if not resultats:
                    st.info("Aucun club trouvé — remplir le formulaire ci-dessous.")

        st.markdown("---")
        st.caption("Nouveau club ou modification")

        cn1, cn2 = st.columns(2)
        with cn1:
            club_nouveau_nom = st.text_input(
                "Nom du club *", placeholder="Ex: Oyonnax Rugby", key="club_nom_new"
            )
        with cn2:
            club_nouveau_sport = st.selectbox(
                "Sport", ["Rugby", "Football", "Basketball",
                          "Handball", "Volleyball", "Autre"],
                key="club_sport_new"
            )

        logo_club_upload = st.file_uploader(
            "Logo du club (PNG recommandé)", type=["png", "jpg", "jpeg"],
            key="up_logo_club"
        )
        if logo_club_upload:
            st.image(logo_club_upload, width=80)

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("✅ Utiliser ce club", use_container_width=True, key="btn_use"):
                if club_nouveau_nom:
                    new_club = {
                        "nom": club_nouveau_nom,
                        "sport": club_nouveau_sport,
                        "division": "Autre",
                        "couleur": "#1c3f6e",
                    }
                    st.session_state.club_selectionne = new_club
                    st.session_state.nom_club_cache = club_nouveau_nom
                    st.rerun()
        with cb2:
            if st.button("💾 Enregistrer dans la base", use_container_width=True, key="btn_save"):
                if club_nouveau_nom:
                    logo_b64_save = None
                    if logo_club_upload:
                        import base64 as _b64
                        ext = logo_club_upload.name.rsplit(".", 1)[-1].lower()
                        mime = "image/png" if ext == "png" else "image/jpeg"
                        logo_b64_save = (f"data:{mime};base64,"
                                         + _b64.b64encode(logo_club_upload.getvalue()).decode())
                    new_club = {
                        "nom": club_nouveau_nom,
                        "sport": club_nouveau_sport,
                        "division": "Autre",
                        "couleur": "#1c3f6e",
                        "logo_b64": logo_b64_save,
                    }
                    sauvegarder_club_db(club_nouveau_nom, new_club)
                    st.session_state.club_selectionne = new_club
                    st.session_state.nom_club_cache = club_nouveau_nom
                    st.success(f"'{club_nouveau_nom}' enregistré — logo inclus !")
                    st.rerun()
                else:
                    st.warning("Renseigner le nom du club avant d'enregistrer.")

    # Bandeau club (hors expander, toujours visible si sélectionné)
    if st.session_state.club_selectionne:
        club = st.session_state.club_selectionne
        logo_src = club.get("logo_b64") or get_logo(club["nom"], club.get("couleur", "#1c3f6e"))
        col_cl, col_chg = st.columns([5, 1])
        with col_cl:
            st.markdown(f"""
<div class="club-selected">
  <img src="{logo_src}" style="height:35px;border-radius:6px;">
  <div>
    <div style="font-size:14px;">{club['nom']}</div>
    <div style="font-size:11px;color:#555;font-weight:400;">
      {club.get('sport', '')} — {club.get('division', '')}
    </div>
  </div>
</div>""", unsafe_allow_html=True)
        with col_chg:
            if st.button("✏️ Changer", key="chg_club"):
                st.session_state.club_selectionne = None
                st.rerun()
    else:
        st.markdown('<span class="badge badge-wait">⏳ Aucun club sélectionné</span>',
                    unsafe_allow_html=True)


# ╔══════════════════════════════════════════╗
# ║     COLONNE DROITE — APERÇU + GÉNÉRATION ║
# ╚══════════════════════════════════════════╝
with col_right:

    # Aperçu données
    st.markdown('<div class="card"><div class="card-title">📋 Aperçu des données</div>', unsafe_allow_html=True)

    entree_data = None
    sortie_data = None

    if pdf_entree or pdf_sortie:
        with st.spinner("Lecture des PDFs..."):
            try:
                from biodex_parser import parse_biodex_pdf

                pdf_a = pdf_entree or pdf_sortie
                pdf_b = pdf_sortie or pdf_entree

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_a.getvalue()); path_e_prev = f.name
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_b.getvalue()); path_s_prev = f.name

                entree_data = parse_biodex_pdf(path_e_prev)
                sortie_data = parse_biodex_pdf(path_s_prev)
                os.unlink(path_e_prev); os.unlink(path_s_prev)

                lbl_e = "Entrée" if pdf_entree else "Sortie (utilisée comme référence)"
                lbl_s = "Sortie" if pdf_sortie else "Entrée (utilisée comme référence)"
                st.success(f"✅ {entree_data.nom} — PDFs lus avec succès")

                c_nom, c_infos = st.columns([1.2, 1])
                with c_nom:
                    st.markdown(f"""
**👤 {entree_data.nom}**
- Âge : {entree_data.age} ans
- {entree_data.poids_kg} kg  |  {entree_data.taille_cm} cm
- Lésion : **{entree_data.articulation} {entree_data.lese}**
                    """)
                with c_infos:
                    st.markdown(f"""
📅 **Entrée :** {entree_data.date_test}
📅 **Sortie :** {sortie_data.date_test}
🏋️ **Sport :** {sport if sport != "— Sélectionner —" else "—"}
🏆 **Club :** {st.session_state.club_selectionne['nom'] if st.session_state.club_selectionne else '—'}
                    """)

                if entree_data.serie_60 and sortie_data.serie_60:
                    e60 = entree_data.serie_60; s60 = sortie_data.serie_60

                    def prog_str(e, s):
                        if e and s and e != 0:
                            p = round(((s-e)/abs(e))*100, 1)
                            return f"{'▲' if p>=0 else '▼'} {p:+.1f}%"
                        return "—"

                    rows = [
                        ["Moment Max Extension", f"{e60.ext_moment_max.lese_g} N·m", f"{s60.ext_moment_max.lese_g} N·m", prog_str(e60.ext_moment_max.lese_g, s60.ext_moment_max.lese_g)],
                        ["Moment Max Flexion",   f"{e60.flex_moment_max.lese_g} N·m", f"{s60.flex_moment_max.lese_g} N·m", prog_str(e60.flex_moment_max.lese_g, s60.flex_moment_max.lese_g)],
                        ["Ratio I/Q",            f"{e60.ratio_lese_g}%", f"{s60.ratio_lese_g}%", prog_str(e60.ratio_lese_g, s60.ratio_lese_g)],
                    ]
                    header = f"<tr><th>Métrique (Lésé G)</th><th>Entrée {entree_data.date_test}</th><th>Sortie {sortie_data.date_test}</th><th>Progression</th></tr>"
                    trs = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in rows)
                    st.markdown(f'<table class="preview-table">{header}{trs}</table>', unsafe_allow_html=True)

            except Exception as ex:
                st.error(f"❌ Erreur lecture PDF : {ex}")
    else:
        st.markdown('<div class="info-box">👈 Dépose les 2 PDFs Biodex pour voir l\'aperçu.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Génération
    st.markdown('<div class="card"><div class="card-title">🚀 Générer le Rapport PDF</div>', unsafe_allow_html=True)

    if not pdf_entree and not pdf_sortie:
        st.info("ℹ️ Sans PDF Biodex, le rapport contiendra uniquement les données CR / VALD / GPS disponibles.")

    btn_gen = st.button("🔄  Générer le Rapport PDF Complet", use_container_width=True)

    if btn_gen:

        club = st.session_state.get("club_selectionne")
        nom_club = (club["nom"] if club else "") or st.session_state.get("nom_club_cache", "")
        progress = st.progress(0, text="Initialisation...")

        try:
            from generate_rapport import generer_rapport_biodex

            progress.progress(10, text="📄 Sauvegarde des fichiers...")

            # Sauvegarder PDFs Biodex (gestion des PDFs manquants — fallback dans generate_rapport.py)
            path_e = None
            if pdf_entree:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_entree.getvalue()); path_e = f.name

            path_s = None
            if pdf_sortie:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_sortie.getvalue()); path_s = f.name

            path_comp = None
            if pdf_comp:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_comp.getvalue()); path_comp = f.name

            path_comp_sain = None
            if pdf_comp_sain:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_comp_sain.getvalue()); path_comp_sain = f.name

            path_exc = None
            if pdf_exc:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_exc.getvalue()); path_exc = f.name

            path_photo = None
            if photo:
                ext_ph = photo.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(suffix=f".{ext_ph}", delete=False) as f:
                    f.write(photo.getvalue()); path_photo = f.name

            # Logo club — A4 : priorité upload session, sinon logo_b64 depuis clubs_db
            path_logo_club = None
            club_selec = st.session_state.get("club_selectionne")

            if logo_club_upload:
                ext_logo = logo_club_upload.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(suffix=f".{ext_logo}", delete=False) as f:
                    f.write(logo_club_upload.getvalue())
                    path_logo_club = f.name

            elif club_selec and club_selec.get("logo_b64"):
                import base64 as _b64
                logo_data = club_selec["logo_b64"]
                if ";base64," in logo_data:
                    header_part, b64_str = logo_data.split(";base64,", 1)
                    ext_logo = "png" if "png" in header_part else "jpg"
                    with tempfile.NamedTemporaryFile(suffix=f".{ext_logo}", delete=False) as f:
                        f.write(_b64.b64decode(b64_str))
                        path_logo_club = f.name

            progress.progress(30, text="🔍 Parsing des PDFs Biodex...")

            # Dossier de sortie FIXE (obligatoire pour pdfkit sur Windows)
            out_dir  = os.path.join(_APP_DIR, "outputs")
            os.makedirs(out_dir, exist_ok=True)
            out_html = os.path.join(out_dir, "rapport_temp.html")
            out_pdf  = os.path.join(out_dir, "rapport_temp.pdf")

            progress.progress(60, text="📊 Calcul + graphiques en cours...")

            result = generer_rapport_biodex(
                pdf_entree              = path_e,
                pdf_sortie              = path_s,
                pdf_comparatif          = path_comp,
                pdf_comparatif_sain     = path_comp_sain,
                pdf_excentrique         = path_exc,
                slj_data                = slj_data,
                cmj_data                = cmj_data,
                output_html             = out_html,
                output_pdf              = out_pdf,
                template_dir            = os.path.join(_APP_DIR, "templates"),
                nom_club                = nom_club,
                logo_club_path          = path_logo_club,
                photo_patient_path      = path_photo,
                sport                   = sport if sport != "— Sélectionner —" else "",
                date_naissance          = str(date_naissance) if date_naissance else "",
                date_operation          = date_operation.strftime("%d/%m/%Y") if date_operation else "",
                type_blessure           = type_blessure,
                cote_opere              = cote_opere,
                acl_rsi_score           = acl_rsi_score if acl_rsi_score > 0 else None,
                remarques_medecin       = remarques_medecin,
                cr_data                 = cr_data,
                programme_kine          = programme_kine,
                programme_prepa         = programme_prepa,
                conclusion_sortie       = conclusion_sortie,
                gps_data               = gps_data,
                vald_manual            = vald_manual if _has_vald_manual else None,
            )

            progress.progress(90, text="📄 Traitement du résultat...")

            # Gérer dict (nouvelle version) ou str (ancienne version)
            if isinstance(result, dict):
                html_bytes = result.get("html_bytes")
                pdf_bytes  = result.get("pdf_bytes")
                chemin     = result.get("pdf_path", "")
            else:
                chemin = result
                pdf_bytes  = None
                html_bytes = None
                if chemin and os.path.exists(chemin):
                    with open(chemin, "rb") as f:
                        if chemin.endswith(".pdf"):
                            pdf_bytes = f.read()
                        else:
                            html_bytes = f.read()
                if html_bytes is None and os.path.exists(out_html):
                    with open(out_html, "rb") as f:
                        html_bytes = f.read()

            progress.progress(100, text="✅ Rapport prêt !")

            _primary_data = entree_data or sortie_data
            nom_patient  = (_primary_data.nom.replace(" ", "_").replace(".", "") if _primary_data else "patient")
            nom_club_safe = (nom_club or "club").replace(" ", "_")
            nom_base     = f"Rapport_{nom_patient}_{nom_club_safe}"

            st.session_state.rapport_html_bytes = html_bytes
            st.session_state.rapport_pdf_bytes  = pdf_bytes
            st.session_state.rapport_nom_base   = nom_base

            # Nettoyer fichiers temporaires
            for p in [path_e, path_s, path_comp, path_comp_sain, path_exc,
                      path_photo, path_logo_club]:
                if p and os.path.exists(p):
                    try: os.unlink(p)
                    except: pass

        except Exception as ex:
            st.error(f"❌ Erreur : {ex}")
            import traceback
            with st.expander("Détails de l'erreur"):
                st.code(traceback.format_exc())

    # Téléchargement
    if st.session_state.get("rapport_html_bytes") or st.session_state.get("rapport_pdf_bytes"):
        st.markdown("""
<div class="success-box">
  <h3>&#10003; Rapport g&#233;n&#233;r&#233; !</h3>
  <p>T&#233;l&#233;charger en PDF, ou en HTML pour personnaliser avant impression</p>
</div>""", unsafe_allow_html=True)

        nom_base = st.session_state.get("rapport_nom_base", "rapport")
        col1, col2 = st.columns(2)

        with col1:
            pdf_b = st.session_state.get("rapport_pdf_bytes")
            if pdf_b:
                st.download_button(
                    label="⬇️ Télécharger PDF",
                    data=pdf_b,
                    file_name=f"{nom_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_pdf",
                )
            else:
                st.info("PDF non disponible sur ce serveur.")

        with col2:
            html_b = st.session_state.get("rapport_html_bytes")
            if html_b:
                html_interactif = _injecter_panneau_personnalisation(
                    html_b.decode("utf-8")
                )
                st.download_button(
                    label="🎛️ Personnaliser puis imprimer (HTML)",
                    data=html_interactif.encode("utf-8"),
                    file_name=f"{nom_base}_personnalisable.html",
                    mime="text/html",
                    use_container_width=True,
                    key="dl_html",
                )

    st.markdown('</div>', unsafe_allow_html=True)


# Footer
st.markdown("---")
st.markdown('<div style="text-align:center;color:#888;font-size:11px;">CERS Capbreton • Groupe Ramsay Santé • Bilan Isocinétique Biodex v6 • 4 sports • 112 clubs</div>', unsafe_allow_html=True)
