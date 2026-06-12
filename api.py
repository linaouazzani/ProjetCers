"""
api.py — CERS Capbreton API Flask
===================================
Pont entre le front PHP et les parsers Python.
Port : 5000

Lancement :
    python api.py

Routes :
    GET  /ping
    GET  /clubs/search?q=xxx
    POST /clubs/save
    GET  /blessures
    POST /blessures/add
    POST /generate
"""

import os
import sys
import json
import base64
import tempfile
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS

# Dossier racine du projet
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _APP_DIR)

app = Flask(__name__)
CORS(app)  # Autorise toutes les origines (CORS *)

# Dossier pour les uploads temporaires
UPLOAD_DIR = os.path.join(_APP_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Dossier de sortie pour les rapports
OUTPUT_DIR = os.path.join(_APP_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Blessures ─────────────────────────────────────────────────────────────────

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

BLESSURES_DB_PATH = os.path.join(_APP_DIR, "blessures_db.json")


def _charger_blessures():
    if os.path.exists(BLESSURES_DB_PATH):
        try:
            with open(BLESSURES_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return list(dict.fromkeys(BLESSURES_DEFAULT + data.get("custom", [])))
        except Exception:
            pass
    return list(BLESSURES_DEFAULT)


def _sauvegarder_blessure(blessure: str):
    custom = []
    if os.path.exists(BLESSURES_DB_PATH):
        try:
            with open(BLESSURES_DB_PATH, "r", encoding="utf-8") as f:
                custom = json.load(f).get("custom", [])
        except Exception:
            pass
    if blessure not in custom:
        custom.append(blessure)
    with open(BLESSURES_DB_PATH, "w", encoding="utf-8") as f:
        json.dump({"custom": custom}, f, ensure_ascii=False, indent=2)


# ── Utilitaire upload ─────────────────────────────────────────────────────────

def _save_upload(file_obj, suffix=".pdf") -> str:
    """Sauvegarde un fichier uploadé et retourne son chemin absolu."""
    uid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{uid}{suffix}")
    file_obj.save(path)
    return path


# ════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "CERS API opérationnelle"})


# ── Clubs ─────────────────────────────────────────────────────────────────────

@app.route("/clubs/search", methods=["GET"])
def clubs_search():
    from database import rechercher_clubs
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    clubs = rechercher_clubs(q, limite=8)
    return jsonify(clubs)


@app.route("/clubs/save", methods=["POST"])
def clubs_save():
    from database import enregistrer_club

    # Supporte JSON et multipart/form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    nom = data.get("nom", "").strip()
    if not nom:
        return jsonify({"error": "Nom du club requis"}), 400

    logo_b64 = data.get("logo_b64") or None

    # Logo uploadé en multipart
    if "logo" in request.files and request.files["logo"].filename:
        lf = request.files["logo"]
        raw = lf.read()
        ext = (lf.filename.rsplit(".", 1)[-1].lower() if lf.filename else "png")
        mime = "image/png" if ext == "png" else "image/jpeg"
        logo_b64 = f"data:{mime};base64," + base64.b64encode(raw).decode()

    club = enregistrer_club(
        nom=nom,
        sport=data.get("sport", "Autre"),
        division=data.get("division", "Autre"),
        couleur=data.get("couleur", "#1c3f6e"),
        logo_b64=logo_b64,
        sport_key=data.get("sport_key", "autre"),
    )
    return jsonify(club)


# ── Blessures ─────────────────────────────────────────────────────────────────

@app.route("/blessures", methods=["GET"])
def blessures_list():
    return jsonify(_charger_blessures())


@app.route("/blessures/add", methods=["POST"])
def blessures_add():
    data = request.get_json(silent=True) or {}
    blessure = data.get("blessure", "").strip()
    if not blessure:
        return jsonify({"error": "Blessure requise"}), 400
    _sauvegarder_blessure(blessure)
    return jsonify({"success": True, "blessures": _charger_blessures()})


# ── Génération rapport ────────────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
def generate():
    from generate_rapport import generer_rapport_biodex

    tmp_files = []

    try:
        # ── PDFs uploadés ──────────────────────────────────────────────
        def get_pdf(key):
            if key in request.files and request.files[key].filename:
                f = request.files[key]
                ext = (f.filename.rsplit(".", 1)[-1].lower() if f.filename else "pdf")
                path = _save_upload(f, f".{ext}")
                tmp_files.append(path)
                return path
            return None

        path_e          = get_pdf("pdf_entree")
        path_s          = get_pdf("pdf_sortie")
        path_comp       = get_pdf("pdf_comparatif")
        path_comp_sain  = get_pdf("pdf_comparatif_sain")
        path_exc        = get_pdf("pdf_excentrique")
        path_cr         = get_pdf("pdf_cr")
        path_gps        = get_pdf("pdf_gps")
        path_photo      = get_pdf("photo")
        path_logo       = get_pdf("logo_club")

        # ── Paramètres texte ───────────────────────────────────────────
        form = request.form

        def fstr(key, default=""):
            return (form.get(key) or default).strip()

        def fint(key):
            v = form.get(key, "").strip()
            try:
                i = int(v)
                return i if i > 0 else None
            except (ValueError, TypeError):
                return None

        sport           = fstr("sport")
        date_operation  = fstr("date_operation")
        type_blessure   = fstr("type_blessure")
        cote_opere      = fstr("cote_opere")
        nom_club        = fstr("nom_club", "—")
        remarques       = fstr("remarques_medecin")
        programme_kine  = fstr("programme_kine")
        programme_prepa = fstr("programme_prepa")
        conclusion      = fstr("conclusion_sortie")
        titre_rapport   = fstr("titre_rapport")
        acl_rsi         = fint("acl_rsi_score")

        # ── Parsers optionnels ─────────────────────────────────────────
        cr_data = None
        if path_cr:
            try:
                from cr_parser import parse_compte_rendu
                cr_data = parse_compte_rendu(path_cr)
            except Exception as e:
                print(f"[API] Erreur CR : {e}")

        gps_data = None
        if path_gps:
            try:
                from gps_parser import parse_gps_pdf
                gps_data = parse_gps_pdf(path_gps)
            except Exception as e:
                print(f"[API] Erreur GPS : {e}")

        # ── VALD manuel ────────────────────────────────────────────────
        vald_manual = None
        vald_json = form.get("vald_manual", "")
        if vald_json:
            try:
                vm = json.loads(vald_json)
                if any(vm.get(k) for k in vm):
                    vald_manual = vm
            except Exception:
                pass

        # ── Sorties ────────────────────────────────────────────────────
        uid      = str(uuid.uuid4())[:8]
        out_html = os.path.join(OUTPUT_DIR, f"rapport_{uid}.html")
        out_pdf  = os.path.join(OUTPUT_DIR, f"rapport_{uid}.pdf")

        # ── Appel pipeline ─────────────────────────────────────────────
        result = generer_rapport_biodex(
            pdf_entree          = path_e,
            pdf_sortie          = path_s,
            pdf_comparatif      = path_comp,
            pdf_comparatif_sain = path_comp_sain,
            pdf_excentrique     = path_exc,
            cr_data             = cr_data,
            output_html         = out_html,
            output_pdf          = out_pdf,
            template_dir        = os.path.join(_APP_DIR, "templates"),
            nom_club            = nom_club,
            logo_club_path      = path_logo,
            photo_patient_path  = path_photo,
            sport               = sport,
            date_operation      = date_operation,
            type_blessure       = type_blessure,
            cote_opere          = cote_opere,
            acl_rsi_score       = acl_rsi,
            remarques_medecin   = remarques,
            programme_kine      = programme_kine,
            programme_prepa     = programme_prepa,
            conclusion_sortie   = conclusion,
            titre_rapport       = titre_rapport,
            gps_data            = gps_data,
            vald_manual         = vald_manual,
        )

        # ── Encodage base64 ────────────────────────────────────────────
        pdf_b64 = html_b64 = ""
        if isinstance(result, dict):
            pb = result.get("pdf_bytes")
            hb = result.get("html_bytes")
            if pb:
                pdf_b64 = base64.b64encode(pb).decode()
            if hb:
                html_b64 = base64.b64encode(hb).decode()

        # Nettoyer les sorties temporaires
        for f in [out_html, out_pdf]:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except Exception:
                pass

        return jsonify({"success": True, "pdf_b64": pdf_b64, "html_b64": html_b64})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        for p in tmp_files:
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from database import init_db
    init_db()
    print("=" * 60)
    print("  CERS API Flask — http://localhost:5000")
    print("  Front PHP  : cd php && php -S localhost:8080")
    print("  Test API   : curl http://localhost:5000/ping")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
