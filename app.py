import eventlet
eventlet.monkey_patch()

import os
import uuid
import functools
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from database import (
    init_db, get_all_drinks, get_drinks_by_type, get_drink_by_id,
    add_drink, update_drink, delete_drink, record_sale,
    get_sales_today, get_sales_summary, get_price_history,
    get_drink_types_with_icons, create_ticket, get_setting, set_setting
)
from price_engine import PriceEngine
from config import PRICE_UPDATE_INTERVAL, KRASH_DURATION

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize price engine
price_engine = None

# ==================== AUTH ====================

def login_required(f):
    """Decorator — redirects to /login if not authenticated."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            # API routes get a 401 instead of a redirect
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Non authentifié'}), 401
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    """PIN login page"""
    if session.get('authenticated'):
        return redirect(url_for('caisse'))
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        stored_pin = get_setting('access_pin', '1234')
        if pin == stored_pin:
            session['authenticated'] = True
            next_url = request.args.get('next') or url_for('caisse')
            return redirect(next_url)
        error = 'Code PIN incorrect'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Clear session and redirect to login"""
    session.clear()
    return redirect(url_for('login'))

# ==================== PAGES ====================

@app.route('/')
def index():
    """Redirect to wall"""
    return render_template('wall.html')

@app.route('/wall')
def wall():
    """Public display - The Wall"""
    return render_template('wall.html')

@app.route('/caisse')
@login_required
def caisse():
    """Staff interface - Point of sale"""
    return render_template('caisse.html')

@app.route('/admin')
@login_required
def admin():
    """Admin backoffice"""
    return render_template('admin.html')

# ==================== API ====================

@app.route('/api/drinks')
def api_get_drinks():
    """Get all drinks"""
    drinks = get_drinks_by_type()
    return jsonify(drinks)

@app.route('/api/drinks/<int:drink_id>')
def api_get_drink(drink_id):
    """Get a single drink"""
    drink = get_drink_by_id(drink_id)
    if drink:
        return jsonify(drink)
    return jsonify({'error': 'Drink not found'}), 404

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
LOGOS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'logos')

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/drinks/upload-logo', methods=['POST'])
@login_required
def api_upload_logo():
    """Upload a drink logo image"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    f = request.files['file']
    if not f.filename or not _allowed_file(f.filename):
        return jsonify({'error': 'Format non supporté (png, jpg, gif, webp, svg)'}), 400
    ext = f.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    os.makedirs(LOGOS_FOLDER, exist_ok=True)
    f.save(os.path.join(LOGOS_FOLDER, filename))
    return jsonify({'url': f'/static/images/logos/{filename}'})

@app.route('/api/drinks', methods=['POST'])
@login_required
def api_add_drink():
    """Add a new drink"""
    data = request.json
    try:
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Le nom est requis'}), 400

        price_min = float(data['price_min'])
        price_max = float(data['price_max'])
        price_krash = float(data['price_krash'])
        tva = float(data.get('tva', 20.0))
        icon = data.get('icon') or None

        if price_min <= 0 or price_max <= 0 or price_krash <= 0:
            return jsonify({'error': 'Les prix doivent être supérieurs à 0'}), 400
        if price_min > price_max:
            return jsonify({'error': 'Le prix min doit être inférieur au prix max'}), 400
        if price_krash > price_min:
            return jsonify({'error': 'Le prix krash doit être inférieur ou égal au prix min'}), 400

        drink_id = add_drink(
            name=name,
            drink_type=data['type'],
            price_min=price_min,
            price_max=price_max,
            price_krash=price_krash,
            tva=tva,
            icon=icon
        )
        return jsonify({'id': drink_id, 'success': True})
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/drinks/<int:drink_id>', methods=['PUT'])
@login_required
def api_update_drink(drink_id):
    """Update a drink"""
    data = request.json
    try:
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Le nom est requis'}), 400

        price_min = float(data['price_min'])
        price_max = float(data['price_max'])
        price_krash = float(data['price_krash'])
        tva = float(data.get('tva', 20.0))
        icon = data.get('icon') or None

        if price_min <= 0 or price_max <= 0 or price_krash <= 0:
            return jsonify({'error': 'Les prix doivent être supérieurs à 0'}), 400
        if price_min > price_max:
            return jsonify({'error': 'Le prix min doit être inférieur au prix max'}), 400
        if price_krash > price_min:
            return jsonify({'error': 'Le prix krash doit être inférieur ou égal au prix min'}), 400

        update_drink(
            drink_id=drink_id,
            name=name,
            drink_type=data['type'],
            price_min=price_min,
            price_max=price_max,
            price_krash=price_krash,
            tva=tva,
            icon=icon
        )
        return jsonify({'success': True})
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/drinks/<int:drink_id>', methods=['DELETE'])
@login_required
def api_delete_drink(drink_id):
    """Delete a drink"""
    try:
        delete_drink(drink_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/sale', methods=['POST'])
@login_required
def api_record_sale():
    """Record a sale"""
    data = request.json
    try:
        price = float(data['price'])
        quantity = int(data.get('quantity', 1))
        if price <= 0:
            return jsonify({'error': 'Le prix doit être supérieur à 0'}), 400
        if quantity <= 0:
            return jsonify({'error': 'La quantité doit être supérieure à 0'}), 400

        sale_id = record_sale(
            drink_id=data['drink_id'],
            drink_name=data['drink_name'],
            price=price,
            quantity=quantity
        )
        
        # Emit sale event
        socketio.emit('sale_recorded', {
            'drink_name': data['drink_name'],
            'price': data['price'],
            'quantity': data.get('quantity', 1)
        })
        
        return jsonify({'id': sale_id, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/sales')
@login_required
def api_get_sales():
    """Get today's sales"""
    from database import get_sales_by_drink_today, get_sales_by_payment_method_today, get_tva_breakdown_today
    sales = get_sales_today()
    summary = get_sales_summary()
    breakdown = get_sales_by_drink_today()
    payment_stats = get_sales_by_payment_method_today()
    tva_breakdown = get_tva_breakdown_today()
    return jsonify({
        'sales': sales,
        'summary': summary,
        'breakdown': breakdown,
        'payment_stats': payment_stats,
        'tva_breakdown': tva_breakdown
    })

