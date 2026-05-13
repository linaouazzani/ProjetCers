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
from clubs_database import CLUBS_DATABASE, search_clubs

_APP_DIR = os.path.dirname(os.path.abspath(__file__))

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


# ── En-tête ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div>
    <h1>🏥 CERS Capbreton — Bilan Isocinétique</h1>
    <p>Génération automatique du rapport Biodex • Groupe Ramsay Santé • 4 sports • 112 clubs</p>
  </div>
  <div class="hero-badge">Biodex v6 • PDF direct</div>
</div>
""", unsafe_allow_html=True)


# ── Layout ────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 1.1], gap="large")


# ╔══════════════════════════════════════╗
# ║       COLONNE GAUCHE — INPUTS       ║
# ╚══════════════════════════════════════╝
with col_left:

    # 1. PDFs Biodex
    st.markdown('<div class="card"><div class="card-title">📄 Fichiers Biodex</div>', unsafe_allow_html=True)
    pdf_entree    = st.file_uploader("Test d'ENTRÉE (début de séjour)",      type=["pdf"], key="up_entree")
    pdf_sortie    = st.file_uploader("Test de SORTIE (fin de séjour)",       type=["pdf"], key="up_sortie")
    pdf_comp      = st.file_uploader("Comparatif Lésé (optionnel)",          type=["pdf"], key="up_comp")
    pdf_comp_sain = st.file_uploader("Comparatif Sain (optionnel)",          type=["pdf"], key="up_comp_sain")
    pdf_exc       = st.file_uploader("Test Excentrique 30°/s (optionnel)",   type=["pdf"], key="up_exc")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f'<span class="badge {"badge-ok" if pdf_entree else "badge-wait"}">{"✅ Entrée" if pdf_entree else "⏳ Entrée"}</span>', unsafe_allow_html=True)
    with c2: st.markdown(f'<span class="badge {"badge-ok" if pdf_sortie else "badge-wait"}">{"✅ Sortie" if pdf_sortie else "⏳ Sortie"}</span>', unsafe_allow_html=True)
    with c3: st.markdown(f'<span class="badge {"badge-ok" if pdf_comp else "badge-opt"}">{"✅ Comp. Lésé" if pdf_comp else "Comp. Lésé"}</span>', unsafe_allow_html=True)
    with c4: st.markdown(f'<span class="badge {"badge-ok" if pdf_comp_sain else "badge-opt"}">{"✅ Comp. Sain" if pdf_comp_sain else "Comp. Sain"}</span>', unsafe_allow_html=True)
    with c5: st.markdown(f'<span class="badge {"badge-ok" if pdf_exc else "badge-opt"}">{"✅ Excentrique" if pdf_exc else "Excentrique"}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Informations patient
    st.markdown('<div class="card"><div class="card-title">👤 Informations Patient</div>', unsafe_allow_html=True)

    date_naissance = st.date_input(
        "Date de naissance (optionnel)",
        value=None,
        min_value=datetime.date(1950, 1, 1),
        max_value=datetime.date.today(),
        key="date_naissance"
    )

    sport = st.selectbox("Sport", [
        "— Sélectionner —", "Rugby", "Football", "Basketball",
        "Handball", "Tennis", "Natation", "Athlétisme", "Autre"
    ])

    date_operation = st.date_input(
        "Date d'opération (optionnel)", value=None
    )

    type_blessure = st.text_input(
        "Type de blessure (optionnel)",
        placeholder="Ex: Rupture LCA, Ménisque..."
    )

    cote_opere = st.selectbox(
        "Côté opéré (optionnel)",
        ["— Sélectionner —", "Gauche", "Droit", "Bilatéral"]
    )

    acl_rsi_score = st.number_input(
        "Score ACL-RSI % (optionnel)",
        min_value=0, max_value=100, value=0, step=1
    )

    remarques_medecin = st.text_area(
        "Remarques médicales finales (optionnel)",
        placeholder="Zone libre pour le médecin ou kinésithérapeute...",
        height=100
    )

    photo = st.file_uploader("📸 Photo du joueur (optionnel)", type=["png","jpg","jpeg"], key="up_photo")
    if photo:
        st.image(photo, width=70, caption="Aperçu photo")
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. Logo club (upload direct)
    st.markdown('<div class="card"><div class="card-title">🖼️ Logo du Club (optionnel)</div>', unsafe_allow_html=True)
    logo_club_upload = st.file_uploader(
        "Logo du club (PNG recommandé, fond transparent idéal)",
        type=["png","jpg","jpeg"],
        key="up_logo_club",
        help="Upload le logo directement — il apparaîtra dans le PDF",
    )
    if logo_club_upload:
        st.image(logo_club_upload, width=100, caption="Logo club")
        st.success("✅ Logo chargé")
    else:
        st.info("Sans logo : le nom du club s'affichera à la place.")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. Club
    st.markdown('<div class="card"><div class="card-title">🏆 Club du joueur</div>', unsafe_allow_html=True)

    recherche = st.text_input("🔍 Rechercher un club", placeholder="Ex: Clermont, PSG, Monaco...", key="search_club")

    if recherche and len(recherche) >= 2:
        resultats = search_clubs(recherche)
        if resultats:
            st.markdown(f"**{len(resultats)} club(s) trouvé(s) :**")
            for club in resultats[:8]:
                logo_b64 = get_logo(club["nom"], club["couleur"])
                col_logo, col_info = st.columns([1, 4])
                with col_logo:
                    st.markdown(f'<img src="{logo_b64}" style="height:35px;border-radius:4px;">', unsafe_allow_html=True)
                with col_info:
                    if st.button(f"{club['nom']}  ·  {club['sport']} — {club['division']}", key=f"btn_{club['nom']}", use_container_width=True):
                        st.session_state.club_selectionne = club
                        st.session_state.nom_club_cache = club["nom"]
                        st.rerun()
        else:
            st.info("Aucun club trouvé. Essaie un autre terme.")
    else:
        st.markdown('<div class="info-box">Tape le nom d\'un club ci-dessus, ou sélectionne par sport :</div>', unsafe_allow_html=True)
        sport_choix = st.selectbox("Sport", ["— Choisir un sport —"] + [d["label"] for d in CLUBS_DATABASE.values()], key="sport_select")

        if sport_choix and sport_choix != "— Choisir un sport —":
            sport_key = next((k for k, v in CLUBS_DATABASE.items() if v["label"] == sport_choix), None)
            if sport_key:
                sport_data = CLUBS_DATABASE[sport_key]
                division_choix = st.selectbox("Division", list(sport_data["divisions"].keys()), key="div_select")
                if division_choix:
                    clubs_div = sport_data["divisions"][division_choix]
                    club_noms = [c["nom"] for c in clubs_div]
                    club_nom_choix = st.selectbox("Club", ["— Choisir —"] + club_noms, key="club_select")
                    if club_nom_choix and club_nom_choix != "— Choisir —":
                        club_data = next((c for c in clubs_div if c["nom"] == club_nom_choix), None)
                        if club_data and st.button("✅ Sélectionner ce club", use_container_width=True):
                            st.session_state.club_selectionne = {
                                "nom": club_data["nom"],
                                "sport": sport_data["label"],
                                "sport_key": sport_key,
                                "division": division_choix,
                                "couleur": club_data.get("couleur", "#1c3f6e"),
                            }
                            st.session_state.nom_club_cache = club_data["nom"]
                            st.rerun()

    if not st.session_state.club_selectionne:
        st.markdown("---")
        st.markdown("**Club non trouvé dans la liste ?**")
        col_nom, col_sport = st.columns(2)
        with col_nom:
            club_manuel_nom = st.text_input(
                "Nom du club",
                placeholder="Ex: FC Bayeux, AS Villemur...",
                key="club_manuel_nom"
            )
        with col_sport:
            club_manuel_sport = st.selectbox(
                "Sport",
                ["Rugby", "Football", "Basketball",
                 "Handball", "Volleyball", "Autre"],
                key="club_manuel_sport"
            )
        if club_manuel_nom and st.button("✅ Utiliser ce club", key="btn_club_manuel"):
            st.session_state.club_selectionne = {
                "nom": club_manuel_nom,
                "sport": club_manuel_sport,
                "division": "Autre",
                "couleur": "#1c3f6e",
            }
            st.session_state.nom_club_cache = club_manuel_nom
            st.rerun()

    if st.session_state.club_selectionne:
        club = st.session_state.club_selectionne
        logo_b64 = get_logo(club["nom"], club["couleur"])
        st.markdown(f"""
