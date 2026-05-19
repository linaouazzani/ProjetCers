"""
cr_parser.py — Parser compte-rendu médical CERS Capbreton
Extrait les informations cliniques absentes des PDFs Biodex.
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
        print(f"cr_parser: erreur lecture PDF : {e}")
        return _empty_result()

    def find(pattern, text=full_text, group=1, flags=re.IGNORECASE):
        try:
            m = re.search(pattern, text, flags)
            if m is None:
                return None
            val = m.group(group)
            return val.strip() if val else None
        except Exception:
            return None

    def find_date(pattern, text=full_text):
        """Cherche une date et la retourne au format JJ/MM/AAAA."""
        try:
            m = re.search(pattern, text, re.IGNORECASE)
            if not m: return None
            raw = m.group(1)
            if not raw: return None
            raw = raw.strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", raw):
                parts = raw.split("-")
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
            return raw
        except Exception:
            return None

    try:
        # ── Identité ──────────────────────────────────────────────
        nom_complet = find(
            r"Monsieur|Madame\s+([\w\s\(\)]+?)\s*\n",
            full_text
        )
        if not nom_complet:
            nom_complet = find(r"(?:Monsieur|Madame)\s+(DELLA\s+SCHIAVA[\w\s]+?)(?:\n|IPP)")

        date_naissance = find_date(r"[Nn][ée]\s+le\s+(\d{2}/\d{2}/\d{4})")
        sexe = find(r"[Ss]exe\s*:\s*(\w+)")
        medecin_responsable = find(
            r"[Mm][ée]decin\s+responsable\s*:\s*(.+?)(?:\n|$)"
        )

        # ── Contexte sportif ──────────────────────────────────────
        sport = find(r"[Ss]port\s+pratiqu[ée]\s*:\s*(.+?)(?:\n|Niveau)")
        club = find(r"[Cc]lub\s*:\s*(.+?)(?:\n|Niveau)")
        niveau = find(r"[Nn]iveau\s*:\s*(.+?)(?:\n|$)")

        # ── Diagnostic ────────────────────────────────────────────
        diagnostic = find(
            r"DIAGNOSTIC\s*:\s*(.+?)(?:\n|L[ée]sion)"
        )
        lesions_associees = find(
            r"L[ée]sion\(s\)\s+associ[ée]\(s\)\s*:\s*(.+?)(?:\n|C[oô]t[ée])"
        )
        cote_lese = find(r"C[oô]t[ée]\s+l[ée]s[ée]\s*:\s*(\w+)")

        # ── Accident ──────────────────────────────────────────────
        date_accident = find_date(r"[Aa]ccident\s+.+?le\s+(\d{2}/\d{2}/\d{4})")
        mecanisme = find(r"[Mm][ée]canisme\s*:\s*(.+?)(?:\n|$)")

        # ── Intervention ──────────────────────────────────────────
        intervention = find(
            r"INTERVENTION\s*:\s*(.+?)(?:\n|Geste)"
        )
        date_intervention = find_date(
            r"(?:INTERVENTION|intervention).+?(\d{2}/\d{2}/\d{4})"
        )
        gestes_associes = find(
            r"Geste\(s\)\s+associ[ée]\(s\)\s*:\s*(.+?)(?:\n|SPO)"
        )

        # ── Dates séjour ──────────────────────────────────────────
        date_entree = find_date(r"du\s+(\d{2}/\d{2}/\d{4})\s+au")
        date_sortie = find_date(r"au\s+(\d{2}/\d{2}/\d{4})(?:\.|$|\n)")

        # ── Bilan clinique entrée ─────────────────────────────────
        douleur_meca_entree = find(
            r"EXAMEN CLINIQUE D.ENTREE.*?Douleur m[ée]canique[^:]*:\s*([\d./]+)",
            flags=re.IGNORECASE | re.DOTALL
        )
        perimetre_g = find(r"Gauche\s+([\d.]+)\s+\d")
        perimetre_d = find(r"\d+\s+([\d.]+)\s+[\d.]+\s*Epanchement")

        # ── Bilan clinique sortie ─────────────────────────────────
        squat_sortie = find(
            r"EXAMEN CLINIQUE DE SORTIE.*?Squat\s+Unipodal\s*:\s*(.+?)(?:\n|Sauts)",
            flags=re.IGNORECASE | re.DOTALL
        )
        saut_sortie = find(
            r"EXAMEN CLINIQUE DE SORTIE.*?Sauts\s+Unipodal\s*:\s*(.+?)(?:\n|EVALUATIONS)",
            flags=re.IGNORECASE | re.DOTALL
        )

        # ── Conclusion ────────────────────────────────────────────
        conclusion = find(
            r"CONCLUSION A LA SORTIE\s*\n(.+?)(?=RISQUES|$)",
            flags=re.IGNORECASE | re.DOTALL
        )
        if conclusion:
            conclusion = " ".join(
                line.strip() for line in conclusion.split("\n")
                if len(line.strip()) > 20
            )[:800]

        # ── Antécédents ──────────────────────────────────────────
        antecedents_block = find(
            r"M[ée]dicaux / chirurgicaux\s*:\s*\n(.+?)(?=Allergies|$)",
            flags=re.IGNORECASE | re.DOTALL
        )
        antecedents = []
        if antecedents_block:
            for line in antecedents_block.split("\n"):
                l = line.strip()
                if l and len(l) > 3:
                    antecedents.append(l)

        # ── Délai post-opératoire ────────────────────────────────
        delai_postop = None
        if date_intervention and date_entree:
            try:
                from datetime import datetime
                d_op = datetime.strptime(date_intervention, "%d/%m/%Y")
                d_ent = datetime.strptime(date_entree, "%d/%m/%Y")
                delai_postop = (d_ent - d_op).days
            except Exception:
                pass

        return {
            # Identité
            "nom_complet":          nom_complet,
            "date_naissance":       date_naissance,
            "sexe":                 sexe,
            "medecin_responsable":  medecin_responsable,
            # Contexte sportif
            "sport":                sport,
            "club":                 club,
            "niveau":               niveau,
            # Diagnostic
            "diagnostic":           diagnostic,
            "lesions_associees":    lesions_associees,
            "cote_lese":            cote_lese,
            # Accident & intervention
            "date_accident":        date_accident,
            "mecanisme":            mecanisme,
            "intervention":         intervention,
            "date_intervention":    date_intervention,
            "gestes_associes":      gestes_associes,
            "delai_postop_jours":   delai_postop,
            # Séjour
            "date_entree":          date_entree,
            "date_sortie":          date_sortie,
            # Clinique
            "douleur_meca_entree":  douleur_meca_entree,
            "perimetre_rotulien_g": perimetre_g,
            "perimetre_rotulien_d": perimetre_d,
            "squat_sortie":         squat_sortie,
            "saut_sortie":          saut_sortie,
            # Antécédents
            "antecedents":          antecedents,
            # Conclusion
            "conclusion":           conclusion,
        }
    except Exception as e:
        print(f"cr_parser: erreur parsing : {e}")
        import traceback
        traceback.print_exc()
        return _empty_result()


def _empty_result() -> dict:
    return {k: None for k in [
        "nom_complet","date_naissance","sexe","medecin_responsable",
        "sport","club","niveau","diagnostic","lesions_associees","cote_lese",
        "date_accident","mecanisme","intervention","date_intervention",
        "gestes_associes","delai_postop_jours","date_entree","date_sortie",
        "douleur_meca_entree","perimetre_rotulien_g","perimetre_rotulien_d",
        "squat_sortie","saut_sortie","conclusion",
    ]} | {"antecedents": []}


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "data/compte_rendu.pdf"
    result = parse_compte_rendu(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