@app.route('/api/sessions/close', methods=['POST'])
@login_required
def api_close_session():
    """Close the current session (Z-report)"""
    from database import get_sales_by_payment_method_today, close_session
    import json
    
    payment_stats = get_sales_by_payment_method_today()
    
    if payment_stats['grand_total']['tickets'] == 0:
        return jsonify({'error': 'Aucune vente dans la session courante'}), 400
        
    session_id = close_session(json.dumps(payment_stats))
    
    if session_id:
        return jsonify({'success': True, 'session_id': session_id})
    else:
        return jsonify({'error': 'Impossible de clôturer la session'}), 500

@app.route('/api/sessions')
@login_required
def api_get_sessions():
    """Get historical sessions"""
    from database import get_past_sessions
    sessions = get_past_sessions()
    return jsonify(sessions)

@app.route('/api/history/<int:drink_id>')
def api_get_history(drink_id):
    """Get price history for a drink"""
    limit = request.args.get('limit', 10, type=int)
    history = get_price_history(drink_id, limit)
    return jsonify(history)

@app.route('/api/types')
def api_get_types():
    """Get drink types with icons"""
    types = get_drink_types_with_icons()
    return jsonify(types)

@app.route('/api/ticket', methods=['POST'])
@login_required
def api_create_ticket():
    """Create a ticket with multiple items and payment method"""
    data = request.json
    try:
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'Espèces')
        total = round(sum(item['price'] * item['quantity'] for item in items), 2)
        
        # Create ticket
        ticket_id = create_ticket(total, payment_method)
        
        # Record each sale
        for item in items:
            record_sale(
                drink_id=item['drink_id'],
                drink_name=item['drink_name'],
                price=float(item['price']),
                quantity=int(item['quantity']),
                ticket_id=ticket_id
            )
        
        # Emit sale event
        socketio.emit('sale_recorded', {
            'ticket_id': ticket_id,
            'total': total,
            'payment_method': payment_method,
            'items_count': len(items)
        })
        
        return jsonify({'id': ticket_id, 'total': total, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/status')
def api_get_status():
    """Get current engine status"""
    global price_engine
    if price_engine:
        return jsonify(price_engine.get_status())
    return jsonify({'timer': PRICE_UPDATE_INTERVAL, 'krash_active': False})

@app.route('/api/krash', methods=['POST'])
@login_required
def api_trigger_krash():
    """Trigger KRASH mode"""
    global price_engine
    data = request.json or {}
    duration = int(data.get('duration', KRASH_DURATION))
    if duration <= 0 or duration > 3600:
        return jsonify({'error': 'La durée doit être entre 1 et 3600 secondes'}), 400

    if price_engine:
        price_engine.trigger_krash(duration)
        return jsonify({'success': True, 'duration': duration})
    return jsonify({'error': 'Price engine not running'}), 500

@app.route('/api/krash', methods=['DELETE'])
@login_required
def api_stop_krash():
    """Stop KRASH mode"""
    global price_engine
    if price_engine:
        price_engine.stop_krash()
        return jsonify({'success': True})
    return jsonify({'error': 'Price engine not running'}), 500

@app.route('/api/engine/start', methods=['POST'])
@login_required
def api_engine_start():
    """Manually start or restart the price engine"""
    global price_engine
    if price_engine.running:
        price_engine.stop()
    price_engine.start()
    return jsonify({'success': True, 'status': price_engine.get_status()})

@app.route('/api/settings/pin', methods=['PUT'])
@login_required
def api_change_pin():
    """Change the access PIN"""
    data = request.json or {}
    current = data.get('current_pin', '').strip()
    new_pin = data.get('new_pin', '').strip()

    stored_pin = get_setting('access_pin', '1234')
    if current != stored_pin:
        return jsonify({'error': 'Code PIN actuel incorrect'}), 403
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 8:
        return jsonify({'error': 'Le PIN doit être composé de 4 à 8 chiffres'}), 400

    set_setting('access_pin', new_pin)
    return jsonify({'success': True})

# ==================== WEBSOCKET ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection — start engine lazily (survives gunicorn fork)"""
    global price_engine
    if price_engine and not price_engine.running:
        price_engine.start()
    # Send current status
    if price_engine:
        emit('status', price_engine.get_status())
    # Send current prices
    drinks = get_drinks_by_type()
    emit('prices_update', {
        'event': 'initial',
        'drinks': drinks
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass

@socketio.on('request_prices')
def handle_request_prices():
    """Handle price request"""
    drinks = get_drinks_by_type()
    emit('prices_update', {
        'event': 'refresh',
        'drinks': drinks
    })

# ==================== INIT ====================

# Init DB and create engine at import time — start() appelé au premier connect
init_db()
price_engine = PriceEngine(socketio)

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("BAR TRADERS - Stock Exchange")
    print("="*50)
    print("\nWall (Ecran Public):  http://localhost:5000/wall")
    print("Caisse (Staff):       http://localhost:5000/caisse")
    print("Admin (Backoffice):   http://localhost:5000/admin")
    print("\n" + "="*50 + "\n")
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