<div class="club-selected">
  <img src="{logo_b64}" style="height:40px;border-radius:6px;">
  <div>
    <div style="font-size:15px;">{club['nom']}</div>
    <div style="font-size:11px;color:#555;font-weight:400;">{club['sport']} — {club['division']}</div>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button("✏️ Changer de club", use_container_width=False):
            st.session_state.club_selectionne = None
            st.rerun()
    else:
        st.markdown('<span class="badge badge-wait">⏳ Aucun club sélectionné</span>', unsafe_allow_html=True)

    nom_club_manuel = ""
    if st.session_state.club_selectionne and st.session_state.club_selectionne.get("nom") == "Autre club":
        nom_club_manuel = st.text_input("Nom du club (saisie libre)", placeholder="Ex: FC Bordeaux")

    st.markdown('</div>', unsafe_allow_html=True)


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
                    f.write(pdf_entree.read()); path_e_prev = f.name
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_sortie.read()); path_s_prev = f.name
                pdf_entree.seek(0); pdf_sortie.seek(0)

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
        nom_club = (nom_club_manuel
                    or (club["nom"] if club else "")
                    or st.session_state.get("nom_club_cache", ""))
        progress = st.progress(0, text="Initialisation...")

        try:
            from generate_rapport import generer_rapport_biodex

            progress.progress(10, text="📄 Sauvegarde des fichiers...")

            # Sauvegarder PDFs
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_entree.getvalue()); path_e = f.name
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_sortie.getvalue()); path_s = f.name

            path_comp = None
            if pdf_comp:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_comp.getvalue()); path_comp = f.name

            path_photo = None
            if photo:
                ext_ph = photo.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(suffix=f".{ext_ph}", delete=False) as f:
                    f.write(photo.getvalue()); path_photo = f.name

            # Logo club : priorité à l'upload manuel
            path_logo_club = None
            if logo_club_upload:
                ext_logo = logo_club_upload.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(suffix=f".{ext_logo}", delete=False) as f:
                    f.write(logo_club_upload.getvalue()); path_logo_club = f.name

            path_comp_sain = None
            if pdf_comp_sain:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_comp_sain.getvalue()); path_comp_sain = f.name

            path_exc = None
            if pdf_exc:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_exc.getvalue()); path_exc = f.name

            progress.progress(30, text="🔍 Parsing des PDFs Biodex...")

            # Dossier de sortie FIXE (obligatoire pour pdfkit sur Windows)
            out_dir  = os.path.join(_APP_DIR, "outputs")
            os.makedirs(out_dir, exist_ok=True)
            out_html = os.path.join(out_dir, "rapport_temp.html")
            out_pdf  = os.path.join(out_dir, "rapport_temp.pdf")

            progress.progress(60, text="📊 Calcul + graphiques en cours...")

            chemin = generer_rapport_biodex(
                pdf_entree           = path_e,
                pdf_sortie           = path_s,
                pdf_comparatif       = path_comp,
                pdf_comparatif_sain  = path_comp_sain,
                pdf_excentrique      = path_exc,
                output_html          = out_html,
                output_pdf           = out_pdf,
                template_dir         = os.path.join(_APP_DIR, "templates"),
                nom_club             = nom_club,
                logo_club_path       = path_logo_club,
                photo_patient_path   = path_photo,
                sport                = sport if sport != "— Sélectionner —" else "",
                date_naissance       = str(date_naissance) if date_naissance else "",
                date_operation       = str(date_operation) if date_operation else "",
                type_blessure        = type_blessure,
                cote_opere           = cote_opere if cote_opere != "— Sélectionner —" else "",
                acl_rsi_score        = acl_rsi_score if acl_rsi_score > 0 else None,
                remarques_medecin    = remarques_medecin,
            )

            progress.progress(90, text="📄 Lecture du fichier généré...")

            ext_out  = "pdf"  if chemin.endswith(".pdf")  else "html"
            mime_out = "application/pdf" if ext_out == "pdf" else "text/html"

            with open(chemin, "rb") as f:
                rapport_bytes = f.read()

            progress.progress(100, text="✅ Rapport prêt !")

            # Nom fichier téléchargement
            nom_patient = (entree_data.nom.replace(" ","_").replace(".","") if entree_data else "patient")
            nom_fichier = f"Rapport_Biodex_{nom_patient}_{nom_club.replace(' ','_')}.{ext_out}"

            st.session_state.rapport_bytes = rapport_bytes
            st.session_state.rapport_nom   = nom_fichier
            st.session_state.rapport_ext   = ext_out

            # Nettoyer fichiers temporaires
            for p in [path_e, path_s, path_comp, path_comp_sain, path_exc, path_photo, path_logo_club]:
                if p and os.path.exists(p):
                    try: os.unlink(p)
                    except: pass

        except Exception as ex:
            st.error(f"❌ Erreur : {ex}")
            import traceback
            with st.expander("Détails de l'erreur"):
                st.code(traceback.format_exc())

    # Téléchargement
    if st.session_state.rapport_bytes:
        ext  = st.session_state.rapport_ext
        mime = "application/pdf" if ext == "pdf" else "text/html"

        st.markdown("""
<div class="success-box">
  <h3>✅ Rapport généré avec succès !</h3>
  <p>Page 1 : Données numériques • Page 2 : Graphiques</p>
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

    st.markdown('</div>', unsafe_allow_html=True)


# Footer
st.markdown("---")
st.markdown('<div style="text-align:center;color:#888;font-size:11px;">CERS Capbreton • Groupe Ramsay Santé • Bilan Isocinétique Biodex v6 • 4 sports • 112 clubs</div>', unsafe_allow_html=True)
