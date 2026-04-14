import sqlite3
from datetime import datetime
from config import DATABASE_FILE, DEFAULT_DRINKS, DEFAULT_DRINK_TYPES
import random

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Table Boissons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            price_min REAL NOT NULL,
            price_max REAL NOT NULL,
            price_krash REAL NOT NULL,
            price_current REAL NOT NULL,
            price_previous REAL DEFAULT NULL,
            tva REAL NOT NULL DEFAULT 20.0,
            active INTEGER DEFAULT 1,
            icon TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Add icon column to existing databases
    try:
        cursor.execute('ALTER TABLE drinks ADD COLUMN icon TEXT DEFAULT NULL')
    except sqlite3.OperationalError:
        pass
    # Add display_order column to existing databases
    try:
        cursor.execute('ALTER TABLE drinks ADD COLUMN display_order INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    # Table Ventes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drink_id INTEGER NOT NULL,
            drink_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER DEFAULT 1,
            total REAL NOT NULL,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (drink_id) REFERENCES drinks (id)
        )
    ''')
    
    # Table Historique des prix
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drink_id INTEGER NOT NULL,
            price REAL NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (drink_id) REFERENCES drinks (id)
        )
    ''')
    
    # Table Tickets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Update sales table to include ticket_id if not exists
    try:
        cursor.execute('ALTER TABLE sales ADD COLUMN ticket_id INTEGER DEFAULT NULL REFERENCES tickets(id)')
    except sqlite3.OperationalError:
        pass # Column likely exists
        
    # Table Sessions (Z-reports)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_revenue REAL NOT NULL,
            total_tickets INTEGER NOT NULL,
            breakdown_json TEXT
        )
    ''')
    
    # Update sales and tickets to support sessions
    try:
        cursor.execute('ALTER TABLE sales ADD COLUMN session_id INTEGER DEFAULT NULL REFERENCES sessions(id)')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE tickets ADD COLUMN session_id INTEGER DEFAULT NULL REFERENCES sessions(id)')
    except sqlite3.OperationalError:
        pass
    
    # Table Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Default settings
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                  ('price_update_interval', '90'))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                  ('access_pin', '1234'))
    
    # Table Types de boissons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drink_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '🍷',
            display_order INTEGER DEFAULT 99,
            active INTEGER DEFAULT 1
        )
    ''')
    
    # Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_drink_id ON sales(drink_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_sold_at ON sales(sold_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_session_id ON sales(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_drink_id ON price_history(drink_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history(recorded_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_session_id ON tickets(session_id)')

    conn.commit()

    # Purge old price history (keep last 7 days)
    cursor.execute("DELETE FROM price_history WHERE recorded_at < datetime('now', '-7 days')")
    conn.commit()

    # Insert default types if none exist
    cursor.execute('SELECT COUNT(*) FROM drink_types')
    if cursor.fetchone()[0] == 0:
        for name, icon, order in DEFAULT_DRINK_TYPES:
            cursor.execute('INSERT INTO drink_types (name, icon, display_order) VALUES (?, ?, ?)',
                          (name, icon, order))
        conn.commit()
    else:
        # Migrate old/plural type names to canonical singular names
        _renames = [
            ('Bière',       'Bière'),   # no-op guard
            ('Bières',      'Bière'),
            ('Soft',        'Soft'),
            ('Softs',       'Soft'),
            ('Cocktail',    'Cocktail'),
            ('Cocktails',   'Cocktail'),
            ('Alcool Fort', 'Alcool'),
            ('Alcools',     'Alcool'),
            ('Vins',        'Vin'),
            ('Shoots',      'Shoot'),
        ]
        for old, new in _renames:
            if old != new:
                cursor.execute('UPDATE drink_types SET name=? WHERE name=?', (new, old))
                cursor.execute('UPDATE drinks SET type=? WHERE type=?', (new, old))
        # Distribute "Autres" drinks → proper types, then deactivate it
        cursor.execute("UPDATE drinks SET type='Vin'    WHERE type='Autres' AND LOWER(name) LIKE '%vin%'")
        cursor.execute("UPDATE drinks SET type='Shoot'  WHERE type='Autres' AND LOWER(name) LIKE '%shot%'")
        cursor.execute("UPDATE drinks SET type='Alcool' WHERE type='Autres'")
        cursor.execute("UPDATE drink_types SET active=0 WHERE name='Autres'")
        # Ensure Vin and Shoot types exist
        for name, icon, order in [('Vin', '🍷', 5), ('Shoot', '🥂', 6)]:
            cursor.execute(
                'INSERT OR IGNORE INTO drink_types (name, icon, display_order) VALUES (?, ?, ?)',
                (name, icon, order)
            )
            cursor.execute('UPDATE drink_types SET active=1 WHERE name=?', (name,))
        conn.commit()
    
    # Check if drinks exist
    cursor.execute('SELECT COUNT(*) FROM drinks')
    if cursor.fetchone()[0] == 0:
        # Insert default drinks
        for drink in DEFAULT_DRINKS:
            # Round to nearest 0.10€
            initial_price = round(random.uniform(drink['price_min'], drink['price_max']) * 10) / 10
            cursor.execute('''
                INSERT INTO drinks (name, type, price_min, price_max, price_krash, price_current, tva)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (drink['name'], drink['type'], drink['price_min'], drink['price_max'], 
                  drink['price_krash'], initial_price, drink['tva']))
        conn.commit()
    
    conn.close()

def get_all_drinks():
    """Get all active drinks"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM drinks WHERE active = 1 ORDER BY display_order, name')
    drinks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return drinks

def get_drinks_by_type():
    """Get drinks grouped by type"""
    drinks = get_all_drinks()
    grouped = {}
    for drink in drinks:
        drink_type = drink['type']
        if drink_type not in grouped:
            grouped[drink_type] = []
        grouped[drink_type].append(drink)
    return grouped

def get_drink_by_id(drink_id):
    """Get a single drink by ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM drinks WHERE id = ?', (drink_id,))
    drink = cursor.fetchone()
    conn.close()
    return dict(drink) if drink else None

def update_drink_price(drink_id, new_price, old_price=None):
    """Update drink price and store in history"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE drinks SET price_current = ?, price_previous = ? WHERE id = ?
    ''', (new_price, old_price, drink_id))
    
    # Record in history
    cursor.execute('''
        INSERT INTO price_history (drink_id, price) VALUES (?, ?)
    ''', (drink_id, new_price))
    
    conn.commit()
    conn.close()

