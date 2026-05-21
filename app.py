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
if "rapport_bytes" not in st.session_state:
    st.session_state.rapport_bytes = None
if "rapport_nom" not in st.session_state:
    st.session_state.rapport_nom = None
if "rapport_ext" not in st.session_state:
    st.session_state.rapport_ext = "html"
if "rapport_phase" not in st.session_state:
    st.session_state.rapport_phase = "input"   # "input" | "personalize" | "done"
if "parsed_entree" not in st.session_state:
    st.session_state.parsed_entree = None
if "parsed_sortie" not in st.session_state:
    st.session_state.parsed_sortie = None
if "parsed_cr" not in st.session_state:
    st.session_state.parsed_cr = None
if "temp_paths" not in st.session_state:
    st.session_state.temp_paths = {}


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

    # ── ÉTAPE 1 : Bouton "Préparer" ─────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🚀 Générer le Rapport PDF</div>', unsafe_allow_html=True)

    erreurs = []
    if not pdf_entree: erreurs.append("PDF Entrée manquant")
    if not pdf_sortie: erreurs.append("PDF Sortie manquant")
    if not st.session_state.get("club_selectionne") and not st.session_state.get("nom_club_cache"):
        erreurs.append("Club non sélectionné")

    for e in erreurs:
        st.warning(f"⚠️ {e}")

    if st.session_state.rapport_phase == "input":
        btn_gen = st.button("📝  Préparer &amp; Personnaliser le rapport", disabled=bool(erreurs), use_container_width=True)
        if btn_gen:
            if not pdf_entree or not pdf_sortie:
                st.error("❌ Les fichiers PDF ne sont plus disponibles — veuillez les re-uploader.")
                st.stop()
            # Sauvegarder les fichiers temporaires pour la génération ultérieure
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
            path_logo_club = None
            club_selec = st.session_state.get("club_selectionne")
            if logo_club_upload:
                ext_logo = logo_club_upload.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(suffix=f".{ext_logo}", delete=False) as f:
                    f.write(logo_club_upload.getvalue()); path_logo_club = f.name
            elif club_selec and club_selec.get("logo_b64"):
                import base64 as _b64
                logo_data = club_selec["logo_b64"]
                if ";base64," in logo_data:
                    header_part, b64_str = logo_data.split(";base64,", 1)
                    ext_logo = "png" if "png" in header_part else "jpg"
                    with tempfile.NamedTemporaryFile(suffix=f".{ext_logo}", delete=False) as f:
                        f.write(_b64.b64decode(b64_str)); path_logo_club = f.name
            # Parser les PDFs pour pré-remplir le formulaire
            try:
                from biodex_parser import parse_biodex_pdf as _pbp
                _ed = _pbp(path_e)
                _sd = _pbp(path_s)
                st.session_state.parsed_entree = _ed
                st.session_state.parsed_sortie = _sd
            except Exception:
                st.session_state.parsed_entree = None
                st.session_state.parsed_sortie = None
            st.session_state.parsed_cr = cr_data
            st.session_state.temp_paths = {
                "path_e": path_e, "path_s": path_s,
                "path_comp": path_comp, "path_comp_sain": path_comp_sain,
                "path_exc": path_exc, "path_photo": path_photo,
                "path_logo_club": path_logo_club,
            }
            st.session_state.rapport_phase = "personalize"
            st.rerun()

    # ── ÉTAPE 2 : Formulaire de personnalisation ──────────────────
    if st.session_state.rapport_phase in ("personalize", "done"):
        _ed = st.session_state.parsed_entree
        _cr = st.session_state.parsed_cr or {}
        _club = st.session_state.get("club_selectionne")
        _nom_club = (_club["nom"] if _club else "") or st.session_state.get("nom_club_cache", "")

        st.markdown("""
<div style="background:linear-gradient(135deg,#1c3f6e,#2176c7);border-radius:10px;padding:14px 18px;margin:10px 0 14px 0;">
  <div style="color:white;font-size:15px;font-weight:800;">📝 Personnalisation du rapport</div>
  <div style="color:#a8c4e0;font-size:11px;margin-top:3px;">Modifiez les informations avant de générer le PDF final</div>
</div>""", unsafe_allow_html=True)

        if st.button("← Recommencer depuis le début", key="btn_reset"):
            st.session_state.rapport_phase = "input"
            st.session_state.rapport_bytes = None
            for p in st.session_state.temp_paths.values():
                if p and os.path.exists(p):
                    try: os.unlink(p)
                    except: pass
            st.session_state.temp_paths = {}
            st.rerun()

        with st.form("personalisation_rapport"):
            st.markdown("#### 🏥 Identité du rapport")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                f_titre = st.text_input("Titre du rapport", value="Bilan Complet du Patient", key="f_titre")
            with col_t2:
                f_notes = st.text_input("Notes de séance (optionnel)", value="", placeholder="Ex: Reprise post-opératoire 6 mois", key="f_notes")

            st.markdown("#### 🩺 Diagnostic & Intervention")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                f_diag = st.text_input(
                    "Diagnostic (laisser vide = depuis CR)",
                    value=_cr.get("diagnostic", "") or "",
                    placeholder="Ex: Rupture LCA Gauche",
                    key="f_diag"
                )
            with col_d2:
                f_interv = st.text_input(
                    "Intervention (laisser vide = depuis CR)",
                    value=_cr.get("intervention", "") or "",
                    placeholder="Ex: Ligamentoplastie LCA DT4",
                    key="f_interv"
                )

            st.markdown("#### 📄 Résumé du séjour")
            f_resume = st.text_area(
                "Résumé du séjour (laisser vide = depuis CR)",
                value=_cr.get("conclusion", "") or "",
                height=100,
                placeholder="Décrivez le séjour, la prise en charge, les exercices réalisés...",
                key="f_resume"
            )

            st.markdown("#### 💬 Évaluation médicale")
            col_e1, col_e2 = st.columns([3, 1])
            with col_e1:
                f_remq = st.text_area(
                    "Remarques médicales",
                    value=remarques_medecin or "",
                    height=80,
                    placeholder="Zone libre pour le médecin / kinésithérapeute...",
                    key="f_remq"
                )
            with col_e2:
                f_acl = st.number_input("Score ACL-RSI (%)", min_value=0, max_value=100,
                                         value=int(acl_rsi_score) if acl_rsi_score else 0, key="f_acl")

            st.markdown("#### ✅ Sections à inclure")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                f_inc_exc  = st.checkbox("Test Excentrique", value=bool(pdf_exc), key="f_inc_exc")
                f_inc_prog = st.checkbox("Graphiques Progression", value=True, key="f_inc_prog")
            with col_s2:
                f_inc_vald = st.checkbox("VALD ForceDecks", value=bool(vald_slj_e or vald_cmj_e), key="f_inc_vald")
            with col_s3:
                st.caption("GPS Catapult : disponible prochainement")

            st.markdown("---")
            btn_confirm = st.form_submit_button(
                "🎯  Générer le Rapport Personnalisé",
                use_container_width=True
            )

        if btn_confirm:
            paths = st.session_state.temp_paths
            progress = st.progress(0, text="Initialisation...")
            try:
                from generate_rapport import generer_rapport_biodex
                out_dir  = os.path.join(_APP_DIR, "outputs")
                os.makedirs(out_dir, exist_ok=True)
                out_html = os.path.join(out_dir, "rapport_temp.html")
                out_pdf  = os.path.join(out_dir, "rapport_temp.pdf")
                progress.progress(40, text="📊 Calcul + graphiques en cours...")
                chemin = generer_rapport_biodex(
                    pdf_entree              = paths["path_e"],
                    pdf_sortie              = paths["path_s"],
                    pdf_comparatif          = paths.get("path_comp"),
                    pdf_comparatif_sain     = paths.get("path_comp_sain"),
                    pdf_excentrique         = paths.get("path_exc"),
                    vald_slj_entree         = vald_slj_e,
                    vald_slj_sortie         = vald_slj_s,
                    vald_cmj_entree         = vald_cmj_e,
                    vald_cmj_sortie         = vald_cmj_s,
                    output_html             = out_html,
                    output_pdf              = out_pdf,
                    template_dir            = os.path.join(_APP_DIR, "templates"),
                    nom_club                = _nom_club,
                    logo_club_path          = paths.get("path_logo_club"),
                    photo_patient_path      = paths.get("path_photo"),
                    sport                   = sport if sport != "— Sélectionner —" else "",
                    date_naissance          = str(date_naissance) if date_naissance else "",
                    date_operation          = date_operation.strftime("%d/%m/%Y") if date_operation else "",
                    type_blessure           = type_blessure,
                    cote_opere              = cote_opere,
                    acl_rsi_score           = f_acl if f_acl > 0 else None,
                    remarques_medecin       = f_remq,
                    cr_data                 = _cr if _cr else None,
                    titre_rapport           = f_titre,
                    notes_seance            = f_notes,
                    diagnostic_override     = f_diag,
                    intervention_override   = f_interv,
                    resume_override         = f_resume,
                    include_excentrique     = f_inc_exc,
                    include_vald            = f_inc_vald,
                    include_progression     = f_inc_prog,
                )
                progress.progress(90, text="📄 Lecture du fichier généré...")
                ext_out = "pdf" if chemin.endswith(".pdf") else "html"
                with open(chemin, "rb") as f:
                    rapport_bytes = f.read()
                progress.progress(100, text="✅ Rapport prêt !")
                nom_patient = (_ed.nom.replace(" ", "_").replace(".", "") if _ed else "patient")
                nom_fichier = f"Rapport_Biodex_{nom_patient}_{_nom_club.replace(' ', '_')}.{ext_out}"
                st.session_state.rapport_bytes = rapport_bytes
                st.session_state.rapport_nom   = nom_fichier
                st.session_state.rapport_ext   = ext_out
                st.session_state.rapport_phase = "done"
                # Nettoyer fichiers temporaires
                for p in paths.values():
                    if p and os.path.exists(p):
                        try: os.unlink(p)
                        except: pass
                st.session_state.temp_paths = {}
                st.rerun()
            except Exception as ex:
                st.error(f"❌ Erreur : {ex}")
                import traceback
                with st.expander("Détails de l'erreur"):
                    st.code(traceback.format_exc())

    # ── ÉTAPE 3 : Téléchargement ──────────────────────────────────
    if st.session_state.rapport_bytes:
        ext  = st.session_state.rapport_ext
        mime = "application/pdf" if ext == "pdf" else "text/html"
        st.markdown("""
<div class="success-box">
  <h3>✅ Rapport généré avec succès !</h3>
  <p>Rapport personnalisé prêt au téléchargement</p>
</div>""", unsafe_allow_html=True)
        st.download_button(
            label    = f"⬇️  Télécharger le Rapport ({ext.upper()})",
            data     = st.session_state.rapport_bytes,
            file_name= st.session_state.rapport_nom,
            mime     = mime,
            use_container_width=True,
        )
        if ext == "html":
            st.markdown("""
<div class="info-box">
💡 <b>PDF avec couleurs :</b> Ouvre le fichier HTML dans Chrome
→ <code>Ctrl+P</code> → <em>Enregistrer en PDF</em>.<br>
Ou installe <b>wkhtmltopdf</b> depuis wkhtmltopdf.org pour avoir le PDF directement.
</div>""", unsafe_allow_html=True)
        if st.button("🔄 Générer un nouveau rapport", key="btn_new"):
            st.session_state.rapport_phase = "input"
            st.session_state.rapport_bytes = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# Footer
st.markdown("---")
st.markdown('<div style="text-align:center;color:#888;font-size:11px;">CERS Capbreton • Groupe Ramsay Santé • Bilan Isocinétique Biodex v6 • 4 sports • 112 clubs</div>', unsafe_allow_html=True)
