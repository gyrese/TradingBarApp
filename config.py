# Bar Traders Configuration

# Price update interval in seconds
PRICE_UPDATE_INTERVAL = 90

# Krash duration in seconds (5 minutes by default)
KRASH_DURATION = 300

# Database file — chemin absolu pour éviter les ambiguïtés selon le CWD de lancement
import os as _os
DATABASE_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'bar_traders.db')

# Default drinks data
DEFAULT_DRINKS = [
    # Bières
    {"name": "Heineken", "type": "Bière", "price_min": 2.50, "price_max": 5.00, "price_krash": 1.50, "tva": 20.0},
    {"name": "Corona", "type": "Bière", "price_min": 3.00, "price_max": 6.00, "price_krash": 2.00, "tva": 20.0},
    {"name": "Leffe Blonde", "type": "Bière", "price_min": 3.50, "price_max": 7.00, "price_krash": 2.50, "tva": 20.0},
    {"name": "Desperados", "type": "Bière", "price_min": 3.00, "price_max": 6.50, "price_krash": 2.00, "tva": 20.0},
    {"name": "Guinness", "type": "Bière", "price_min": 4.00, "price_max": 8.00, "price_krash": 2.50, "tva": 20.0},
    {"name": "1664", "type": "Bière", "price_min": 2.50, "price_max": 5.50, "price_krash": 1.50, "tva": 20.0},
    
    # Softs
    {"name": "Coca-Cola", "type": "Soft", "price_min": 2.00, "price_max": 4.00, "price_krash": 1.00, "tva": 5.5},
    {"name": "Orangina", "type": "Soft", "price_min": 2.00, "price_max": 4.00, "price_krash": 1.00, "tva": 5.5},
    {"name": "Perrier", "type": "Soft", "price_min": 1.50, "price_max": 3.50, "price_krash": 1.00, "tva": 5.5},
    {"name": "Red Bull", "type": "Soft", "price_min": 3.00, "price_max": 6.00, "price_krash": 2.00, "tva": 5.5},
    {"name": "Ice Tea", "type": "Soft", "price_min": 2.00, "price_max": 4.00, "price_krash": 1.00, "tva": 5.5},
    
    # Cocktails
    {"name": "Mojito", "type": "Cocktail", "price_min": 6.00, "price_max": 12.00, "price_krash": 4.00, "tva": 20.0},
    {"name": "Piña Colada", "type": "Cocktail", "price_min": 7.00, "price_max": 14.00, "price_krash": 5.00, "tva": 20.0},
    {"name": "Margarita", "type": "Cocktail", "price_min": 6.50, "price_max": 13.00, "price_krash": 4.50, "tva": 20.0},
    {"name": "Sex on Beach", "type": "Cocktail", "price_min": 7.00, "price_max": 14.00, "price_krash": 5.00, "tva": 20.0},
    {"name": "Cuba Libre", "type": "Cocktail", "price_min": 5.50, "price_max": 11.00, "price_krash": 4.00, "tva": 20.0},
    {"name": "Tequila Sunrise", "type": "Cocktail", "price_min": 6.00, "price_max": 12.00, "price_krash": 4.00, "tva": 20.0},
    {"name": "Long Island", "type": "Cocktail", "price_min": 8.00, "price_max": 16.00, "price_krash": 6.00, "tva": 20.0},
]