def update_all_prices(krash_mode=False):
    """Update all drink prices randomly or to krash prices (atomic transaction)"""
    conn = get_db()
    cursor = conn.cursor()

    updated_drinks = []

    try:
        cursor.execute('BEGIN IMMEDIATE')

        cursor.execute('SELECT * FROM drinks WHERE active = 1 ORDER BY display_order, name')
        drinks = cursor.fetchall()

        for drink in drinks:
            old_price = drink['price_current']

            if krash_mode:
                new_price = drink['price_krash']
            else:
                new_price = round(random.uniform(drink['price_min'], drink['price_max']) * 10) / 10

            cursor.execute('''
                UPDATE drinks SET price_current = ?, price_previous = ? WHERE id = ?
            ''', (new_price, old_price, drink['id']))

            cursor.execute('''
                INSERT INTO price_history (drink_id, price) VALUES (?, ?)
            ''', (drink['id'], new_price))

            updated_drinks.append({
                'id': drink['id'],
                'name': drink['name'],
                'type': drink['type'],
                'icon': drink['icon'],
                'price_current': new_price,
                'price_previous': old_price,
                'price_min': drink['price_min'],
                'price_max': drink['price_max'],
                'price_krash': drink['price_krash'],
                'tva': drink['tva']
            })

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return updated_drinks

