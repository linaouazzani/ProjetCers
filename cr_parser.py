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
            r"[Mm][ée]decin\s+responsable\s*:\s*[Dd]octeur\s+([A-Z][A-Za-z\s]+?)(?:\n|Fait|$)"
        )
        if not medecin_responsable:
            medecin_responsable = find(
                r"[Dd]octeur\s+([A-Z]+\s+[A-Z][a-z]+)"
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

        # Périmètre rotulien : chercher la ligne "Périmètre rotulien" puis
        # les 3 premières valeurs numériques sur la ligne suivante (G, D, diff)
        perimetre_g = None
        perimetre_d = None
        m_perim = re.search(
            r"[Pp][ée]rim[eè]tre\s+rotulien[^\n]*\n[^\n]*?(\d{2,3}[.,]?\d?)\s+(\d{2,3}[.,]?\d?)",
            full_text, re.DOTALL
        )
        if m_perim:
            perimetre_g = m_perim.group(1).replace(",", ".")
            perimetre_d = m_perim.group(2).replace(",", ".")

        epanchement_entree = find(
            r"EXAMEN CLINIQUE D.ENTREE.*?[Ee]panchement\s*:\s*(\w+)",
            flags=re.IGNORECASE | re.DOTALL
        )

        # ── Bilan clinique sortie ─────────────────────────────────
        douleur_meca_sortie = find(
            r"EXAMEN CLINIQUE DE SORTIE.*?Douleur m[ée]canique[^:]*:\s*([\d./]+)",
            flags=re.IGNORECASE | re.DOTALL
        )
        squat_sortie = find(
            r"EXAMEN CLINIQUE DE SORTIE.*?Squat\s+Unipodal\s*:\s*(.+?)(?:\n|Sauts)",
            flags=re.IGNORECASE | re.DOTALL
        )
        saut_sortie = find(
            r"EXAMEN CLINIQUE DE SORTIE.*?Sauts\s+Unipodal\s*:\s*(.+?)(?:\n|EVALUATIONS)",
            flags=re.IGNORECASE | re.DOTALL
        )

        # ── Sections cliniques isolées (entrée / sortie) ──────────
        m_entree_sec = re.search(
            r"EXAMEN\s+CLINIQUE\s+D.ENTR[EÉ]E(.+?)(?=EXAMEN\s+CLINIQUE\s+DE\s+SORTIE|CONCLUSION|$)",
            full_text, re.DOTALL | re.IGNORECASE
        )
        m_sortie_sec = re.search(
            r"EXAMEN\s+CLINIQUE\s+DE\s+SORTIE(.+?)(?=CONCLUSION\s+A\s+LA\s+SORTIE|CONCLUSION|$)",
            full_text, re.DOTALL | re.IGNORECASE
        )
        entree_sec_txt = m_entree_sec.group(1) if m_entree_sec else ""
        sortie_sec_txt = m_sortie_sec.group(1) if m_sortie_sec else ""

        # ── Squat / Sauts entrée (dans section ENTREE) ───────────
        squat_entree = None
        saut_entree  = None
        if entree_sec_txt:
            squat_entree = find(r"Squat\s+[Uu]nipodal\s*:\s*([^\n]+)", entree_sec_txt)
            saut_entree  = find(r"Sauts?\s+[Uu]nipodaux?\s*:\s*([^\n]+)", entree_sec_txt)

        # ── Marche entrée / sortie ────────────────────────────────
        marche_entree = None
        marche_sortie = None
        if entree_sec_txt:
            marche_entree = find(r"[Mm]arche\s*:\s*([^\n]+)", entree_sec_txt)
        if sortie_sec_txt:
            marche_sortie = find(r"[Mm]arche\s*:\s*([^\n]+)", sortie_sec_txt)

        # ── Appui monopodal entrée / sortie ───────────────────────
        appui_mono_entree = None
        appui_mono_sortie = None
        if entree_sec_txt:
            appui_mono_entree = find(r"[Aa]ppui\s+[Mm]onopodal\s*:\s*([^\n]+)", entree_sec_txt)
            if not appui_mono_entree:
                appui_mono_entree = find(r"[Aa]ppui\s+[Uu]nipodal\s*:\s*([^\n]+)", entree_sec_txt)
        if sortie_sec_txt:
            appui_mono_sortie = find(r"[Aa]ppui\s+[Mm]onopodal\s*:\s*([^\n]+)", sortie_sec_txt)
            if not appui_mono_sortie:
                appui_mono_sortie = find(r"[Aa]ppui\s+[Uu]nipodal\s*:\s*([^\n]+)", sortie_sec_txt)

        # ── Programme de rééducation (depuis le CR médical) ───────
        programme_kine_cr  = None
        programme_prepa_cr = None
        m_prog_sec = re.search(
            r"PROGRAMME\s+DE\s+R[EÉ][EÉ]DUCATION(.+?)(?=RISQUES|SIGNATURE|^Fait\s|\Z)",
            full_text, re.DOTALL | re.IGNORECASE | re.MULTILINE
        )
        if m_prog_sec:
            prog_txt = m_prog_sec.group(1)
            # Section kinésithérapie
            m_kine = re.search(
                r"[Kk]in[eé]sith[eé]rapie[^\n]*\n(.+?)(?=[Pp]r[eé]paration\s+[Pp]hysique|PREPARATION|$)",
                prog_txt, re.DOTALL | re.IGNORECASE
            )
            if m_kine:
                kine_lines = [
                    l.strip() for l in m_kine.group(1).split("\n")
                    if l.strip() and len(l.strip()) > 3
                ]
                if kine_lines:
                    programme_kine_cr = "\n".join(kine_lines)
            # Section préparation physique
            m_prepa = re.search(
                r"[Pp]r[eé]paration\s+[Pp]hysique[^\n]*\n(.+?)(?=RISQUES|SIGNATURE|^Fait\s|$)",
                prog_txt, re.DOTALL | re.IGNORECASE | re.MULTILINE
            )
            if m_prepa:
                prepa_lines = [
                    l.strip() for l in m_prepa.group(1).split("\n")
                    if l.strip() and len(l.strip()) > 3
                ]
                if prepa_lines:
                    programme_prepa_cr = "\n".join(prepa_lines)

        # État trophique régional (entrée / sortie) — essai multi-patterns
        def _extract_trophique(txt):
            if not txt:
                return None
            for pat in [
                r"[EÉeé]tat\s+[Tt]rophique[^:\n]*:\s*([^\n]+)",
                r"[EÉeé]tat\s+[Tt]rophique\s*[Rr][eé]gional[^:\n]*:\s*([^\n]+)",
                r"[Tt]rophique\s+[Rr][eé]gional[^:\n]*:\s*([^\n]+)",
                r"[Tt]rophique[^:\n]*:\s*([^\n]+)",
            ]:
                m = re.search(pat, txt, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    if val and len(val) > 1:
                        return val
            return None

        etat_trophique_entree = _extract_trophique(entree_sec_txt)
        # Fallback : chercher dans le texte complet si section vide
        if not etat_trophique_entree:
            etat_trophique_entree = _extract_trophique(full_text)

        etat_trophique_sortie = _extract_trophique(sortie_sec_txt)

        # Périmètre rotulien SORTIE
        perimetre_g_sortie = None
        perimetre_d_sortie = None
        if sortie_sec_txt:
            m_perim_s = re.search(
                r"[Pp][ée]rim[eè]tre\s+rotulien[^\n]*\n[^\n]*?(\d{2,3}[.,]?\d?)\s+(\d{2,3}[.,]?\d?)",
                sortie_sec_txt, re.DOTALL
            )
            if m_perim_s:
                perimetre_g_sortie = m_perim_s.group(1).replace(",", ".")
                perimetre_d_sortie = m_perim_s.group(2).replace(",", ".")

        # Épanchement SORTIE
        epanchement_sortie = None
        if sortie_sec_txt:
            epanchement_sortie = find(r"[Ee]panchement\s*:\s*(\w+)", sortie_sec_txt)

        # ── Conclusion ────────────────────────────────────────────
        conclusion = find(
            r"CONCLUSION A LA SORTIE\s*\n(.+?)(?=RISQUES|$)",
            flags=re.IGNORECASE | re.DOTALL
        )
        if conclusion:
            conclusion = " ".join(
                line.strip() for line in conclusion.split("\n")
                if len(line.strip()) > 10
            )

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
            # Clinique entrée
            "douleur_meca_entree":  douleur_meca_entree,
            "perimetre_rotulien_g": perimetre_g,
            "perimetre_rotulien_d": perimetre_d,
            "epanchement_entree":   epanchement_entree,
            # Clinique sortie
            "douleur_meca_sortie":  douleur_meca_sortie,
            "squat_entree":         squat_entree,
            "saut_entree":          saut_entree,
            "squat_sortie":         squat_sortie,
            "saut_sortie":          saut_sortie,
            # Fonctionnel : marche & appui monopodal
            "marche_entree":        marche_entree,
            "marche_sortie":        marche_sortie,
            "appui_mono_entree":    appui_mono_entree,
            "appui_mono_sortie":    appui_mono_sortie,
            # Programme de rééducation (extrait du CR)
            "programme_kine_cr":    programme_kine_cr,
            "programme_prepa_cr":   programme_prepa_cr,
            # État trophique régional
            "etat_trophique_entree": etat_trophique_entree,
            "etat_trophique_sortie": etat_trophique_sortie,
            # Périmètre sortie
            "perimetre_rotulien_g_sortie": perimetre_g_sortie,
            "perimetre_rotulien_d_sortie": perimetre_d_sortie,
            # Épanchement sortie
            "epanchement_sortie":   epanchement_sortie,
            # Antécédents (conservé pour compatibilité)
            "antecedents":          antecedents,
            # Conclusion complète
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
        "epanchement_entree","douleur_meca_sortie","squat_entree","saut_entree","squat_sortie","saut_sortie",
        "marche_entree","marche_sortie","appui_mono_entree","appui_mono_sortie",
        "etat_trophique_entree","etat_trophique_sortie",
        "perimetre_rotulien_g_sortie","perimetre_rotulien_d_sortie",
        "epanchement_sortie",
        "conclusion",
        "programme_kine_cr","programme_prepa_cr",
    ]} | {"antecedents": []}


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "data/compte_rendu.pdf"
    result = parse_compte_rendu(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
