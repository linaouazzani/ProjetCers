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
    Permet de cocher/décocher des sections et d'imprimer via Chrome.
    Disparaît à l'impression (@media print).
    """
    import re as _re

    def assigner_sections(html_text):
        # Assigner data-section aux div.page en ordre séquentiel
        sequential = ["bilan-60", "bilan-240", "remarques", "bilan-vald",
                      "section-4", "section-5"]
        pattern = r'(<div[^>]*class=["\'][^"\']*\bpage\b[^"\']*["\'][^>]*>)'
        parts = _re.split(pattern, html_text)
        result = []
        page_count = 0
        for part in parts:
            if _re.match(r'<div[^>]*class=["\'][^"\']*\bpage\b', part):
                sid = sequential[page_count] if page_count < len(sequential) else f"section-{page_count}"
                page_count += 1
                # Insérer data-section avant le > de fermeture
                part = part.rstrip('>')
                part = part + f' data-section="{sid}" data-printable="true">'
            result.append(part)
        return ''.join(result)

    html = assigner_sections(html)

    panneau = """
<style>
@media print {
    #ctrl-panel { display: none !important; }
    body { padding-top: 0 !important; margin-top: 0 !important; }
    [data-section].hidden { display: none !important; }
}
#ctrl-panel {
    position: fixed;
    top: 0; left: 0; right: 0;
    background: #1c3f6e;
    color: #fff;
    padding: 8px 16px;
    font-family: Arial, sans-serif;
    font-size: 12px;
    z-index: 99999;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    box-shadow: 0 3px 10px rgba(0,0,0,0.4);
    min-height: 48px;
}
.ctrl-title {
    font-size: 13px;
    font-weight: bold;
    margin-right: 4px;
    white-space: nowrap;
}
.ctrl-label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.2);
    padding: 3px 9px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11.5px;
    user-select: none;
    transition: background 0.15s;
}
.ctrl-label:hover { background: rgba(255,255,255,0.22); }
.ctrl-label input { cursor: pointer; width:13px; height:13px; }
.ctrl-label.unchecked {
    background: rgba(255,255,255,0.05);
    opacity: 0.6;
    text-decoration: line-through;
}
#edit-toggle {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.25);
    color: #fff;
    padding: 3px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11.5px;
}
#edit-toggle:hover { background: rgba(255,255,255,0.22); }
#print-btn {
    background: #2a8a36;
    color: #fff;
    border: none;
    padding: 6px 16px;
    border-radius: 5px;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
    margin-left: auto;
    white-space: nowrap;
}
#print-btn:hover { background: #237030; }
#edit-zone {
    width: 100%;
    display: none;
    padding: 6px 0 2px;
}
#remarques-textarea {
    width: 100%;
    min-height: 50px;
    padding: 5px 8px;
    font-size: 12px;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.3);
    background: rgba(255,255,255,0.1);
    color: #fff;
    resize: vertical;
    box-sizing: border-box;
}
#remarques-textarea::placeholder { color: rgba(255,255,255,0.5); }
body { padding-top: 58px; box-sizing: border-box; }
</style>

<div id="ctrl-panel">
  <span class="ctrl-title">Personnaliser :</span>

  <label class="ctrl-label" id="lbl-page-garde">
    <input type="checkbox" checked
           onchange="toggleSection('page-garde', this)">
    Page de garde
  </label>
  <label class="ctrl-label" id="lbl-bilan-60">
    <input type="checkbox" checked
           onchange="toggleSection('bilan-60', this)">
    Bilan 60°/s
  </label>
  <label class="ctrl-label" id="lbl-bilan-240">
    <input type="checkbox" checked
           onchange="toggleSection('bilan-240', this)">
    Bilan 240°/s
  </label>
  <label class="ctrl-label" id="lbl-remarques">
    <input type="checkbox" checked
           onchange="toggleSection('remarques', this)">
    Analyse clinique
  </label>
  <label class="ctrl-label" id="lbl-bilan-vald">
    <input type="checkbox" checked
           onchange="toggleSection('bilan-vald', this)">
    VALD
  </label>
  <label class="ctrl-label" id="lbl-conclusion-programme">
    <input type="checkbox" checked
           onchange="toggleSection('conclusion-programme', this)">
    Conclusion
  </label>

  <button id="edit-toggle" onclick="toggleEdit()">
    ✏️ Remarques
  </button>

  <button id="print-btn" onclick="imprimerRapport()">
    Imprimer / PDF
  </button>

  <div id="edit-zone">
    <textarea id="remarques-textarea"
              placeholder="Saisir les remarques médicales ici..."
              oninput="syncRemarques(this.value)"></textarea>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    var rem = document.querySelector('[data-remarques-content]');
    var ta  = document.getElementById('remarques-textarea');
    if (rem && ta) ta.value = rem.innerText.trim();

    var sections = ['page-garde','bilan-60','bilan-240','remarques','bilan-vald','conclusion-programme'];
    sections.forEach(function(sid) {
        var el  = document.querySelector('[data-section="'+sid+'"]');
        var lbl = document.getElementById('lbl-'+sid);
        if (!el && lbl) lbl.style.display = 'none';
    });
});