def add_drink(name, drink_type, price_min, price_max, price_krash, tva=20.0, icon=None):
    """Add a new drink"""
    conn = get_db()
    cursor = conn.cursor()

    # Round to nearest 0.10€
    initial_price = round(random.uniform(price_min, price_max) * 10) / 10

    cursor.execute('''
        INSERT INTO drinks (name, type, price_min, price_max, price_krash, price_current, tva, icon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, drink_type, price_min, price_max, price_krash, initial_price, tva, icon))

    drink_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return drink_id

def update_drink(drink_id, name, drink_type, price_min, price_max, price_krash, tva, icon=None):
    """Update drink details"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE drinks SET name = ?, type = ?, price_min = ?, price_max = ?, price_krash = ?, tva = ?, icon = ?
        WHERE id = ?
    ''', (name, drink_type, price_min, price_max, price_krash, tva, icon, drink_id))

    conn.commit()
    conn.close()

def delete_drink(drink_id):
    """Soft delete a drink"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE drinks SET active = 0 WHERE id = ?', (drink_id,))
    conn.commit()
    conn.close()

def create_ticket(total, payment_method):
    """Create a new ticket transaction"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO tickets (total, payment_method) VALUES (?, ?)',
                  (total, payment_method))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def record_sale(drink_id, drink_name, price, quantity=1, ticket_id=None):
    """Record a sale"""
    conn = get_db()
    cursor = conn.cursor()
    
    total = round(price * quantity, 2)
    
    cursor.execute('''
        INSERT INTO sales (drink_id, drink_name, price, quantity, total, ticket_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (drink_id, drink_name, price, quantity, total, ticket_id))
    
    sale_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return sale_id

def get_sales_today():
    """Get today's sales"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM sales WHERE session_id IS NULL ORDER BY sold_at DESC
    ''')
    
    sales = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return sales

def get_sales_summary():
    """Get sales summary for today"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as count, SUM(total) as total FROM sales WHERE session_id IS NULL
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    return {
        'count': result['count'] or 0,
        'total': round(result['total'] or 0, 2)
    }

def get_sales_by_drink_today():
    """Get sales aggregated by drink for today"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            drink_id, 
            drink_name, 
            SUM(quantity) as total_quantity, 
            SUM(total) as total_revenue
        FROM sales 
        WHERE session_id IS NULL 
        GROUP BY drink_id, drink_name
        ORDER BY total_revenue DESC
    ''')
    
    breakdown = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return breakdown

def get_sales_by_payment_method_today():
    """Get sales summarized by payment method for today"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT payment_method, COUNT(id) as tickets, SUM(total) as revenue
        FROM tickets
        WHERE session_id IS NULL
        GROUP BY payment_method
    ''')
    
    methods = {row['payment_method']: {'tickets': row['tickets'], 'revenue': row['revenue'], 'articles': 0, 'drink_breakdown': []} 
               for row in cursor.fetchall()}
               
    cursor.execute('''
        SELECT t.payment_method, SUM(s.quantity) as articles
        FROM sales s
        JOIN tickets t ON s.ticket_id = t.id
        WHERE s.session_id IS NULL
        GROUP BY t.payment_method
    ''')
    
    for row in cursor.fetchall():
        method = row['payment_method']
        if method in methods:
            methods[method]['articles'] = row['articles']
            
    # Get breakdown of drinks per payment method
    cursor.execute('''
        SELECT t.payment_method, s.drink_name, SUM(s.quantity) as total_quantity, SUM(s.total) as total_revenue
        FROM sales s
        JOIN tickets t ON s.ticket_id = t.id
        WHERE s.session_id IS NULL
        GROUP BY t.payment_method, s.drink_id, s.drink_name
        ORDER BY t.payment_method, total_revenue DESC
    ''')
    
    for row in cursor.fetchall():
        method = row['payment_method']
        if method in methods:
            methods[method]['drink_breakdown'].append({
                'drink_name': row['drink_name'],
                'total_quantity': row['total_quantity'],
                'total_revenue': row['total_revenue']
            })
            
    conn.close()
    
    # Also calculate a grand total to easily pass it
    grand_total_revenue = sum(m['revenue'] for m in methods.values())
    grand_total_tickets = sum(m['tickets'] for m in methods.values())
    grand_total_articles = sum(m['articles'] for m in methods.values())
    
    return {
        'methods': [{'payment_method': k, **v} for k, v in methods.items()],
        'grand_total': {'revenue': grand_total_revenue, 'tickets': grand_total_tickets, 'articles': grand_total_articles}
    }

