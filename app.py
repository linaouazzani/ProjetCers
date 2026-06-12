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
from cr_parser import parse_compte_rendu
from gps_parser import parse_gps_pdf
from database import rechercher_clubs, enregistrer_club, get_club

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
    """Compatibilité ascendante — retourne les clubs custom depuis SQLite."""
    from database import lister_clubs_custom
    clubs = lister_clubs_custom()
    return {c["nom"].lower(): c for c in clubs}


def sauvegarder_club_db(nom: str, data: dict):
    """Compatibilité ascendante — délègue à SQLite."""
    enregistrer_club(
        nom      = nom,
        sport    = data.get("sport", "Autre"),
        division = data.get("division", "Autre"),
        couleur  = data.get("couleur", "#1c3f6e"),
        logo_b64 = data.get("logo_b64"),
    )


# ── État session ──────────────────────────────────────────────────────────────

if "club_selectionne" not in st.session_state:
    st.session_state.club_selectionne = None
if "nom_club_cache" not in st.session_state:
    st.session_state.nom_club_cache = ""
if "rapport_html_bytes" not in st.session_state:
    st.session_state.rapport_html_bytes = None
if "rapport_nom_base" not in st.session_state:
    st.session_state.rapport_nom_base = None
# Purge any legacy PDF bytes still in session state from a previous run
st.session_state.pop("rapport_pdf_bytes", None)
# Upload locks — once set, uploaders are frozen until Rafraîchir / page reload
for _uk in ["pdf_entree", "pdf_sortie", "pdf_exc", "pdf_comp", "pdf_comp_sain", "pdf_cr"]:
    if f"locked_{_uk}" not in st.session_state:
        st.session_state[f"locked_{_uk}"] = None  # None = not uploaded; bytes = locked


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
    """Le template rapport.html embarque déjà #ctrl-bar complet.
    Cette fonction est conservée pour compatibilité mais ne modifie plus le HTML.
    """

    _panneau_legacy = """
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

  <!-- LIGNE 2 : sous-sections page de garde -->
  <div class="ctrl-row" style="padding-top:3px;border-top:1px solid rgba(255,255,255,0.15);margin-top:3px;">
    <span class="ctrl-group-title">Page de garde :</span>

    <label class="ctrl-label sub" id="lbl-guard-hero">
      <input type="checkbox" checked onchange="toggle('guard-hero',this)"> Photo / Infos patient
    </label>
    <label class="ctrl-label sub" id="lbl-guard-info-bande">
      <input type="checkbox" checked onchange="toggle('guard-info-bande',this)"> S&#233;jour / M&#233;decin / C&#244;t&#233;
    </label>
    <label class="ctrl-label sub" id="lbl-guard-diagnostic">
      <input type="checkbox" checked onchange="toggle('guard-diagnostic',this)"> Diagnostic + Intervention
    </label>
    <label class="ctrl-label sub" id="lbl-guard-antecedents">
      <input type="checkbox" checked onchange="toggle('guard-antecedents',this)"> Ant&#233;c&#233;dents
    </label>
    <label class="ctrl-label sub" id="lbl-guard-fonctionnel">
      <input type="checkbox" checked onchange="toggle('guard-fonctionnel',this)"> Bilan fonctionnel
    </label>
    <label class="ctrl-label sub" id="lbl-guard-resume">
      <input type="checkbox" checked onchange="toggle('guard-resume',this)"> R&#233;sum&#233; du s&#233;jour
    </label>
  </div>
</div>

<script>
var ALL_PAGES = [
    'page-garde','bilan-60','bilan-240','analyse-clinique',
    'bilan-vald','excentrique','vald-tableau',
    'vald-manuel','gps-catapult','conclusion-programme'
];
var ALL_SUBS = [
    'guard-hero','guard-info-bande','guard-diagnostic','guard-antecedents',
    'guard-fonctionnel','guard-resume'
];

// Au chargement : masquer les labels des sections absentes du rapport
document.addEventListener('DOMContentLoaded', function() {
    ALL_PAGES.forEach(function(sid) {
        var el  = document.querySelector('[data-section="'+sid+'"]');
        var lbl = document.getElementById('lbl-'+sid);
        if (!el && lbl) lbl.style.display = 'none';
    });
    ALL_SUBS.forEach(function(sid) {
        var el  = document.querySelector('[data-subsection="'+sid+'"]');
        var lbl = document.getElementById('lbl-'+sid);
        if (!el && lbl) lbl.style.display = 'none';
    });
});

// toggle() : masque/affiche via classe .hidden UNIQUEMENT
// (.hidden { display:none !important } fonctionne aussi à l'impression)
function toggle(sid, checkbox) {
    var sel = '[data-section="'+sid+'"],[data-subsection="'+sid+'"]';
    var els = document.querySelectorAll(sel);
    var lbl = document.getElementById('lbl-'+sid);
    els.forEach(function(el) {
        el.classList.toggle('hidden', !checkbox.checked);
    });
    if (lbl) lbl.classList.toggle('unchecked', !checkbox.checked);
}
</script>
"""

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

    def _locked_uploader(label, key, lock_key, file_type=None, help=None):
        """Show a file uploader or a locked badge. Returns bytes or None."""
        locked = st.session_state.get(f"locked_{lock_key}")
        if locked is not None:
            st.markdown(
                f'<span class="badge badge-ok">✅ {label} — chargé</span>',
                unsafe_allow_html=True,
            )
            return locked
        kwargs = {"type": file_type or ["pdf"], "key": key}
        if help:
            kwargs["help"] = help
        uploaded = st.file_uploader(label, **kwargs)
        if uploaded is not None:
            data = uploaded.getvalue()
            st.session_state[f"locked_{lock_key}"] = data
            return data
        return None

    col_e, col_s = st.columns(2)
    with col_e:
        _raw_entree = _locked_uploader(
            "📥 Test d'ENTRÉE (optionnel si Sortie fournie)", "up_entree", "pdf_entree"
        )
    with col_s:
        _raw_sortie = _locked_uploader(
            "📤 Test de SORTIE (optionnel si Entrée fournie)", "up_sortie", "pdf_sortie"
        )

    # Reconstruct file-like wrappers so downstream code can call .getvalue()
    class _BytesFile:
        def __init__(self, data, name="upload.pdf"):
            self._data = data
            self.name = name
        def getvalue(self):
            return self._data

    pdf_entree = _BytesFile(_raw_entree) if _raw_entree else None
    pdf_sortie = _BytesFile(_raw_sortie) if _raw_sortie else None

    if not pdf_entree and not pdf_sortie:
        st.info("💡 Fournissez au moins un PDF Biodex (Entrée **ou** Sortie) pour générer le rapport.")
    elif not pdf_entree:
        st.warning("⚠️ PDF Entrée absent — le PDF Sortie sera utilisé comme référence unique (progression = 0%).")
    elif not pdf_sortie:
        st.warning("⚠️ PDF Sortie absent — le PDF Entrée sera utilisé comme référence unique (progression = 0%).")

    if st.button("🔄 Rafraîchir les fichiers", key="btn_refresh_uploads", help="Efface tous les fichiers chargés"):
        for _uk in ["pdf_entree", "pdf_sortie", "pdf_exc", "pdf_comp", "pdf_comp_sain", "pdf_cr"]:
            st.session_state[f"locked_{_uk}"] = None
        st.rerun()

    with st.expander("📎 PDFs optionnels"):
        co1, co2, co3, co4 = st.columns(4)
        with co1:
            _raw_exc = _locked_uploader("Excentrique 30°/s", "up_exc", "pdf_exc")
        with co2:
            _raw_comp = _locked_uploader("Comparatif Lésé", "up_comp", "pdf_comp")
        with co3:
            _raw_comp_sain = _locked_uploader("Comparatif Sain", "up_comp_sain", "pdf_comp_sain")
        with co4:
            _raw_cr = _locked_uploader(
                "Compte-rendu médical", "up_cr", "pdf_cr",
                help="PDF compte-rendu CERS — extrait diagnostic, intervention, bilan clinique"
            )

    pdf_exc       = _BytesFile(_raw_exc)       if _raw_exc       else None
    pdf_comp      = _BytesFile(_raw_comp)      if _raw_comp      else None
    pdf_comp_sain = _BytesFile(_raw_comp_sain) if _raw_comp_sain else None
    pdf_cr        = _BytesFile(_raw_cr)        if _raw_cr        else None

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

    # 1b. VALD ForceDecks — saisie manuelle
    # CMJ / DJ : listes dynamiques (ajout/suppression de lignes)
    # SLJ + sections LR : 4 colonnes Ent.G / Ent.D / Sort.G / Sort.D
    _CMJ_IND = [
        "Jump Height (cm)", "Peak Power / BM (W/kg)", "RSI Modified Imp-Mom (m/s)",
        "Eccentric Braking Impulse % Asym", "Concentric Impulse % Asym",
        "Peak Landing Force % Asym",
    ]
    _DJ_IND = [
        "Jump Height (cm)", "Peak Power / BM (W/kg)",
        "RSI JH — Flight Time / Contact Time (m/s)",
        "Eccentric Impulse % Asym", "Concentric Impulse % Asym",
        "Peak Landing Force % Asym",
    ]
    # Sections LR : indicateurs fixes
    _LR_INDS = {
        "slj":          ["Max Jump Height (cm)", "RSI Modified (m/s)", "Eccentric Braking RFD / BM (N/s)"],
        "shoulder":     ["Iso-T — Max Peak Vertical Force (N)", "Iso-T — Max RFD 200ms (N/s)",
                         "Iso-Y — Max Peak Vertical Force (N)", "Iso-Y — Max RFD 200ms (N/s)",
                         "Iso-I — Max Peak Vertical Force (N)", "Iso-I — Max RFD 200ms (N/s)"],
        "mollet_run":   ["Max Peak Specific Force (N)", "Max RFD 200ms (N/s)"],
        "mollet_seated":["Max Peak Vertical Force (N)", "Max RFD 200ms (N/s)"],
        "nordic":       ["Max Force (N)"],
        "imtp":         ["Max Peak Vertical Force (N)", "Max RFD 200ms (N/s)"],
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

    def _prog_html(p):
        if p is None:
            return '<span style="color:#aaa;">—</span>'
        arrow = "↑" if p >= 0 else "↓"
        col = "#1a7a30" if p >= 0 else "#c0392b"
        return f'<span style="color:{col};font-weight:700;font-size:13px;">{arrow} {abs(p):.1f} %</span>'

    # Init session state listes
    for _k, _d in [("cmj", _CMJ_IND), ("dj", _DJ_IND)]:
        if f"vald_{_k}_inds" not in st.session_state:
            st.session_state[f"vald_{_k}_inds"] = list(_d)
    for _k, _d in _LR_INDS.items():
        if f"vald_{_k}_inds" not in st.session_state:
            st.session_state[f"vald_{_k}_inds"] = list(_d)

    # ── Suppression d'une ligne (CMJ/DJ uniquement) ───────────────────
    def _del_row(tk, idx):
        inds = st.session_state[f"vald_{tk}_inds"]
        n = len(inds)
        for j in range(idx, n - 1):
            for sfx in ["e", "s"]:
                st.session_state[f"v_{tk}_{sfx}_{j}"] = st.session_state.get(f"v_{tk}_{sfx}_{j+1}", "")
        for sfx in ["e", "s"]:
            st.session_state.pop(f"v_{tk}_{sfx}_{n-1}", None)
        inds.pop(idx)
        st.rerun()

    # ── Rendu CMJ / DJ (simple Entrée/Sortie + supprimer) ────────────
    def _render_simple(tk):
        inds = st.session_state[f"vald_{tk}_inds"]
        hc = st.columns([3.0, 1.3, 1.3, 1.7, 0.45])
        hc[0].markdown("**Indicateur**"); hc[1].markdown("**Entrée**")
        hc[2].markdown("**Sortie**");     hc[3].markdown("**Progression**")
        st.markdown('<hr style="margin:2px 0 4px 0;border-color:#d0dae8;">', unsafe_allow_html=True)
        for i, ind in enumerate(inds):
            rc = st.columns([3.0, 1.3, 1.3, 1.7, 0.45])
            rc[0].write(ind)
            e = rc[1].text_input(f"e {tk} {i}", key=f"v_{tk}_e_{i}", label_visibility="collapsed", placeholder="0.00")
            s = rc[2].text_input(f"s {tk} {i}", key=f"v_{tk}_s_{i}", label_visibility="collapsed", placeholder="0.00")
            rc[3].markdown(_prog_html(_prog(e, s)), unsafe_allow_html=True)
            if rc[4].button("🗑", key=f"v_{tk}_del_{i}", help="Supprimer"):
                _del_row(tk, i)
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        ac = st.columns([3.5, 1.8])
        new_ind = ac[0].text_input(f"new {tk}", key=f"v_{tk}_new", label_visibility="collapsed", placeholder="Ajouter un indicateur...")
        if ac[1].button("+ Ajouter", key=f"v_{tk}_add"):
            if new_ind.strip():
                st.session_state[f"vald_{tk}_inds"].append(new_ind.strip())
                st.session_state.pop(f"v_{tk}_new", None)
                st.rerun()

    # ── Rendu LR — 4 colonnes : Ent.G / Ent.D / Sort.G / Sort.D ─────
    def _render_lr(tk):
        inds = st.session_state[f"vald_{tk}_inds"]
        hc = st.columns([2.6, 0.95, 0.95, 0.95, 0.95, 1.3, 1.3, 0.4])
        hc[0].markdown("**Indicateur**")
        hc[1].markdown("**Ent. G**"); hc[2].markdown("**Ent. D**")
        hc[3].markdown("**Sort. G**"); hc[4].markdown("**Sort. D**")
        hc[5].markdown("**Prog. G**"); hc[6].markdown("**Prog. D**")
        st.markdown('<hr style="margin:2px 0 4px 0;border-color:#d0dae8;">', unsafe_allow_html=True)
        for i, ind in enumerate(inds):
            rc = st.columns([2.6, 0.95, 0.95, 0.95, 0.95, 1.3, 1.3, 0.4])
            rc[0].write(ind)
            eg = rc[1].text_input(f"eg {tk} {i}", key=f"v_{tk}_eg_{i}", label_visibility="collapsed", placeholder="G")
            ed = rc[2].text_input(f"ed {tk} {i}", key=f"v_{tk}_ed_{i}", label_visibility="collapsed", placeholder="D")
            sg = rc[3].text_input(f"sg {tk} {i}", key=f"v_{tk}_sg_{i}", label_visibility="collapsed", placeholder="G")
            sd = rc[4].text_input(f"sd {tk} {i}", key=f"v_{tk}_sd_{i}", label_visibility="collapsed", placeholder="D")
            rc[5].markdown(_prog_html(_prog(eg, sg)), unsafe_allow_html=True)
            rc[6].markdown(_prog_html(_prog(ed, sd)), unsafe_allow_html=True)
            if rc[7].button("🗑", key=f"v_{tk}_del_{i}", help="Supprimer"):
                _del_lr_row(tk, i)

    def _del_lr_row(tk, idx):
        inds = st.session_state[f"vald_{tk}_inds"]
        n = len(inds)
        for j in range(idx, n - 1):
            for sfx in ["eg", "ed", "sg", "sd"]:
                st.session_state[f"v_{tk}_{sfx}_{j}"] = st.session_state.get(f"v_{tk}_{sfx}_{j+1}", "")
        for sfx in ["eg", "ed", "sg", "sd"]:
            st.session_state.pop(f"v_{tk}_{sfx}_{n-1}", None)
        inds.pop(idx)
        st.rerun()

    # ── Collecte pour le rapport ──────────────────────────────────────
    def _collect_simple(tk):
        rows = []
        for i, ind in enumerate(st.session_state.get(f"vald_{tk}_inds", [])):
            e = _safe_float(st.session_state.get(f"v_{tk}_e_{i}", ""))
            s = _safe_float(st.session_state.get(f"v_{tk}_s_{i}", ""))
            if e is not None or s is not None:
                rows.append({"indicateur": ind, "entree": e, "sortie": s, "progression": _prog(e, s)})
        return rows

    def _collect_lr(tk):
        rows = []
        for i, ind in enumerate(st.session_state.get(f"vald_{tk}_inds", [])):
            eg = _safe_float(st.session_state.get(f"v_{tk}_eg_{i}", ""))
            ed = _safe_float(st.session_state.get(f"v_{tk}_ed_{i}", ""))
            sg = _safe_float(st.session_state.get(f"v_{tk}_sg_{i}", ""))
            sd = _safe_float(st.session_state.get(f"v_{tk}_sd_{i}", ""))
            if any(v is not None for v in [eg, ed, sg, sd]):
                rows.append({
                    "indicateur": ind,
                    "entree_g": eg, "entree_d": ed,
                    "sortie_g": sg, "sortie_d": sd,
                    "prog_g": _prog(eg, sg), "prog_d": _prog(ed, sd),
                })
        return rows

    slj_data, cmj_data = None, None  # compatibilité ascendante

    with st.expander("VALD ForceDecks — Saisie manuelle (optionnel)", expanded=False):
        tabs = st.tabs(["CMJ", "Drop Jump", "SLJ", "Epaule", "Mollet", "Nordic", "IMTP"])
        with tabs[0]: _render_simple("cmj")
        with tabs[1]: _render_simple("dj")
        with tabs[2]: _render_lr("slj")
        with tabs[3]: _render_lr("shoulder")
        with tabs[4]:
            st.caption("Run-Specific Ankle Iso-Push")
            _render_lr("mollet_run")
            st.divider()
            st.caption("Seated Isometric Calf Raise")
            _render_lr("mollet_seated")
        with tabs[5]: _render_lr("nordic")
        with tabs[6]: _render_lr("imtp")

        st.markdown("---")
        if st.button("Reinitialiser tous les tableaux VALD", key="reset_vald"):
            for _tk, _d in [("cmj", _CMJ_IND), ("dj", _DJ_IND)]:
                st.session_state[f"vald_{_tk}_inds"] = list(_d)
                for i in range(len(_d) + 5):
                    for sfx in ["e", "s"]:
                        st.session_state.pop(f"v_{_tk}_{sfx}_{i}", None)
            for _tk, _d in _LR_INDS.items():
                st.session_state[f"vald_{_tk}_inds"] = list(_d)
                for i in range(len(_d) + 2):
                    for sfx in ["eg", "ed", "sg", "sd"]:
                        st.session_state.pop(f"v_{_tk}_{sfx}_{i}", None)
            st.rerun()

    vald_manual = {
        "cmj":          _collect_simple("cmj"),
        "dj":           _collect_simple("dj"),
        "slj":          _collect_lr("slj"),
        "shoulder":     _collect_lr("shoulder"),
        "mollet_run":   _collect_lr("mollet_run"),
        "mollet_seated":_collect_lr("mollet_seated"),
        "nordic":        _collect_lr("nordic"),
        "imtp":          _collect_lr("imtp"),
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
            # Recherche unifiée dans SQLite (clubs prédéfinis + clubs ajoutés + logos)
            resultats = rechercher_clubs(recherche_club, limite=6)
            if resultats:
                for club in resultats:
                    col_l, col_b = st.columns([1, 5])
                    with col_l:
                        if club.get("logo_b64"):
                            st.markdown(
                                f'<img src="{club["logo_b64"]}" style="height:32px;border-radius:4px;">',
                                unsafe_allow_html=True
                            )
                        else:
                            logo_svg = get_logo(club["nom"], club.get("couleur", "#1c3f6e"))
                            st.markdown(
                                f'<img src="{logo_svg}" style="height:32px;border-radius:4px;">',
                                unsafe_allow_html=True
                            )
                    with col_b:
                        label = f"{club['nom']}  ·  {club.get('sport','')} — {club.get('division','')}"
                        if st.button(label, key=f"db_{club['nom']}", use_container_width=True):
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

        # Auto-load logo from DB when club name matches an existing record
        _club_db_match = get_club(club_nouveau_nom) if club_nouveau_nom and len(club_nouveau_nom) >= 3 else None
        if _club_db_match and _club_db_match.get("logo_b64"):
            st.markdown(
                f'<img src="{_club_db_match["logo_b64"]}" style="height:40px;border-radius:4px;margin-bottom:4px;" title="Logo enregistré">',
                unsafe_allow_html=True,
            )
            st.caption("✅ Logo existant trouvé dans la base")

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
                    _logo_b64_use = None
                    if logo_club_upload:
                        import base64 as _b64
                        _ext = logo_club_upload.name.rsplit(".", 1)[-1].lower()
                        _mime = "image/png" if _ext == "png" else "image/jpeg"
                        _logo_b64_use = (f"data:{_mime};base64,"
                                         + _b64.b64encode(logo_club_upload.getvalue()).decode())
                    elif _club_db_match and _club_db_match.get("logo_b64"):
                        _logo_b64_use = _club_db_match["logo_b64"]
                    new_club = {
                        "nom": club_nouveau_nom,
                        "sport": club_nouveau_sport,
                        "division": "Autre",
                        "couleur": "#1c3f6e",
                        "logo_b64": _logo_b64_use,
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
                    elif _club_db_match and _club_db_match.get("logo_b64"):
                        logo_b64_save = _club_db_match["logo_b64"]
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

            # Récupérer uniquement les bytes HTML (PDF non utilisé)
            if isinstance(result, dict):
                html_bytes = result.get("html_bytes")
                chemin     = result.get("pdf_path", "")
            else:
                chemin = result
                html_bytes = None
                if chemin and os.path.exists(chemin) and not chemin.endswith(".pdf"):
                    with open(chemin, "rb") as f:
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

    # Téléchargement — rapport HTML interactif uniquement
    html_b = st.session_state.get("rapport_html_bytes")
    if html_b:
        st.markdown("""
<div class="success-box">
  <h3>&#10003; Rapport g&#233;n&#233;r&#233; !</h3>
  <p>T&#233;l&#233;chargez le rapport HTML interactif, puis ouvrez-le dans votre navigateur pour personnaliser et imprimer en PDF</p>
</div>""", unsafe_allow_html=True)

        nom_base = st.session_state.get("rapport_nom_base", "rapport")
        html_interactif = _injecter_panneau_personnalisation(
            html_b.decode("utf-8")
        )
        st.download_button(
            label="🎛️ Télécharger le rapport HTML interactif",
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