function toggleSection(sid, checkbox) {
    var els = document.querySelectorAll('[data-section="'+sid+'"]');
    var lbl = document.getElementById('lbl-'+sid);
    els.forEach(function(el) {
        el.style.display = checkbox.checked ? '' : 'none';
    });
    if (lbl) lbl.classList.toggle('unchecked', !checkbox.checked);
}

function toggleEdit() {
    var zone = document.getElementById('edit-zone');
    zone.style.display = (zone.style.display === 'none' || zone.style.display === '')
                         ? 'block' : 'none';
}

function syncRemarques(val) {
    var rems = document.querySelectorAll('[data-remarques-content]');
    rems.forEach(function(el) {
        el.innerText = val;
        el.style.display = val.trim() ? '' : 'none';
    });
    var bloc = document.querySelector('[data-section="remarques-medicales"]');
    if (bloc) bloc.style.display = val.trim() ? '' : 'none';
}

function imprimerRapport() {
    window.print();
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
            "📥 Test d'ENTRÉE (obligatoire)", type=["pdf"], key="up_entree"
        )
    with col_s:
        pdf_sortie = st.file_uploader(
            "📤 Test de SORTIE (obligatoire)", type=["pdf"], key="up_sortie"
        )

    with st.expander("📎 PDFs optionnels"):
        co1, co2, co3, co4 = st.columns(4)
        with co1:
            pdf_comp = st.file_uploader(
                "Comparatif Lésé", type=["pdf"], key="up_comp"
            )
        with co2:
            pdf_comp_sain = st.file_uploader(
                "Comparatif Sain", type=["pdf"], key="up_comp_sain"
            )
        with co3:
            pdf_exc = st.file_uploader(
                "Excentrique 30°/s", type=["pdf"], key="up_exc"
            )
        with co4:
            pdf_cr = st.file_uploader(
                "Compte-rendu médical",
                type=["pdf"], key="up_cr",
                help="PDF compte-rendu CERS — extrait diagnostic, intervention, bilan clinique"
            )

    cols_b = st.columns(6)
    statuts = [
        (pdf_entree,    "Entrée",      True),
        (pdf_sortie,    "Sortie",      True),
        (pdf_comp,      "Comp.Lésé",   False),
        (pdf_comp_sain, "Comp.Sain",   False),
        (pdf_exc,       "Excentrique", False),
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

    # 1b. VALD ForceDecks
    import io
    from vald_parser import parse_vald_slj, parse_vald_cmj

    vald_slj_e, vald_slj_s, vald_cmj_e, vald_cmj_s = None, None, None, None

    with st.expander("📊 VALD ForceDecks — Sauts (optionnel)"):
        st.caption("PDFs exportés depuis VALD Hub · Firefox → Imprimer → Enregistrer en PDF")

        col_v1, col_v2, col_v3, col_v4 = st.columns(4)
        with col_v1:
            pdf_slj_e_up = st.file_uploader("SLJ Entrée", type="pdf", key="vald_slj_e",
                                             help="PDF Single Leg Jump séance d'entrée")
        with col_v2:
            pdf_slj_s_up = st.file_uploader("SLJ Sortie", type="pdf", key="vald_slj_s",
                                             help="PDF Single Leg Jump séance de sortie")
        with col_v3:
            pdf_cmj_e_up = st.file_uploader("CMJ Entrée", type="pdf", key="vald_cmj_e",
                                             help="PDF CMJ entrée (avec RSI-modified visible)")
        with col_v4:
            pdf_cmj_s_up = st.file_uploader("CMJ Sortie", type="pdf", key="vald_cmj_s",
                                             help="PDF CMJ sortie (avec RSI-modified visible)")

        if pdf_slj_e_up:
            try:
                vald_slj_e = parse_vald_slj(io.BytesIO(pdf_slj_e_up.getvalue()))
                st.success(f"SLJ Entrée : G={vald_slj_e['slj_hauteur_g']} cm / D={vald_slj_e['slj_hauteur_d']} cm")
            except Exception as _e:
                st.error(f"Erreur SLJ Entrée : {_e}")

        if pdf_slj_s_up:
            try:
                vald_slj_s = parse_vald_slj(io.BytesIO(pdf_slj_s_up.getvalue()))
                st.success(f"SLJ Sortie : G={vald_slj_s['slj_hauteur_g']} cm / D={vald_slj_s['slj_hauteur_d']} cm")
            except Exception as _e:
                st.error(f"Erreur SLJ Sortie : {_e}")

        if pdf_cmj_e_up:
            try:
                vald_cmj_e = parse_vald_cmj(io.BytesIO(pdf_cmj_e_up.getvalue()))
                rsi_txt = f"RSI={vald_cmj_e['cmj_rsi']} m/s" if vald_cmj_e['cmj_rsi'] else "RSI absent du PDF"
                st.success(f"CMJ Entrée : H={vald_cmj_e['cmj_hauteur']} cm · {rsi_txt}")
            except Exception as _e:
                st.error(f"Erreur CMJ Entrée : {_e}")

        if pdf_cmj_s_up:
            try:
                vald_cmj_s = parse_vald_cmj(io.BytesIO(pdf_cmj_s_up.getvalue()))
                rsi_txt = f"RSI={vald_cmj_s['cmj_rsi']} m/s" if vald_cmj_s['cmj_rsi'] else "RSI absent du PDF"
                st.success(f"CMJ Sortie : H={vald_cmj_s['cmj_hauteur']} cm · {rsi_txt}")
            except Exception as _e:
                st.error(f"Erreur CMJ Sortie : {_e}")

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

    # 1c. GPS Catapult — A3
    with st.expander("📡 GPS Catapult (optionnel — à venir)"):
        st.info("Section en cours de développement. "
                "Uploader ici les exports Catapult CSV/XLSX du patient.")
        pdf_gps = st.file_uploader(
            "Fichier GPS Catapult (CSV ou XLSX)",
            type=["csv", "xlsx"], key="up_gps"
        )

    # Valeurs par défaut (accessibles même si l'expander n'est pas ouvert)
    remarques_medecin = ""
    programme_kine    = ""
    programme_prepa   = ""
    conclusion_sortie = ""
    ressenti          = ""

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

        st.markdown("---")
        st.caption("🩺 Ressenti du joueur & avis clinique — retour au sport (apparaît en page de garde)")
        ressenti = st.text_area(
            "Ressenti du joueur / Avis clinique (optionnel)",
            placeholder="Ex : Le joueur se sent prêt à reprendre l'entraînement collectif. Bonne confiance dans le genou. Appréhension légère sur les changements de direction...\nOu : Nécessite encore 3 semaines de rééducation avant retour au club.",
            height=80, key="ressenti_joueur"
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

    if pdf_entree and pdf_sortie:
        with st.spinner("Lecture des PDFs..."):
            try:
                from biodex_parser import parse_biodex_pdf

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_entree.getvalue()); path_e_prev = f.name
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_sortie.getvalue()); path_s_prev = f.name

                entree_data = parse_biodex_pdf(path_e_prev)
                sortie_data = parse_biodex_pdf(path_s_prev)
                os.unlink(path_e_prev); os.unlink(path_s_prev)

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

    erreurs = []
    if not pdf_entree: erreurs.append("PDF Entrée manquant")
    if not pdf_sortie: erreurs.append("PDF Sortie manquant")
    if not st.session_state.get("club_selectionne") and not st.session_state.get("nom_club_cache"):
        erreurs.append("Club non sélectionné")

    for e in erreurs:
        st.warning(f"⚠️ {e}")

    btn_gen = st.button("🔄  Générer le Rapport PDF Complet", disabled=bool(erreurs), use_container_width=True)

    if btn_gen:
        if not pdf_entree or not pdf_sortie:
            st.error("❌ Les fichiers PDF ne sont plus disponibles — veuillez les re-uploader.")
            st.stop()

        club = st.session_state.get("club_selectionne")
        nom_club = (club["nom"] if club else "") or st.session_state.get("nom_club_cache", "")
        progress = st.progress(0, text="Initialisation...")

        try:
            from generate_rapport import generer_rapport_biodex

            progress.progress(10, text="📄 Sauvegarde des fichiers...")

            # Sauvegarder PDFs Biodex
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_entree.getvalue()); path_e = f.name
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
                vald_slj_entree         = vald_slj_e,
                vald_slj_sortie         = vald_slj_s,
                vald_cmj_entree         = vald_cmj_e,
                vald_cmj_sortie         = vald_cmj_s,
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
                ressenti                = ressenti,
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

            nom_patient  = (entree_data.nom.replace(" ", "_").replace(".", "") if entree_data else "patient")
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
