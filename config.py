# Bar Traders Configuration

# Price update interval in seconds
PRICE_UPDATE_INTERVAL = 90

# Krash duration in seconds (5 minutes by default)
KRASH_DURATION = 300

# Database file — chemin absolu pour éviter les ambiguïtés selon le CWD de lancement
import os as _os
DATABASE_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'bar_traders.db')

# Default drink types
DEFAULT_DRINK_TYPES = [
    ('Bière',      '🍺', 1),
    ('Soft',       '🥤', 2),
    ('Cocktail',   '🍹', 3),
    ('Alcool Fort','🥃', 4),
    ('Autres',     '🍷', 4),
]

# Default drinks data
DEFAULT_DRINKS = [
    # Bières
    {"name": "Chipek 25cl",   "type": "Bière", "price_min": 3.5, "price_max": 6.0,  "price_krash": 3.0, "tva": 8.5},
    {"name": "Chipek 50cl",   "type": "Bière", "price_min": 3.0, "price_max": 6.0,  "price_krash": 2.0, "tva": 8.5},
    {"name": "Desperados",    "type": "Bière", "price_min": 6.5, "price_max": 9.0,  "price_krash": 5.0, "tva": 8.5},
    {"name": "Grim 50cl",     "type": "Bière", "price_min": 6.5, "price_max": 10.0, "price_krash": 5.5, "tva": 8.5},
    {"name": "Heineken Btl",  "type": "Bière", "price_min": 3.0, "price_max": 5.0,  "price_krash": 2.5, "tva": 8.5},
    {"name": "Phoenix 25cl",  "type": "Bière", "price_min": 3.5, "price_max": 7.0,  "price_krash": 2.5, "tva": 8.5},
    {"name": "Phoenix 50cl",  "type": "Bière", "price_min": 2.5, "price_max": 5.5,  "price_krash": 1.5, "tva": 8.5},
    {"name": "Slash",         "type": "Bière", "price_min": 5.5, "price_max": 9.0,  "price_krash": 4.0, "tva": 8.5},

    # Softs
    {"name": "Boisson Energisante", "type": "Soft", "price_min": 3.5, "price_max": 6.5, "price_krash": 1.0, "tva": 2.1},
    {"name": "Ginger Beer",         "type": "Soft", "price_min": 4.0, "price_max": 7.0, "price_krash": 3.0, "tva": 2.1},
    {"name": "Soft Classique",      "type": "Soft", "price_min": 2.0, "price_max": 4.0, "price_krash": 1.0, "tva": 2.1},

    # Cocktails
    {"name": "Cocktail Classic",        "type": "Cocktail", "price_min": 8.0,  "price_max": 12.0, "price_krash": 6.0, "tva": 8.5},
    {"name": "Cocktail Premium",        "type": "Cocktail", "price_min": 10.0, "price_max": 16.0, "price_krash": 8.0, "tva": 8.5},
    {"name": "L'Aventure",              "type": "Cocktail", "price_min": 10.0, "price_max": 16.0, "price_krash": 8.0, "tva": 8.5},
    {"name": "Mocktail ( sans alcool )", "type": "Cocktail", "price_min": 6.0,  "price_max": 10.0, "price_krash": 4.0, "tva": 2.1},

    # Alcool Fort
    {"name": "Alcool Classic",        "type": "Alcool Fort", "price_min": 7.0,  "price_max": 11.0,  "price_krash": 5.0,  "tva": 8.5},
    {"name": "Alcool Premium",        "type": "Alcool Fort", "price_min": 8.0,  "price_max": 14.0,  "price_krash": 7.0,  "tva": 8.5},
    {"name": "Bouteil Alcool Classic","type": "Alcool Fort", "price_min": 70.0, "price_max": 110.0, "price_krash": 60.0, "tva": 8.5},

    # Autres
    {"name": "Bouteille de vin", "type": "Autres", "price_min": 15.0, "price_max": 25.0, "price_krash": 13.0, "tva": 8.5},
    {"name": "Shots",            "type": "Autres", "price_min": 3.5,  "price_max": 6.0,  "price_krash": 2.5,  "tva": 8.5},
    {"name": "Verre de vin",     "type": "Autres", "price_min": 4.0,  "price_max": 6.0,  "price_krash": 3.0,  "tva": 8.5},
]
