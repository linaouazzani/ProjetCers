"""
clubs_database.py
=================
Base de données complète des clubs sportifs français
Rugby (Top 14 + Pro D2 + Nationale)
Football (Ligue 1 + Ligue 2)
Basketball (Betclic Elite)
Handball (Starligue)

Chaque club a : nom, logo_url, sport, division, couleur_principale
"""

CLUBS_DATABASE = {

    # ══════════════════════════════════════════════
    # 🏉 RUGBY
    # ══════════════════════════════════════════════
    "rugby": {
        "label": "🏉 Rugby",
        "divisions": {

            "Top 14": [
                {"nom": "ASM Clermont",         "couleur": "#FCD116"},
                {"nom": "Stade Toulousain",      "couleur": "#8B0000"},
                {"nom": "Racing 92",             "couleur": "#004A9E"},
                {"nom": "Stade Français Paris",  "couleur": "#E91E8C"},
                {"nom": "UBB Bordeaux-Bègles",  "couleur": "#001F5B"},
                {"nom": "RC Toulon",             "couleur": "#E30613"},
                {"nom": "Stade Rochelais",       "couleur": "#FFCB00"},
                {"nom": "Lyon OU",               "couleur": "#E30613"},
                {"nom": "Montpellier HR",        "couleur": "#003DA5"},
                {"nom": "Section Paloise",       "couleur": "#00A86B"},
                {"nom": "Castres Olympique",     "couleur": "#003087"},
                {"nom": "Bayonne",               "couleur": "#003087"},
                {"nom": "Perpignan",             "couleur": "#E30613"},
                {"nom": "Vannes",                "couleur": "#000000"},
            ],

            "Pro D2": [
                {"nom": "Brive",            "couleur": "#E30613"},
                {"nom": "Aurillac",         "couleur": "#003087"},
                {"nom": "Oyonnax",          "couleur": "#003087"},
                {"nom": "Béziers",          "couleur": "#E30613"},
                {"nom": "Rouen",            "couleur": "#003087"},
                {"nom": "Grenoble",         "couleur": "#E30613"},
                {"nom": "Nevers",           "couleur": "#003087"},
                {"nom": "Mont-de-Marsan",   "couleur": "#000000"},
                {"nom": "Provence Rugby",   "couleur": "#0070B8"},
                {"nom": "Carcassonne",      "couleur": "#E30613"},
                {"nom": "Massy",            "couleur": "#003087"},
                {"nom": "Narbonne",         "couleur": "#E30613"},
                {"nom": "Valence Romans",   "couleur": "#003087"},
                {"nom": "Angoulême",        "couleur": "#000000"},
            ],

            "Nationale": [
                {"nom": "Dax",              "couleur": "#003087"},
                {"nom": "Nice RC",          "couleur": "#003087"},
                {"nom": "Albi",             "couleur": "#E30613"},
                {"nom": "Bourgoin-Jallieu", "couleur": "#003087"},
                {"nom": "Blagnac",          "couleur": "#003087"},
                {"nom": "Suresnes",         "couleur": "#003087"},
            ],

            "International": [
                {"nom": "Équipe de France XV", "couleur": "#002395"},
                {"nom": "Équipe de France 7",  "couleur": "#002395"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # ⚽ FOOTBALL
    # ══════════════════════════════════════════════
    "football": {
        "label": "⚽ Football",
        "divisions": {

            "Ligue 1": [
                {"nom": "PSG",                      "couleur": "#004170"},
                {"nom": "Olympique de Marseille",   "couleur": "#009AC7"},
                {"nom": "Olympique Lyonnais",        "couleur": "#B01C2E"},
                {"nom": "Monaco",                   "couleur": "#E30613"},
                {"nom": "Lille OSC",                "couleur": "#E30613"},
                {"nom": "Stade Rennais",            "couleur": "#E30613"},
                {"nom": "OGC Nice",                 "couleur": "#E30613"},
                {"nom": "RC Lens",                  "couleur": "#E30613"},
                {"nom": "RC Strasbourg",            "couleur": "#003DA5"},
                {"nom": "FC Nantes",                "couleur": "#FFCB00"},
                {"nom": "Stade Brestois",           "couleur": "#E30613"},
                {"nom": "Stade de Reims",           "couleur": "#E30613"},
                {"nom": "Toulouse FC",              "couleur": "#7B1FA2"},
                {"nom": "Montpellier HSC",          "couleur": "#003DA5"},
                {"nom": "Le Havre AC",              "couleur": "#003DA5"},
                {"nom": "Girondins de Bordeaux",    "couleur": "#003DA5"},
                {"nom": "Angers SCO",               "couleur": "#000000"},
                {"nom": "Saint-Étienne",            "couleur": "#007A35"},
            ],

            "Ligue 2": [
                {"nom": "Metz",             "couleur": "#7B1FA2"},
                {"nom": "Lorient",          "couleur": "#F5820D"},
                {"nom": "Caen",             "couleur": "#003DA5"},
                {"nom": "Grenoble Foot",    "couleur": "#E30613"},
                {"nom": "Guingamp",         "couleur": "#E30613"},
                {"nom": "Valenciennes",     "couleur": "#E30613"},
                {"nom": "Rodez AF",         "couleur": "#E30613"},
                {"nom": "Laval",            "couleur": "#E30613"},
                {"nom": "Clermont Foot",    "couleur": "#003DA5"},
                {"nom": "Pau FC",           "couleur": "#003DA5"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # 🏀 BASKETBALL
    # ══════════════════════════════════════════════
    "basket": {
        "label": "🏀 Basketball",
        "divisions": {

            "Betclic Elite (Pro A)": [
                {"nom": "ASVEL Lyon-Villeurbanne",  "couleur": "#003DA5"},
                {"nom": "Paris Basketball",         "couleur": "#E30613"},
                {"nom": "Monaco Basket",            "couleur": "#E30613"},
                {"nom": "Boulogne-Levallois",       "couleur": "#003DA5"},
                {"nom": "Le Mans Sarthe Basket",    "couleur": "#E30613"},
                {"nom": "Strasbourg IG",            "couleur": "#003DA5"},
                {"nom": "Nanterre 92",              "couleur": "#E30613"},
                {"nom": "Limoges CSP",              "couleur": "#003DA5"},
                {"nom": "Cholet Basket",            "couleur": "#E30613"},
                {"nom": "Dijon BM",                 "couleur": "#E30613"},
                {"nom": "Pau-Lacq-Orthez",         "couleur": "#003DA5"},
                {"nom": "JDA Dijon",                "couleur": "#E30613"},
                {"nom": "Elan Chalon",              "couleur": "#E30613"},
                {"nom": "Metropolitans 92",         "couleur": "#003DA5"},
            ],

            "Pro B": [
                {"nom": "Blois Basket",         "couleur": "#E30613"},
                {"nom": "Orléans Loiret Basket","couleur": "#E30613"},
                {"nom": "Élan Chalon",          "couleur": "#003DA5"},
                {"nom": "Antibes Sharks",       "couleur": "#003DA5"},
                {"nom": "Aix-Maurienne",        "couleur": "#003DA5"},
                {"nom": "Tours TBC",            "couleur": "#003DA5"},
                {"nom": "Vichy-Clermont",       "couleur": "#003DA5"},
                {"nom": "Fos Provence Basket",  "couleur": "#003DA5"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # 🤾 HANDBALL
    # ══════════════════════════════════════════════
    "handball": {
        "label": "🤾 Handball",
        "divisions": {

            "Starligue (D1 Masculine)": [
                {"nom": "Paris Saint-Germain HB",       "couleur": "#004170"},
                {"nom": "Montpellier HB",               "couleur": "#003DA5"},
                {"nom": "Nîmes Olympique HB",           "couleur": "#E30613"},
                {"nom": "Chambéry SHB",                 "couleur": "#003DA5"},
                {"nom": "Fenix Toulouse HB",            "couleur": "#7B1FA2"},
                {"nom": "Aix-en-Provence THB",         "couleur": "#003DA5"},
                {"nom": "Dunkerque HB Grand Littoral",  "couleur": "#E30613"},
                {"nom": "Saint-Raphaël VHB",            "couleur": "#003DA5"},
                {"nom": "Pays d'Aix UC",                "couleur": "#003DA5"},
                {"nom": "Limoges HB",                   "couleur": "#003DA5"},
                {"nom": "Sélestat AHB",                 "couleur": "#E30613"},
                {"nom": "Créteil HB",                   "couleur": "#003DA5"},
                {"nom": "Istres PH",                    "couleur": "#003DA5"},
                {"nom": "Tremblay-en-France HB",        "couleur": "#003DA5"},
            ],

            "Proligue (D2 Masculine)": [
                {"nom": "Cesson-Rennes MHB",    "couleur": "#003DA5"},
                {"nom": "Lyon HB",              "couleur": "#003DA5"},
                {"nom": "Nantes HB",            "couleur": "#FFCB00"},
                {"nom": "Massy GD HB",          "couleur": "#003DA5"},
                {"nom": "Chartres MHB",         "couleur": "#003DA5"},
            ],

            "Ligue Butagaz Énergie (D1 Féminine)": [
                {"nom": "Brest Bretagne HB",    "couleur": "#E30613"},
                {"nom": "Metz HB",              "couleur": "#7B1FA2"},
                {"nom": "Nîmes HB",             "couleur": "#E30613"},
                {"nom": "Touraine Loire Valley","couleur": "#003DA5"},
                {"nom": "Fleury les Aubrais",   "couleur": "#003DA5"},
                {"nom": "Dijon Bourgogne HB",   "couleur": "#E30613"},
            ],
        }
    },
}


def get_all_clubs_flat() -> list[dict]:
    """
    Retourne la liste complète des clubs à plat pour la recherche.
    Chaque club a : nom, sport, division, couleur
    """
    clubs = []
    for sport_key, sport_data in CLUBS_DATABASE.items():
        for division, club_list in sport_data["divisions"].items():
            for club in club_list:
                clubs.append({
                    "nom":      club["nom"],
                    "sport":    sport_data["label"],
                    "sport_key": sport_key,
                    "division": division,
                    "couleur":  club.get("couleur", "#1c3f6e"),
                    "label":    f"{sport_data['label']} — {division}",
                })
    # Ajouter option "Autre"
    clubs.append({
        "nom": "Autre club",
        "sport": "—",
        "sport_key": "autre",
        "division": "—",
        "couleur": "#555555",
        "label": "Autre",
    })
    return clubs


def search_clubs(query: str) -> list[dict]:
    """
    Recherche de clubs par nom (insensible à la casse).
    Retourne les clubs dont le nom contient la query.
    """
    if not query or len(query) < 2:
        return []
    q = query.lower()
    all_clubs = get_all_clubs_flat()
    return [c for c in all_clubs if q in c["nom"].lower()]


def get_clubs_by_sport(sport_key: str) -> list[dict]:
    """Retourne tous les clubs d'un sport donné."""
    if sport_key not in CLUBS_DATABASE:
        return []
    clubs = []
    sport_data = CLUBS_DATABASE[sport_key]
    for division, club_list in sport_data["divisions"].items():
        for club in club_list:
            clubs.append({
                "nom": club["nom"],
                "division": division,
                "couleur": club.get("couleur", "#1c3f6e"),
            })
    return clubs


if __name__ == "__main__":
    all_clubs = get_all_clubs_flat()
    print(f"Total clubs : {len(all_clubs)}")
    for sport_key, sport_data in CLUBS_DATABASE.items():
        total = sum(len(c) for c in sport_data["divisions"].values())
        print(f"  {sport_data['label']} : {total} clubs")

    print("\nRecherche 'Paris' :")
    for c in search_clubs("Paris"):
        print(f"  → {c['nom']} ({c['sport']} — {c['division']})")