"""
clubs_database.py
=================
Base de données complète des clubs sportifs
Rugby • Football • Basketball • Handball • Volleyball
"""

CLUBS_DATABASE = {

    # ══════════════════════════════════════════════
    # 🏉 RUGBY
    # ══════════════════════════════════════════════
    "rugby": {
        "label": "🏉 Rugby",
        "divisions": {

            "Top 14": [
                {"nom": "Stade Toulousain",          "couleur": "#8B1A3D"},
                {"nom": "UBB Bordeaux-Bègles",       "couleur": "#000080"},
                {"nom": "Stade Rochelais",            "couleur": "#FFD700"},
                {"nom": "ASM Clermont",               "couleur": "#FFCC00"},
                {"nom": "Racing 92",                  "couleur": "#1B5E9B"},
                {"nom": "Stade Français Paris",       "couleur": "#E63946"},
                {"nom": "Lyon OU",                    "couleur": "#C8102E"},
                {"nom": "RC Toulon",                  "couleur": "#E30613"},
                {"nom": "Section Paloise",            "couleur": "#00A86B"},
                {"nom": "Aviron Bayonnais",           "couleur": "#003087"},
                {"nom": "USA Perpignan",              "couleur": "#E30613"},
                {"nom": "Castres Olympique",          "couleur": "#003087"},
                {"nom": "Montpellier HR",             "couleur": "#003DA5"},
                {"nom": "Vannes RC",                  "couleur": "#000000"},
            ],

            "Pro D2": [
                {"nom": "Oyonnax Rugby",             "couleur": "#003087"},
                {"nom": "Mont-de-Marsan",            "couleur": "#000000"},
                {"nom": "FC Grenoble Rugby",         "couleur": "#E30613"},
                {"nom": "CA Brive",                  "couleur": "#E30613"},
                {"nom": "Aurillac",                  "couleur": "#003087"},
                {"nom": "RC Carcassonne",            "couleur": "#E30613"},
                {"nom": "Nevers",                    "couleur": "#003087"},
                {"nom": "Rouen Normandie Rugby",     "couleur": "#003087"},
                {"nom": "Valence Romans Drôme Rugby","couleur": "#003087"},
                {"nom": "Chambéry Savoie Rugby",     "couleur": "#003087"},
                {"nom": "SU Agen",                   "couleur": "#003087"},
                {"nom": "Massy Essonne Rugby",       "couleur": "#003087"},
                {"nom": "RC Béziers",                "couleur": "#E30613"},
                {"nom": "Dax",                       "couleur": "#003087"},
                {"nom": "Narbonne",                  "couleur": "#E30613"},
                {"nom": "Soyaux-Angoulême RC",       "couleur": "#003087"},
            ],

            "Nationale": [
                {"nom": "Auch",                 "couleur": "#003087"},
                {"nom": "Blagnac SC Rugby",     "couleur": "#003087"},
                {"nom": "RC Bobigny",           "couleur": "#003087"},
                {"nom": "Dijon",                "couleur": "#003087"},
                {"nom": "Langon-Castets",       "couleur": "#003087"},
                {"nom": "Nantes Rugby",         "couleur": "#FFCB00"},
                {"nom": "Nice RC",              "couleur": "#003087"},
                {"nom": "Tarbes Pyrénées Rugby","couleur": "#003087"},
            ],

            "Équipes nationales": [
                {"nom": "Équipe de France XV",          "couleur": "#002395"},
                {"nom": "Équipe d'Angleterre",          "couleur": "#FFFFFF"},
                {"nom": "All Blacks (Nouvelle-Zélande)","couleur": "#000000"},
                {"nom": "Springboks (Afrique du Sud)",  "couleur": "#006400"},
                {"nom": "Équipe d'Irlande",             "couleur": "#009A44"},
                {"nom": "Wallabies (Australie)",        "couleur": "#FFD700"},
                {"nom": "Équipe d'Écosse",              "couleur": "#003DA5"},
                {"nom": "Équipe du Pays de Galles",     "couleur": "#C8102E"},
                {"nom": "Équipe d'Italie",              "couleur": "#003DA5"},
                {"nom": "Pumas (Argentine)",            "couleur": "#74ACDF"},
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
                {"nom": "Paris Saint-Germain",      "couleur": "#003087"},
                {"nom": "Olympique de Marseille",   "couleur": "#009fc3"},
                {"nom": "Olympique Lyonnais",        "couleur": "#C8102E"},
                {"nom": "AS Monaco",                "couleur": "#E8192C"},
                {"nom": "LOSC Lille",               "couleur": "#E30613"},
                {"nom": "OGC Nice",                 "couleur": "#E30613"},
                {"nom": "Stade Rennais",            "couleur": "#E30613"},
                {"nom": "RC Lens",                  "couleur": "#E30613"},
                {"nom": "RC Strasbourg",            "couleur": "#003DA5"},
                {"nom": "Stade de Reims",           "couleur": "#E30613"},
                {"nom": "FC Nantes",                "couleur": "#FFCB00"},
                {"nom": "Stade Brestois 29",        "couleur": "#E30613"},
                {"nom": "Toulouse FC",              "couleur": "#7B1FA2"},
                {"nom": "Montpellier HSC",          "couleur": "#003DA5"},
                {"nom": "Le Havre AC",              "couleur": "#003DA5"},
                {"nom": "Angers SCO",               "couleur": "#000000"},
                {"nom": "AS Saint-Étienne",         "couleur": "#007A35"},
                {"nom": "FC Metz",                  "couleur": "#7B1FA2"},
            ],

            "Ligue 2": [
                {"nom": "AJ Auxerre",                   "couleur": "#003DA5"},
                {"nom": "Grenoble Foot 38",             "couleur": "#E30613"},
                {"nom": "En Avant Guingamp",            "couleur": "#E30613"},
                {"nom": "Stade Lavallois",              "couleur": "#F97316"},
                {"nom": "FC Lorient",                   "couleur": "#F5820D"},
                {"nom": "SC Bastia",                    "couleur": "#003DA5"},
                {"nom": "SM Caen",                      "couleur": "#003DA5"},
                {"nom": "US Dunkerque",                 "couleur": "#003DA5"},
                {"nom": "Amiens SC",                    "couleur": "#003DA5"},
                {"nom": "Rodez Aveyron Football",       "couleur": "#E30613"},
                {"nom": "ES Troyes AC",                 "couleur": "#003DA5"},
                {"nom": "Valenciennes FC",              "couleur": "#E30613"},
                {"nom": "Quevilly-Rouen Métropole",     "couleur": "#E30613"},
                {"nom": "US Concarneau",                "couleur": "#FFD700"},
                {"nom": "Martigues FC",                 "couleur": "#003DA5"},
                {"nom": "Saint-Brieuc Armor Football",  "couleur": "#E30613"},
                {"nom": "AC Ajaccio",                   "couleur": "#E30613"},
                {"nom": "Pau FC",                       "couleur": "#003DA5"},
                {"nom": "Chamois Niortais",             "couleur": "#003DA5"},
                {"nom": "FC Annecy",                    "couleur": "#003DA5"},
            ],

            "National 1": [
                {"nom": "Girondins de Bordeaux",     "couleur": "#003DA5"},
                {"nom": "Villefranche-Beaujolais",   "couleur": "#003DA5"},
                {"nom": "AS Béziers Hérault",        "couleur": "#E30613"},
                {"nom": "FC Sète",                   "couleur": "#003DA5"},
                {"nom": "US Avranches",              "couleur": "#003DA5"},
                {"nom": "Red Star FC",               "couleur": "#E30613"},
                {"nom": "LB Châteauroux",            "couleur": "#003DA5"},
                {"nom": "US Orléans Loiret",         "couleur": "#FFD700"},
                {"nom": "SO Cholet",                 "couleur": "#003DA5"},
                {"nom": "SAS Épinal",                "couleur": "#003DA5"},
                {"nom": "SC Toulon Football",        "couleur": "#E30613"},
                {"nom": "FF Fontenay-le-Comte",      "couleur": "#003DA5"},
                {"nom": "Vendée Les Herbiers Football","couleur": "#E30613"},
                {"nom": "Bergerac Périgord FC",      "couleur": "#003DA5"},
                {"nom": "CS Sedan Ardennes",         "couleur": "#E30613"},
                {"nom": "Olympique de Saumur",       "couleur": "#003DA5"},
                {"nom": "Chambly Oise",              "couleur": "#E30613"},
                {"nom": "Nîmes Olympique",           "couleur": "#E30613"},
            ],

            "Équipes nationales": [
                {"nom": "Équipe de France",   "couleur": "#002395"},
                {"nom": "Espagne",            "couleur": "#E30613"},
                {"nom": "Allemagne",          "couleur": "#000000"},
                {"nom": "Angleterre",         "couleur": "#FFFFFF"},
                {"nom": "Italie",             "couleur": "#003DA5"},
                {"nom": "Portugal",           "couleur": "#006400"},
                {"nom": "Brésil",             "couleur": "#009C3B"},
                {"nom": "Argentine",          "couleur": "#74ACDF"},
                {"nom": "Pays-Bas",           "couleur": "#FF6600"},
                {"nom": "Belgique",           "couleur": "#E30613"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # 🏀 BASKETBALL
    # ══════════════════════════════════════════════
    "basket": {
        "label": "🏀 Basketball",
        "divisions": {

            "Betclic Elite": [
                {"nom": "ASVEL Lyon-Villeurbanne",    "couleur": "#7B0041"},
                {"nom": "AS Monaco Basket",           "couleur": "#E8192C"},
                {"nom": "Paris Basketball",           "couleur": "#E30613"},
                {"nom": "Cholet Basket",              "couleur": "#E30613"},
                {"nom": "Le Mans Sarthe Basket",      "couleur": "#E30613"},
                {"nom": "JDA Dijon Basket",           "couleur": "#E30613"},
                {"nom": "JL Bourg-en-Bresse",         "couleur": "#003DA5"},
                {"nom": "Nanterre 92",                "couleur": "#003DA5"},
                {"nom": "Strasbourg IG",              "couleur": "#003DA5"},
                {"nom": "Limoges CSP",                "couleur": "#003DA5"},
                {"nom": "Rouen Métropole Basket",     "couleur": "#003DA5"},
                {"nom": "Fos Provence Basket",        "couleur": "#003DA5"},
                {"nom": "SLUC Nancy Basket",          "couleur": "#E30613"},
                {"nom": "Metropolitans 92",           "couleur": "#003DA5"},
                {"nom": "Élan Chalon",                "couleur": "#E30613"},
                {"nom": "Champagne Basket",           "couleur": "#E30613"},
                {"nom": "BCM Gravelines-Dunkerque",   "couleur": "#003DA5"},
                {"nom": "Pau-Lacq-Orthez",            "couleur": "#003DA5"},
            ],

            "Pro B": [
                {"nom": "Sharks de l'Antibes",        "couleur": "#003DA5"},
                {"nom": "Aix-Maurienne Savoie Basket","couleur": "#003DA5"},
                {"nom": "Blois Basket 41",            "couleur": "#E30613"},
                {"nom": "Élan Chalon-sur-Saône",      "couleur": "#003DA5"},
                {"nom": "Évreux Basket",              "couleur": "#003DA5"},
                {"nom": "Gries-Oberhoffen",           "couleur": "#003DA5"},
                {"nom": "Hyères-Toulon Var Basket",   "couleur": "#003DA5"},
                {"nom": "Hermine de Nantes Basket",   "couleur": "#FFCB00"},
                {"nom": "Orléans Loiret Basket",      "couleur": "#E30613"},
                {"nom": "Poitiers Basket 86",         "couleur": "#003DA5"},
                {"nom": "Champagne Basket Reims",     "couleur": "#E30613"},
                {"nom": "Saint-Quentin Basket Ball",  "couleur": "#003DA5"},
                {"nom": "Chartres Métropole Basket",  "couleur": "#003DA5"},
                {"nom": "Vichy-Clermont Basket",      "couleur": "#003DA5"},
                {"nom": "Tours TB",                   "couleur": "#003DA5"},
                {"nom": "Denain Voltaire",            "couleur": "#003DA5"},
                {"nom": "Fréjus Var Basket",          "couleur": "#003DA5"},
                {"nom": "Clermont Auvergne Basket",   "couleur": "#FFD700"},
            ],

            "Équipes nationales": [
                {"nom": "Équipe de France Basket",   "couleur": "#002395"},
                {"nom": "USA Basketball",            "couleur": "#003087"},
                {"nom": "Espagne Basket",            "couleur": "#E30613"},
                {"nom": "Australie Basket",          "couleur": "#006400"},
                {"nom": "Serbie Basket",             "couleur": "#C8102E"},
                {"nom": "Slovénie Basket",           "couleur": "#003DA5"},
                {"nom": "Grèce Basket",              "couleur": "#003DA5"},
                {"nom": "Allemagne Basket",          "couleur": "#E30613"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # 🤾 HANDBALL
    # ══════════════════════════════════════════════
    "handball": {
        "label": "🤾 Handball",
        "divisions": {

            "Starligue": [
                {"nom": "Paris Saint-Germain HB",   "couleur": "#003087"},
                {"nom": "Montpellier HB",           "couleur": "#F57C00"},
                {"nom": "HBC Nantes",               "couleur": "#FFCB00"},
                {"nom": "Fenix Toulouse HB",        "couleur": "#7B1FA2"},
                {"nom": "Aix-en-Provence THB",      "couleur": "#003DA5"},
                {"nom": "Chartres Métropole HB",    "couleur": "#003DA5"},
                {"nom": "Dunkerque HB Grand Littoral","couleur": "#E30613"},
                {"nom": "Créteil HB",               "couleur": "#003DA5"},
                {"nom": "Chambéry Savoie HB",       "couleur": "#003DA5"},
                {"nom": "Saint-Raphaël Var HB",     "couleur": "#003DA5"},
                {"nom": "US Libourne Handball",     "couleur": "#003DA5"},
                {"nom": "Cesson-Rennes MHB",        "couleur": "#E30613"},
                {"nom": "Istres Provence Handball",  "couleur": "#003DA5"},
                {"nom": "Sélestat Alsace HB",       "couleur": "#E30613"},
            ],

            "Proligue": [
                {"nom": "Billère Handball",          "couleur": "#003DA5"},
                {"nom": "Dijon Bourgogne HB",        "couleur": "#E30613"},
                {"nom": "Gonfreville HB",            "couleur": "#003DA5"},
                {"nom": "MAHB Ivry",                 "couleur": "#003DA5"},
                {"nom": "Limoges Handball",          "couleur": "#003DA5"},
                {"nom": "Massy GD HB",               "couleur": "#003DA5"},
                {"nom": "Mulhouse Handball",         "couleur": "#E30613"},
                {"nom": "Nîmes Olympique HB",        "couleur": "#E30613"},
                {"nom": "Pontault-Combault HB",      "couleur": "#003DA5"},
                {"nom": "Rennes Handball",           "couleur": "#E30613"},
                {"nom": "Sarrebourg HB",             "couleur": "#003DA5"},
                {"nom": "Sélestat HB Pro D",         "couleur": "#003DA5"},
                {"nom": "Tours HB",                  "couleur": "#003DA5"},
                {"nom": "Tremblay-en-France HB",     "couleur": "#003DA5"},
            ],

            "Division 1 Féminine": [
                {"nom": "Metz Handball",              "couleur": "#7B1FA2"},
                {"nom": "Brest Bretagne Handball",    "couleur": "#E30613"},
                {"nom": "Paris 92 Handball",          "couleur": "#003DA5"},
                {"nom": "Nantes HB Atlantique",       "couleur": "#FFCB00"},
                {"nom": "Toulon Saint-Cyr Var HB",    "couleur": "#E30613"},
                {"nom": "Fleury-les-Aubrais HB",      "couleur": "#003DA5"},
                {"nom": "Besançon Femina Sports",     "couleur": "#003DA5"},
                {"nom": "Dijon Olympic HC",           "couleur": "#E30613"},
                {"nom": "Plan-de-Cuques HB",          "couleur": "#003DA5"},
                {"nom": "Celles-sur-Belle HB",        "couleur": "#003DA5"},
                {"nom": "Mulhouse HB 68",             "couleur": "#E30613"},
                {"nom": "Chambray Touraine HB",       "couleur": "#003DA5"},
            ],
        }
    },

    # ══════════════════════════════════════════════
    # 🏐 VOLLEYBALL
    # ══════════════════════════════════════════════
    "volleyball": {
        "label": "🏐 Volleyball",
        "divisions": {

            "Ligue A Masculine": [
                {"nom": "Tours Volley-Ball",         "couleur": "#1565C0"},
                {"nom": "Chaumont Volley-Ball 52",   "couleur": "#003DA5"},
                {"nom": "Paris Volley",              "couleur": "#003DA5"},
                {"nom": "Montpellier UC Volley",     "couleur": "#003DA5"},
                {"nom": "Nantes Rezé Volley",        "couleur": "#FFCB00"},
                {"nom": "Poitiers Stade Poitevin",   "couleur": "#FFD700"},
                {"nom": "ASPTT Cannes Volley",       "couleur": "#E30613"},
                {"nom": "Tourcoing Lille Métropole VB","couleur": "#003DA5"},
                {"nom": "Volley Ball Club Ajaccio",  "couleur": "#E30613"},
                {"nom": "Toulouse Volley",           "couleur": "#7B1FA2"},
                {"nom": "Cambrai Volley",            "couleur": "#003DA5"},
                {"nom": "Arago de Sète",             "couleur": "#003DA5"},
            ],

            "Ligue A Féminine": [
                {"nom": "VB Mulhouse",               "couleur": "#E30613"},
                {"nom": "RC Cannes Volley-Ball",      "couleur": "#E30613"},
                {"nom": "Nantes Rezé Volley Féminin", "couleur": "#FFCB00"},
                {"nom": "Chamalières Volley",         "couleur": "#003DA5"},
                {"nom": "Saint-Raphaël Volley",       "couleur": "#003DA5"},
                {"nom": "Venelles Volley-Ball",       "couleur": "#003DA5"},
                {"nom": "Vandœuvre Nancy VB",         "couleur": "#E30613"},
                {"nom": "AS Le Cannet Volley",        "couleur": "#003DA5"},
                {"nom": "Béziers Angels",             "couleur": "#E30613"},
                {"nom": "Pays d'Aix Volley",          "couleur": "#003DA5"},
                {"nom": "Paris Volley Féminin",       "couleur": "#003DA5"},
                {"nom": "Terville-Florange OC Volley","couleur": "#003DA5"},
            ],

            "Équipes nationales": [
                {"nom": "Équipe de France Volley",   "couleur": "#002395"},
                {"nom": "Brésil Volley",             "couleur": "#009C3B"},
                {"nom": "USA Volley",                "couleur": "#003087"},
                {"nom": "Pologne Volley",            "couleur": "#E30613"},
                {"nom": "Russie Volley",             "couleur": "#003DA5"},
                {"nom": "Italie Volley",             "couleur": "#003DA5"},
                {"nom": "Serbie Volley",             "couleur": "#C8102E"},
                {"nom": "Slovénie Volley",           "couleur": "#003DA5"},
            ],
        }
    },
}


def get_all_clubs_flat() -> list[dict]:
    """Retourne la liste complète des clubs à plat pour la recherche."""
    clubs = []
    for sport_key, sport_data in CLUBS_DATABASE.items():
        for division, club_list in sport_data["divisions"].items():
            for club in club_list:
                clubs.append({
                    "nom":       club["nom"],
                    "sport":     sport_data["label"],
                    "sport_key": sport_key,
                    "division":  division,
                    "couleur":   club.get("couleur", "#1c3f6e"),
                    "label":     f"{sport_data['label']} — {division}",
                })
    clubs.append({
        "nom": "Autre club", "sport": "—", "sport_key": "autre",
        "division": "—", "couleur": "#555555", "label": "Autre",
    })
    return clubs


def search_clubs(query: str) -> list[dict]:
    """Recherche de clubs par nom (insensible à la casse)."""
    if not query or len(query) < 2:
        return []
    q = query.lower()
    return [c for c in get_all_clubs_flat() if q in c["nom"].lower()]


def get_clubs_by_sport(sport_key: str) -> list[dict]:
    """Retourne tous les clubs d'un sport donné."""
    if sport_key not in CLUBS_DATABASE:
        return []
    clubs = []
    sport_data = CLUBS_DATABASE[sport_key]
    for division, club_list in sport_data["divisions"].items():
        for club in club_list:
            clubs.append({
                "nom":      club["nom"],
                "division": division,
                "couleur":  club.get("couleur", "#1c3f6e"),
            })
    return clubs