def get_tva_breakdown_today():
    """Get TVA breakdown for today's sales (current session)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            d.tva as tva_rate,
            SUM(s.total) as total_ttc
        FROM sales s
        JOIN drinks d ON s.drink_id = d.id
        WHERE s.session_id IS NULL
        GROUP BY d.tva
        ORDER BY d.tva
    ''')

    rows = cursor.fetchall()
    conn.close()

    breakdown = []
    total_ht = 0
    total_tva = 0
    total_ttc = 0

    for row in rows:
        rate = row['tva_rate']
        ttc = row['total_ttc']
        ht = ttc / (1 + rate / 100)
        tva = ttc - ht
        breakdown.append({
            'tva_rate': rate,
            'total_ttc': round(ttc, 2),
            'total_ht': round(ht, 2),
            'total_tva': round(tva, 2)
        })
        total_ht += ht
        total_tva += tva
        total_ttc += ttc

    return {
        'breakdown': breakdown,
        'totals': {
            'total_ht': round(total_ht, 2),
            'total_tva': round(total_tva, 2),
            'total_ttc': round(total_ttc, 2)
        }
    }

def close_session(payment_stats_json):
    """Close the current session, archiving the Z-report data (atomic transaction)"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN IMMEDIATE')

        cursor.execute('SELECT COUNT(*) as t_count, SUM(total) as t_revenue FROM tickets WHERE session_id IS NULL')
        res = cursor.fetchone()
        total_revenue = res['t_revenue'] or 0
        total_tickets = res['t_count'] or 0

        if total_revenue == 0 and total_tickets == 0:
            conn.close()
            return None

        cursor.execute('''
            INSERT INTO sessions (total_revenue, total_tickets, breakdown_json) VALUES (?, ?, ?)
        ''', (total_revenue, total_tickets, payment_stats_json))

        session_id = cursor.lastrowid

        cursor.execute('UPDATE sales SET session_id = ? WHERE session_id IS NULL', (session_id,))
        cursor.execute('UPDATE tickets SET session_id = ? WHERE session_id IS NULL', (session_id,))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return session_id

def get_past_sessions():
    """Get historical Z reports"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions ORDER BY closed_at DESC')
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

def get_price_history(drink_id, limit=10):
    """Get price history for a drink"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT price, recorded_at FROM price_history 
        WHERE drink_id = ? 
        ORDER BY recorded_at DESC 
        LIMIT ?
    ''', (drink_id, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return history

def get_setting(key, default=None):
    """Get a setting value"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result['value'] if result else default

def set_setting(key, value):
    """Set a setting value"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
    ''', (key, str(value)))
    conn.commit()
    conn.close()

# ==================== DRINK TYPES ====================

def get_all_drink_types():
    """Get all active drink types"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM drink_types WHERE active = 1 ORDER BY display_order, name')
    types = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return types

def get_drink_type_names():
    """Get list of drink type names"""
    types = get_all_drink_types()
    return [t['name'] for t in types]

def add_drink_type(name, icon='🍷', display_order=99):
    """Add a new drink type"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO drink_types (name, icon, display_order) VALUES (?, ?, ?)
        ''', (name, icon, display_order))
        type_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return type_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def update_drink_type(type_id, name, icon, display_order):
    """Update drink type"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE drink_types SET name = ?, icon = ?, display_order = ? WHERE id = ?
    ''', (name, icon, display_order, type_id))
    conn.commit()
    conn.close()

def update_drinks_order(order_list):
    """Update display_order for a list of drinks. order_list = [{'id': int, 'order': int}, ...]"""
    conn = get_db()
    cursor = conn.cursor()
    for item in order_list:
        cursor.execute('UPDATE drinks SET display_order = ? WHERE id = ?', (item['order'], item['id']))
    conn.commit()
    conn.close()

def delete_drink_type(type_id):
    """Soft delete a drink type"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE drink_types SET active = 0 WHERE id = ?', (type_id,))
    conn.commit()
    conn.close()

def get_drink_types_with_icons():
    """Get drink types as dict with icons"""
    types = get_all_drink_types()
    return {t['name']: {'icon': t['icon'], 'order': t['display_order']} for t in types}
