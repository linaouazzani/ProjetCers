"""
cr_parser.py — Parser compte-rendu médical CERS Capbreton
Extrait les informations cliniques absentes des PDFs Biodex.
Regex multi-tentatives : fonctionne pour n'importe quel rendu CERS.
"""

import re
import pdfplumber
from typing import Optional


def parse_compte_rendu(pdf_source) -> dict:
    """
    Parse le PDF compte-rendu médical CERS.
    pdf_source : chemin str ou BytesIO.

    Retourne un dict avec toutes les infos extraites.
    Toutes les valeurs peuvent être None si non trouvées — jamais d'exception.
    """
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
        def find(*patterns, text=full_text, group=1):
            """Essaie plusieurs patterns ; retourne le premier match."""
            for pat in patterns:
                try:
                    m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
                    if m:
                        val = m.group(group)
                        return val.strip() if val else None
                except Exception:
                    continue
            return None

        def find_date(*patterns, text=full_text):
            """Cherche une date et la normalise en JJ/MM/AAAA."""
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

        def find_block(*start_patterns, end_patterns=None, text=full_text):
            """Extrait un bloc de texte entre un début et une fin."""
            end_patterns = end_patterns or [
                r"\n[A-ZÀ-ÿ][A-ZÀ-ÿ\s]{3,}\n",
                r"\n\n\n"
            ]
            for pat in start_patterns:
                try:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        start = m.end()
                        remaining = text[start:]
                        end = len(remaining)
                        for ep in end_patterns:
                            em = re.search(ep, remaining)
                            if em and em.start() < end:
                                end = em.start()
                        return remaining[:end].strip()
                except Exception:
                    continue
            return None

        # ── Identité ──────────────────────────────────────────
        nom_complet = find(
            r"(?:Monsieur|Madame|M\.|Mme)\s+([A-Z][A-Z\s\-]+[A-Za-z]+)\s*\n",
            r"(?:Nom|NOM)\s*(?:du patient|:)\s*([A-Z][A-Z\s\-]+)",
            r"Profile\s*:\s*([A-Z][A-Za-z\s\-]+?)(?:\n|Report)",
        )

        date_naissance = find_date(
            r"[Nn][ée]\s+le\s+(\d{2}/\d{2}/\d{4})",
            r"[Dd]ate\s+de\s+naissance\s*:\s*(\d{2}/\d{2}/\d{4})",
            r"\((\d{2}\s+\w+\s+\d{4})\)",
            r"(\d{2}/\d{2}/\d{4})\s*\(",
        )

        sexe = find(
            r"[Ss]exe\s*:\s*(\w+)",
            r"sexe\s*:\s*(Masculin|F[ée]minin|M|F)\b",
        )

        medecin_responsable = find(
            r"[Mm][ée]decin\s+responsable\s*:\s*[Dd]octeur\s+([A-Z][A-Z\s]+?)(?:\n|Fait|$)",
            r"[Dd]octeur\s+([A-Z]+\s+[A-Z][a-z]+)(?:\s*\n|,|\s+Visite)",
            r"[Dd]r\s+([A-Z]+\s+[A-Z][a-z]+)",
        )
        # Nettoyer si le match contient "Fait à" ou "CAPBRETON"
        if medecin_responsable and (
            "Fait" in medecin_responsable or "CAPBRETON" in medecin_responsable
        ):
            medecin_responsable = find(
                r"[Dd]octeur\s+([A-Z]{2,}\s+[A-Z][a-z]{2,})"
            )

        # ── Contexte sportif ──────────────────────────────────
        sport = find(
            r"[Ss]port\s+pratiqu[ée]\s*:\s*(.+?)(?:\n|Niveau|Club)",
            r"[Ss]port\s*:\s*(.+?)(?:\n|·|$)",
        )
        if sport:
            sport = sport.strip().rstrip("·").strip()

        club = find(
            r"[Cc]lub\s*:\s*(.+?)(?:\n|Niveau|Sport|$)",
            r"[Cc]lub\s+:\s+([A-Z][A-Za-z\s\-]+?)(?:\n|$)",
        )

        niveau = find(
            r"[Nn]iveau\s*:\s*(.+?)(?:\n|$)",
            r"[Nn]ational|[Rr][ée]gional|[Ll]ocal|[Pp]rofessionnel",
        )

        # ── Diagnostic ────────────────────────────────────────
        diagnostic = find(
            r"DIAGNOSTIC\s*:\s*(.+?)(?:\n|L[ée]sion)",
            r"[Dd]iagnostic\s*:\s*(.+?)(?:\n|$)",
        )

        lesions_associees = find(
            r"L[ée]sion\(?s?\)?\s+associ[ée]\(?s?\)?\s*:\s*(.+?)(?:\n|C[oô]t[ée])",
            r"[Ll][ée]sions?\s+:\s*(.+?)(?:\n|$)",
        )

        cote_lese = find(
            r"C[oô]t[ée]\s+l[ée]s[ée]\s*:\s*(Gauche|Droit|gauche|droit)",
            r"[Cc][oô]t[ée]\s*:\s*(Gauche|Droit)",
        )
        if cote_lese:
            cote_lese = cote_lese.capitalize()

        # ── Accident ──────────────────────────────────────────
        date_accident = find_date(
            r"[Aa]ccident\s+.{0,30}le\s+(\d{2}/\d{2}/\d{4})",
            r"[Aa]ccident\s+:\s+.{0,30}(\d{2}/\d{2}/\d{4})",
        )

        mecanisme = find(
            r"[Mm][ée]canisme\s*:\s*(.+?)(?:\n|$)",
            r"[Mm][ée]canisme\s+:\s*(.{3,80}?)(?:\n|$)",
        )

        # ── Intervention ──────────────────────────────────────
        intervention = find(
            r"INTERVENTION\s*:\s*(.+?)(?:\n|Geste|Date)",
            r"[Ii]ntervention\s*:\s*(.+?)(?:\n|$)",
        )

        date_intervention = find_date(
            r"(?:INTERVENTION|intervention).{0,60}(\d{2}/\d{2}/\d{4})",
            r"op[ée]r[ée]\s+le\s+(\d{2}/\d{2}/\d{4})",
        )

        gestes_associes = find(
            r"Geste\(?s?\)?\s+associ[ée]\(?s?\)?\s*:\s*(.+?)(?:\n|SPO|$)",
        )

        # ── Dates séjour ──────────────────────────────────────
        date_entree = find_date(
            r"du\s+(\d{2}/\d{2}/\d{4})\s+au",
            r"[Ee]ntr[ée]e?\s*:\s*(\d{2}/\d{2}/\d{4})",
        )
        date_sortie = find_date(
            r"au\s+(\d{2}/\d{2}/\d{4})(?:\.|$|\n)",
            r"[Ss]ortie?\s*:\s*(\d{2}/\d{2}/\d{4})",
        )

        # ── Délai post-op ─────────────────────────────────────
        delai_postop = None
        if date_intervention and date_entree:
            try:
                from datetime import datetime
                d_op  = datetime.strptime(date_intervention, "%d/%m/%Y")
                d_ent = datetime.strptime(date_entree,       "%d/%m/%Y")
                delai_postop = (d_ent - d_op).days
            except Exception:
                pass

        # ── Bilan fonctionnel ─────────────────────────────────

        def extract_zone(text, start_keywords, end_keywords):
            """
            Extrait une zone de texte entre des mots-clés de début et de fin.
            Retourne None si non trouvé.
            """
            start_pos = None
            for kw in start_keywords:
                m = re.search(kw, text, re.IGNORECASE)
                if m:
                    start_pos = m.start()
                    break
            if start_pos is None:
                return None

            end_pos = len(text)
            for kw in end_keywords:
                m = re.search(kw, text[start_pos:], re.IGNORECASE)
                if m:
                    candidate = start_pos + m.start()
                    if candidate > start_pos and candidate < end_pos:
                        end_pos = candidate
            return text[start_pos:end_pos]

        def get_fonctionnel(zone, label_patterns):
            """
            Cherche une valeur fonctionnelle dans une zone de texte.
            Essaie plusieurs patterns successivement.
            """
            if not zone:
                return None
            for pat in label_patterns:
                try:
                    m = re.search(pat, zone, re.IGNORECASE | re.DOTALL)
                    if m:
                        val = m.group(1).strip()
                        # Garder seulement la première ligne utile
                        val = val.split("\n")[0].strip()
                        val = re.sub(r"\s+", " ", val)
                        if len(val) > 2 and len(val) < 100:
                            return val
                except Exception:
                    continue
            return None

        # Découper le texte en zone ENTRÉE et zone SORTIE
        zone_entree = extract_zone(
            full_text,
            start_keywords=[
                r"EXAMEN CLINIQUE D.ENTR[EÉ]E",
                r"EXAMEN D.ENTR[EÉ]E",
            ],
            end_keywords=[
                r"VISITES HEBDOMADAIRES",
                r"EXAMEN CLINIQUE DE SORTIE",
                r"PROGRAMME DE R[EÉ][EÉ]DUCATION",
                r"EVALUATIONS ISOCIN[EÉ]TIQUES",
            ]
        )

        zone_sortie = extract_zone(
            full_text,
            start_keywords=[
                r"EXAMEN CLINIQUE DE SORTIE",
                r"EXAMEN DE SORTIE",
            ],
            end_keywords=[
                r"EVALUATIONS ISOCIN[EÉ]TIQUES",
                r"RISQUES LI[EÉ]S",
                r"ORGANISATION DE LA CONTINUIT[EÉ]",
                r"CONCLUSION",
            ]
        )

        # Marche
        marche_entree = get_fonctionnel(zone_entree, [
            r"[Mm]arche\s*\n\s*[Mm]arche\s*:\s*([^\n]+)",
            r"[Mm]arche\s*:\s*([^\n]+)",
            r"[Mm]arch[ée]\s*:\s*([^\n]+)",
        ])
        marche_sortie = get_fonctionnel(zone_sortie, [
            r"[Mm]arche\s*\n\s*[Mm]arche\s*:\s*([^\n]+)",
            r"[Mm]arche\s*:\s*([^\n]+)",
            r"[Mm]arch[ée]\s*:\s*([^\n]+)",
        ])

        # Squat
        squat_entree = get_fonctionnel(zone_entree, [
            r"[Ss]quat\s*\n\s*[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]quat\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]quat\s*:\s*([^\n]+)",
        ])
        squat_sortie = get_fonctionnel(zone_sortie, [
            r"[Ss]quat\s*\n\s*[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]quat\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]quat\s*:\s*([^\n]+)",
        ])

        # Sauts
        saut_entree = get_fonctionnel(zone_entree, [
            r"[Ss]auts?\s*\n\s*[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]auts?\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]aut\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]auts?\s*:\s*([^\n]+)",
        ])
        saut_sortie = get_fonctionnel(zone_sortie, [
            r"[Ss]auts?\s*\n\s*[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]auts?\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]aut\s+[Uu]nipodal\s*:\s*([^\n]+)",
            r"[Ss]auts?\s*:\s*([^\n]+)",
        ])

        # Appui monopodal
        appui_mono_entree = get_fonctionnel(zone_entree, [
            r"[Aa]ppui\s+monopodal\s*\n[^\n]*\n\s*[Bb]ilan[^:]*:\s*([^\n]+)",
            r"[Bb]ilan\s+de\s+l.[ée]quilibre\s*:\s*([^\n]+)",
            r"[Ee]quilibre\s*:\s*([^\n]+)",
            r"[Aa]ppui\s+monopodal[^\n]*\n\s*([^\n]+)",
            r"[Aa]ppui\s+mono\w*\s*:\s*([^\n]+)",
        ])
        appui_mono_sortie = get_fonctionnel(zone_sortie, [
            r"[Aa]ppui\s+monopodal\s*\n[^\n]*\n\s*[Bb]ilan[^:]*:\s*([^\n]+)",
            r"[Bb]ilan\s+de\s+l.[ée]quilibre\s*:\s*([^\n]+)",
            r"[Ee]quilibre\s*:\s*([^\n]+)",
            r"[Aa]ppui\s+monopodal[^\n]*\n\s*([^\n]+)",
            r"[Aa]ppui\s+mono\w*\s*:\s*([^\n]+)",
        ])

        douleur_entree = find(
            r"EXAMEN CLINIQUE D.ENTREE.*?[Mm][ée]canique[^:]*:\s*([\d/]+)",
        )

        # Périmètre rotulien
        m_perim = re.search(
            r"[Pp][ée]rim[eè]tre\s+rotulien.*?\n"
            r"\s*(?:Gauche\s+)?(\d{2,3}[.,]?\d?)\s+(\d{2,3}[.,]?\d?)",
            full_text, re.DOTALL
        )
        perimetre_g = m_perim.group(1).replace(",", ".") if m_perim else None
        perimetre_d = m_perim.group(2).replace(",", ".") if m_perim else None

        # ── Programme de rééducation ──────────────────────────
        prog_block = find_block(
            r"PROGRAMME\s+DE\s+R[EÉ][EÉ]DUCATION",
            end_patterns=[
                r"\nEXAMEN CLINIQUE DE SORTIE",
                r"\nRISQUES",
                r"\nCONCLUSION",
            ]
        )

        # Kinésithérapie
        programme_kine = None
        if prog_block:
            kine_block = find_block(
                r"KIN[ÉE]SITH[ÉE]RAPIE",
                end_patterns=[r"\nPR[EÉ]PARATION", r"\n[A-Z]{4,}"],
                text=prog_block
            )
            if kine_block:
                lines = [l.strip() for l in kine_block.split("\n")
                         if l.strip() and len(l.strip()) > 3]
                programme_kine = lines if lines else None

        # Préparation physique
        programme_prepa = None
        if prog_block:
            prepa_block = find_block(
                r"PR[EÉ]PARATION\s+PHYSIQUE",
                end_patterns=[r"\nEXAMEN", r"\nRISQUES", r"\nCONCLUSION"],
                text=prog_block
            )
            if prepa_block:
                lines = [l.strip() for l in prepa_block.split("\n")
                         if l.strip() and len(l.strip()) > 3]
                programme_prepa = lines if lines else None

        # ── Antécédents ───────────────────────────────────────
        antecedents_block = find_block(
            r"[Mm][ée]dicaux\s*/\s*chirurgicaux\s*:",
            end_patterns=[r"\n[Aa]llergies", r"\n\n\n"]
        )
        antecedents = []
        if antecedents_block:
            for line in antecedents_block.split("\n"):
                l = line.strip().lstrip("-•▸□").strip()
                if l and len(l) > 3 and not re.match(r"^\d+$", l):
                    antecedents.append(l)

        # ── Conclusion ────────────────────────────────────────
        conclusion_block = find_block(
            r"CONCLUSION\s+[AÀ]\s+LA\s+SORTIE",
            end_patterns=[r"\n\n\n", r"\nRISQUES", r"$"]
        )
        conclusion = None
        if conclusion_block:
            lines = [l.strip() for l in conclusion_block.split("\n")
                     if l.strip() and len(l.strip()) > 15]
            conclusion = " ".join(lines)[:900]

        return {
            # Identité
            "nom_complet":           nom_complet,
            "date_naissance":        date_naissance,
            "sexe":                  sexe,
            "medecin_responsable":   medecin_responsable,
            # Contexte sportif
            "sport":                 sport,
            "club":                  club,
            "niveau":                niveau,
            # Diagnostic
            "diagnostic":            diagnostic,
            "lesions_associees":     lesions_associees,
            "cote_lese":             cote_lese,
            # Accident & intervention
            "date_accident":         date_accident,
            "mecanisme":             mecanisme,
            "intervention":          intervention,
            "date_intervention":     date_intervention,
            "gestes_associes":       gestes_associes,
            "delai_postop_jours":    delai_postop,
            # Séjour
            "date_entree":           date_entree,
            "date_sortie":           date_sortie,
            # Bilan fonctionnel
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
            # Programme de rééducation (listes de lignes)
            "programme_kine":        programme_kine,
            "programme_prepa":       programme_prepa,
            # Antécédents & conclusion
            "antecedents":           antecedents,
            "conclusion":            conclusion,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _empty_result()


def _empty_result() -> dict:
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
    path = sys.argv[1] if len(sys.argv) > 1 else "data/compte_rendu.pdf"
    result = parse_compte_rendu(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
