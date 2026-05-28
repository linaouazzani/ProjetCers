"""
cr_parser.py — Parser compte-rendu médical CERS Capbreton
Structure réelle confirmée par analyse pdfplumber.
"""

import re
import pdfplumber
from typing import Optional


def parse_compte_rendu(pdf_source) -> dict:
    try:
        pages_text = []
        with pdfplumber.open(pdf_source) as pdf:
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")
        full_text = "\n".join(pages_text)
    except Exception as e:
        print(f"cr_parser erreur lecture: {e}")
        return _empty_result()

    try:

        # ────────────────────────────────────────
        # UTILITAIRES
        # ────────────────────────────────────────

        def find(*patterns, text=full_text, group=1):
            for pat in patterns:
                try:
                    m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
                    if m:
                        val = m.group(group)
                        if val:
                            val = val.strip()
                            if len(val) > 1:
                                return val
                except Exception:
                    continue
            return None

        def find_date(*patterns, text=full_text):
            for pat in patterns:
                try:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        raw = m.group(1).strip()
                        if re.match(r"\d{2}/\d{2}/\d{4}", raw):
                            return raw
                        if re.match(r"\d{4}-\d{2}-\d{2}", raw):
                            p = raw.split("-")
                            return f"{p[2]}/{p[1]}/{p[0]}"
                except Exception:
                    continue
            return None

        def slice_text(text, start_patterns, end_patterns):
            """Extrait une zone entre start et end patterns."""
            start = None
            for pat in start_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    start = m.start()
                    break
            if start is None:
                return None
            end = len(text)
            for pat in end_patterns:
                m = re.search(pat, text[start:], re.IGNORECASE)
                if m:
                    end = start + m.start()
                    break
            return text[start:end]

        # ────────────────────────────────────────
        # IDENTITÉ
        # ────────────────────────────────────────

        nom_complet = find(
            r"(?:Monsieur|Madame)\s+([A-Z][A-Z\s\-]+?)\s*\n",
            r"(?:Monsieur|Madame)\s+([A-Z][A-Z\s\-]+?)\s*\(",
        )
        # Nettoyer : supprimer la répétition entre parenthèses
        # ex: "DELLA SCHIAVA (DELLA SCHIAVA) Noe" -> "DELLA SCHIAVA Noe"
        if nom_complet:
            nom_complet = re.sub(r"\s*\([^)]*\)\s*", " ", nom_complet)
            nom_complet = " ".join(nom_complet.split())

        date_naissance = find_date(
            r"[Nn][ée]\s+le\s+(\d{2}/\d{2}/\d{4})",
            r"[Nn]aissance\s*:\s*(\d{2}/\d{2}/\d{4})",
        )

        sexe = find(r"[Ss]exe\s*:\s*(Masculin|F[ée]minin|M\b|F\b)")

        medecin_responsable = find(
            r"[Mm][ée]decin\s+responsable\s*:\s*[Dd]octeur\s+([A-Z][A-Z\s]+?)(?:\n|Fait)",
            r"par\s+[Dd]octeur\s+([A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+)",
        )
        if medecin_responsable:
            # Vérifier que ce n'est pas la date
            if any(x in medecin_responsable for x in ["Fait", "CAPBRETON", "/"]):
                medecin_responsable = find(
                    r"par\s+[Dd]octeur\s+([A-Z]{2,}\s+[A-Z][a-z]{2,})"
                )

        # ────────────────────────────────────────
        # CONTEXTE SPORTIF
        # ────────────────────────────────────────

        sport = find(
            r"[Ss]port\s+pratiqu[ée]\s*:\s*(.+?)(?:\s+Niveau|\n)",
            r"[Ss]port\s*:\s*(.+?)(?:\n|·)",
        )

        club = find(
            r"[Cc]lub\s*:\s*([A-Z][A-Za-z\s\-]+?)(?:\n|Niveau|Sport|$)",
        )
        if club:
            club = club.strip().rstrip("·").strip()

        niveau = find(
            r"[Nn]iveau\s*:\s*(.+?)(?:\n|$)",
        )

        # ────────────────────────────────────────
        # DATES SÉJOUR
        # ────────────────────────────────────────

        date_entree = find_date(
            r"du\s+(\d{2}/\d{2}/\d{4})\s+au",
            r"[Ee]ntr[ée]e?\s*:\s*(\d{2}/\d{2}/\d{4})",
        )
        date_sortie = find_date(
            r"au\s+(\d{2}/\d{2}/\d{4})(?:\s*\.|$|\n)",
            r"[Ss]ortie?\s*:\s*(\d{2}/\d{2}/\d{4})",
        )

        # ────────────────────────────────────────
        # DIAGNOSTIC & INTERVENTION
        # ────────────────────────────────────────

        diagnostic = find(
            r"DIAGNOSTIC\s*:\s*(.+?)(?:\n|L[ée]sion)",
            r"[Dd]iagnostic\s*:\s*(.+?)(?:\n|$)",
        )

        lesions_associees = find(
            r"L[ée]sion\(?s?\)?\s+associ[ée]\(?s?\)?\s*:\s*(.+?)(?:\n|C[oô]t[ée])",
        )

        cote_lese = find(
            r"C[oô]t[ée]\s+l[ée]s[ée]\s*:\s*(Gauche|Droit)",
            r"[Cc][oô]t[ée]\s*:\s*(Gauche|Droit)",
        )
        if cote_lese:
            cote_lese = cote_lese.capitalize()

        date_accident = find_date(
            r"[Aa]ccident.{0,40}le\s+(\d{2}/\d{2}/\d{4})",
        )

        mecanisme = find(
            r"[Mm][ée]canisme\s*:\s*(.+?)(?:\n|$)",
        )

        intervention = find(
            r"INTERVENTION\s*:\s*(.+?)(?:\n|Geste)",
            r"INTERVENTION\s*:\s*(.+?)(?:\n|$)",
        )

        date_intervention = find_date(
            r"INTERVENTION.{0,80}(\d{2}/\d{2}/\d{4})",
            r"op[ée]r[ée].{0,30}le\s+(\d{2}/\d{2}/\d{4})",
        )

        gestes_associes = find(
            r"Geste\(?s?\)?\s+associ[ée]\(?s?\)?\s*:\s*(.+?)(?:\n|SPO)",
        )

        # Délai post-op
        delai_postop = None
        if date_intervention and date_entree:
            try:
                from datetime import datetime
                d_op  = datetime.strptime(date_intervention, "%d/%m/%Y")
                d_ent = datetime.strptime(date_entree, "%d/%m/%Y")
                delai_postop = (d_ent - d_op).days
            except Exception:
                pass

        # ────────────────────────────────────────
        # ANTÉCÉDENTS
        # ────────────────────────────────────────

        antecedents = []
        ant_block = slice_text(
            full_text,
            [r"[Mm][ée]dicaux\s*/\s*chirurgicaux\s*:"],
            [r"[Aa]llergies", r"\n\n\n"]
        )
        if ant_block:
            for line in ant_block.split("\n"):
                l = line.strip().lstrip("-•▸□◦·•oO").strip()
                l = re.sub(r"[Mm][ée]dicaux.*chirurgicaux.*:", "", l).strip()
                if l and len(l) > 4 and not re.match(r"^\d+$", l):
                    antecedents.append(l)

        # ────────────────────────────────────────
        # ZONES ENTRÉE ET SORTIE
        # ────────────────────────────────────────

        zone_entree = slice_text(
            full_text,
            [r"EXAMEN CLINIQUE D.ENTR[EÉ]E", r"EXAMEN D.ENTR[EÉ]E"],
            [r"VISITES HEBDOMADAIRES",
             r"EXAMEN CLINIQUE DE SORTIE",
             r"PROGRAMME DE R"]
        )

        zone_sortie = slice_text(
            full_text,
            [r"EXAMEN CLINIQUE DE SORTIE", r"EXAMEN DE SORTIE"],
            [r"EVALUATIONS ISOCIN",
             r"RISQUES LI[EÉ]S",
             r"ORGANISATION DE LA",
             r"CONCLUSION"]
        )

        # ────────────────────────────────────────
        # FONCTIONNEL — structure réelle CERS
        #
        # La ligne réelle dans le PDF :
        # "Marche : Normale  Unipodal : Asymétrie légère  Unipodal : Possible, manque de"
        # "puissance léger"
        # "Appui monopodal"
        # "Bilan de l'équilibre : Stable"
        # ────────────────────────────────────────

        def parse_fonctionnel_ligne(zone):
            """
            Parse la ligne fonctionnelle CERS qui contient
            Marche + Squat + Sauts sur la même ligne.
            Retourne dict avec marche, squat, saut, appui.
            """
            result = {
                "marche": None,
                "squat": None,
                "saut": None,
                "appui": None,
            }
            if not zone:
                return result

            # Chercher la ligne qui contient "Marche :" et "Unipodal :"
            # Ces lignes peuvent être fusionnées par pdfplumber
            # Pattern : "Marche : VALUE Unipodal : VALUE Unipodal : VALUE"
            # ou sur plusieurs lignes

            # Reconstituer le bloc fonctionnel
            fonc_start = re.search(
                r"FONCTIONNEL\s*\n", zone, re.IGNORECASE
            )
            if not fonc_start:
                # Chercher directement la ligne avec Marche :
                fonc_start = re.search(
                    r"Marche\s+Squat\s+Sauts", zone, re.IGNORECASE
                )
                if not fonc_start:
                    fonc_start = re.search(
                        r"Marche\s*:", zone, re.IGNORECASE
                    )

            if not fonc_start:
                return result

            # Extraire les 400 chars après le début du fonctionnel
            bloc = zone[fonc_start.start():fonc_start.start()+400]

            # Marche : chercher "Marche : VALUE" où VALUE s'arrête
            # avant le prochain label ou saut de ligne
            m_marche = re.search(
                r"[Mm]arche\s*:\s*([A-Za-zÀ-ÿ\s,]+?)(?:\s{2,}|Unipodal|Appui|\n)",
                bloc
            )
            if m_marche:
                result["marche"] = m_marche.group(1).strip().rstrip(",")

            # Squat : "Unipodal : VALUE" (premier)
            unipodaux = re.findall(
                r"[Uu]nipodal\s*:\s*([A-Za-zÀ-ÿ\s,]+?)(?:\s{2,}|Unipodal|Appui|\n|$)",
                bloc
            )
            if len(unipodaux) >= 1:
                # Nettoyer et assembler si coupé sur ligne suivante
                val = unipodaux[0].strip().rstrip(",").strip()
                result["squat"] = val

            if len(unipodaux) >= 2:
                val = unipodaux[1].strip().rstrip(",").strip()
                # Parfois la fin est sur la ligne suivante
                # Chercher si la suite est sur la ligne d'après
                m_suite = re.search(
                    r"[Uu]nipodal\s*:[^U\n]+\n([A-Za-zÀ-ÿ\s]{3,50})(?:\n|Appui)",
                    bloc
                )
                if m_suite:
                    suite = m_suite.group(1).strip()
                    if len(suite) > 2 and suite not in ["Appui monopodal"]:
                        val = val + " " + suite
                result["saut"] = val.strip()

            # Appui monopodal
            m_appui = re.search(
                r"[Bb]ilan\s+de\s+l.[ée]quilibre\s*:\s*([^\n]+)",
                bloc
            )
            if m_appui:
                result["appui"] = m_appui.group(1).strip()
            else:
                m_appui2 = re.search(
                    r"[Aa]ppui\s+monopodal[^\n]*\n\s*([^\n]{3,50})",
                    bloc
                )
                if m_appui2:
                    result["appui"] = m_appui2.group(1).strip()

            return result

        fonc_entree = parse_fonctionnel_ligne(zone_entree)
        fonc_sortie = parse_fonctionnel_ligne(zone_sortie)

        marche_entree     = fonc_entree["marche"]
        squat_entree      = fonc_entree["squat"]
        saut_entree       = fonc_entree["saut"]
        appui_mono_entree = fonc_entree["appui"]

        marche_sortie     = fonc_sortie["marche"]
        squat_sortie      = fonc_sortie["squat"]
        saut_sortie       = fonc_sortie["saut"]
        appui_mono_sortie = fonc_sortie["appui"]

        # Douleur entrée
        douleur_entree = find(
            r"[Dd]ouleur\s+m[ée]canique[^:]*:\s*([\d]+\s*/\s*\d+)",
            text=(zone_entree or full_text)
        )

        # Périmètre rotulien
        m_perim = re.search(
            r"[Pp][ée]rim[eè]tre\s+rotulien.*?\n"
            r"[^\n]*\n"
            r"\s*(\d{2,3}[.,]?\d?)\s+(\d{2,3}[.,]?\d?)",
            full_text, re.DOTALL
        )
        perimetre_g = m_perim.group(1).replace(",", ".") if m_perim else None
        perimetre_d = m_perim.group(2).replace(",", ".") if m_perim else None

        # ────────────────────────────────────────
        # PROGRAMME DE RÉÉDUCATION
        # Structure réelle :
        # "PROGRAMME DE REEDUCATION"
        # "KINESITHERAPIE"
        # "- Contenu de Travail :"
        # "• item1"
        # "PREPARATION PHYSIQUE"
        # "-Travail Cardiovasculaire :"
        # "• item1"
        # ────────────────────────────────────────

        prog_block = slice_text(
            full_text,
            [r"PROGRAMME DE R[EÉ][EÉ]DUCATION"],
            [r"EXAMEN CLINIQUE DE SORTIE",
             r"RISQUES LI[EÉ]S",
             r"CONCLUSION A LA SORTIE"]
        )

        programme_kine  = None
        programme_prepa = None

        if prog_block:
            # Zone kiné : de KINESITHERAPIE jusqu'à PREPARATION PHYSIQUE
            kine_block = slice_text(
                prog_block,
                [r"KINESITHERAPIE", r"KIN[EÉ]SITH[EÉ]RAPIE"],
                [r"PREPARATION PHYSIQUE", r"PR[EÉ]PARATION PHYSIQUE"]
            )
            if kine_block:
                lines = []
                for line in kine_block.split("\n"):
                    l = line.strip()
                    l = re.sub(r"^[-•▸□◦·•oO]\s*", "", l).strip()
                    l = re.sub(r"^KINESITHERAPIE$", "", l, flags=re.I).strip()
                    if l and len(l) > 4:
                        lines.append(l)
                programme_kine = lines if lines else None

            # Zone prépa : de PREPARATION PHYSIQUE jusqu'à la fin du bloc
            prepa_block = slice_text(
                prog_block,
                [r"PREPARATION PHYSIQUE", r"PR[EÉ]PARATION PHYSIQUE"],
                [r"\Z"]  # fin du bloc
            )
            if prepa_block:
                lines = []
                for line in prepa_block.split("\n"):
                    l = line.strip()
                    l = re.sub(r"^[-•▸□◦·•oO]\s*", "", l).strip()
                    l = re.sub(r"^PR[EÉ]PARATION\s+PHYSIQUE$", "",
                               l, flags=re.I).strip()
                    if l and len(l) > 4:
                        lines.append(l)
                programme_prepa = lines if lines else None

        # ────────────────────────────────────────
        # CONCLUSION — concaténer toutes les pages
        # pour éviter la coupure en fin de page
        # ────────────────────────────────────────

        conc_block = slice_text(
            full_text,
            [r"CONCLUSION A LA SORTIE", r"CONCLUSION\s+A\s+LA"],
            [r"RISQUES LI[EÉ]S",
             r"ORGANISATION DE LA CONTINUIT[EÉ]",
             r"\Z"]
        )

        conclusion = None
        if conc_block:
            # Nettoyer les en-têtes de page répétés (nom patient, IPP)
            lines = []
            for line in conc_block.split("\n"):
                l = line.strip()
                # Ignorer les lignes d'en-tête de page PDF
                if re.match(
                    r"(Monsieur|Madame|IPP\s*:|CONCLUSION A LA)", l, re.I
                ):
                    continue
                if l and len(l) > 10:
                    lines.append(l)
            conclusion = " ".join(lines)
            # Supprimer les doublons de mots liés aux sauts de ligne PDF
            conclusion = re.sub(r"\s{2,}", " ", conclusion)
            # Limiter à 900 chars mais sans couper au milieu d'un mot
            if len(conclusion) > 900:
                conclusion = conclusion[:900].rsplit(" ", 1)[0] + "…"

        # ────────────────────────────────────────
        # DEBUG
        # ────────────────────────────────────────

        print(f"CR nom={nom_complet!r}")
        print(f"CR naissance={date_naissance!r} sport={sport!r} club={club!r}")
        print(f"CR diagnostic={diagnostic!r}")
        print(f"CR marche_e={marche_entree!r} marche_s={marche_sortie!r}")
        print(f"CR squat_e={squat_entree!r} squat_s={squat_sortie!r}")
        print(f"CR saut_e={saut_entree!r} saut_s={saut_sortie!r}")
        print(f"CR appui_e={appui_mono_entree!r} appui_s={appui_mono_sortie!r}")
        print(f"CR kine={len(programme_kine) if programme_kine else 0} lignes")
        print(f"CR prepa={len(programme_prepa) if programme_prepa else 0} lignes")
        print(f"CR conclusion={len(conclusion) if conclusion else 0} chars")

        return {
            "nom_complet":           nom_complet,
            "date_naissance":        date_naissance,
            "sexe":                  sexe,
            "medecin_responsable":   medecin_responsable,
            "sport":                 sport,
            "club":                  club,
            "niveau":                niveau,
            "diagnostic":            diagnostic,
            "lesions_associees":     lesions_associees,
            "cote_lese":             cote_lese,
            "date_accident":         date_accident,
            "mecanisme":             mecanisme,
            "intervention":          intervention,
            "date_intervention":     date_intervention,
            "gestes_associes":       gestes_associes,
            "delai_postop_jours":    delai_postop,
            "date_entree":           date_entree,
            "date_sortie":           date_sortie,
            "douleur_entree":        douleur_entree,
            "perimetre_rotulien_g":  perimetre_g,
            "perimetre_rotulien_d":  perimetre_d,
            "marche_entree":         marche_entree,
            "marche_sortie":         marche_sortie,
            "squat_entree":          squat_entree,
            "squat_sortie":          squat_sortie,
            "saut_entree":           saut_entree,
            "saut_sortie":           saut_sortie,
            "appui_mono_entree":     appui_mono_entree,
            "appui_mono_sortie":     appui_mono_sortie,
            "antecedents":           antecedents,
            "programme_kine":        programme_kine,
            "programme_prepa":       programme_prepa,
            "conclusion":            conclusion,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _empty_result()


def _empty_result():
    return {
        "nom_complet": None, "date_naissance": None, "sexe": None,
        "medecin_responsable": None, "sport": None, "club": None,
        "niveau": None, "diagnostic": None, "lesions_associees": None,
        "cote_lese": None, "date_accident": None, "mecanisme": None,
        "intervention": None, "date_intervention": None,
        "gestes_associes": None, "delai_postop_jours": None,
        "date_entree": None, "date_sortie": None,
        "douleur_entree": None,
        "perimetre_rotulien_g": None, "perimetre_rotulien_d": None,
        "marche_entree": None, "marche_sortie": None,
        "squat_entree": None, "squat_sortie": None,
        "saut_entree": None, "saut_sortie": None,
        "appui_mono_entree": None, "appui_mono_sortie": None,
        "antecedents": [], "programme_kine": None,
        "programme_prepa": None, "conclusion": None,
    }


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "data/renduMedecin.pdf"
    result = parse_compte_rendu(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
