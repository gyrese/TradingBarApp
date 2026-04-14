"""
Bar Traders - Application Caisse/Admin
Application Python de bureau pour gérer les prix, sessions et KRASH
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import webbrowser
from datetime import datetime, timedelta
import json

from database import (
    init_db, get_all_drinks, get_drinks_by_type, get_drink_by_id,
    add_drink, update_drink, delete_drink, update_all_prices,
    record_sale, get_sales_today, get_sales_summary, set_setting, get_setting,
    get_all_drink_types, get_drink_type_names, add_drink_type, update_drink_type, 
    delete_drink_type, get_drink_types_with_icons,
    create_ticket
)
from config import PRICE_UPDATE_INTERVAL, KRASH_DURATION

# Flask server for Wall display
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

# ==================== FLASK SERVER (for Wall) ====================

flask_app = Flask(__name__)
import os
flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
socketio = SocketIO(flask_app, cors_allowed_origins="*", async_mode='threading')

@flask_app.route('/')
@flask_app.route('/wall')
def wall():
    return render_template('wall.html')

@flask_app.route('/api/drinks')
def api_get_drinks():
    drinks = get_drinks_by_type()
    return jsonify(drinks)

@flask_app.route('/api/drinks/count')
def api_get_drinks_count():
    drinks = get_all_drinks()
    return jsonify({'count': len(drinks)})

@flask_app.route('/api/history/<int:drink_id>')
def api_get_history(drink_id):
    from database import get_price_history
    limit = request.args.get('limit', 10, type=int)
    history = get_price_history(drink_id, limit)
    return jsonify(history)

@flask_app.route('/api/types')
def api_get_types():
    """Get drink types with icons"""
    types = get_drink_types_with_icons()
    return jsonify(types)

@socketio.on('connect')
def handle_connect():
    drinks = get_drinks_by_type()
    socketio.emit('prices_update', {
        'event': 'initial',
        'drinks': drinks
    })

# ==================== MAIN APPLICATION ====================

class BarTradersApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🍺 Bar Traders - Caisse & Admin")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0e17')
        
        # State
        self.session_active = False
        self.krash_active = False
        self.krash_end_time = None
        self.timer = PRICE_UPDATE_INTERVAL
        self.timer_thread = None
        self.flask_thread = None
        self.caisse_window = None # Retain reference to POS window
        self.drinks = []
        
        # Style
        self.setup_style()
        
        # Initialize database
        init_db()
        
        # Build UI
        self.build_ui()
        
        # Load initial data
        self.refresh_drinks()
        
        # Start Flask server
        self.start_flask_server()
        
    def setup_style(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colors
        self.colors = {
            'bg': '#0a0e17',
            'card': '#12182a',
            'accent': '#4a9eff',
            'green': '#00ff88',
            'red': '#ff4757',
            'gold': '#ffd700',
            'text': '#ffffff',
            'text_muted': '#94a3b8'
        }
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 24, 'bold'), foreground=self.colors['gold'])
        style.configure('Timer.TLabel', font=('Consolas', 48, 'bold'), foreground=self.colors['green'])
        style.configure('TButton', font=('Segoe UI', 11, 'bold'), padding=10)
        
    def build_ui(self):
        """Build the main UI"""
        # Main container
        main = ttk.Frame(self.root, style='TFrame')
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.build_header(main)
        
        # Content area with two columns
        content = ttk.Frame(main, style='TFrame')
        content.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Left column - Session Control
        left = ttk.Frame(content, style='TFrame')
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.build_session_panel(left)
        self.build_krash_panel(left)
        self.build_sales_panel(left)
        
        # Right column - Drinks Management
        right = ttk.Frame(content, style='TFrame')
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.build_drinks_panel(right)
        
    def build_header(self, parent):
        """Build header with title and timer"""
        header = ttk.Frame(parent, style='TFrame')
        header.pack(fill=tk.X, pady=(0, 20))
        
        # Title
        title = ttk.Label(header, text="🍺📈 BAR TRADERS", style='Title.TLabel')
        title.pack(side=tk.LEFT)
        
        # Timer frame
        timer_frame = tk.Frame(header, bg=self.colors['card'], bd=2, relief='ridge')
        timer_frame.pack(side=tk.RIGHT)
        
        timer_inner = tk.Frame(timer_frame, bg=self.colors['card'], padx=20, pady=10)
        timer_inner.pack()
        
        self.timer_label = tk.Label(timer_inner, text="90", font=('Consolas', 36, 'bold'),
                                     fg=self.colors['green'], bg=self.colors['card'])
        self.timer_label.pack(side=tk.LEFT)
        
        tk.Label(timer_inner, text="s", font=('Consolas', 24), 
                 fg=self.colors['text_muted'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(5, 0))
        
        # Status
        self.status_label = tk.Label(header, text="⚫ Session inactive", font=('Segoe UI', 12),
                                      fg=self.colors['text_muted'], bg=self.colors['bg'])
        self.status_label.pack(side=tk.RIGHT, padx=20)
        
    def build_session_panel(self, parent):
        """Build session control panel"""
        frame = tk.Frame(parent, bg=self.colors['card'], bd=1, relief='solid')
        frame.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=20)
        inner.pack(fill=tk.X)
        
        tk.Label(inner, text="🎮 Contrôle Session", font=('Segoe UI', 14, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card']).pack(anchor='w')
        
        btn_frame = tk.Frame(inner, bg=self.colors['card'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.session_btn = tk.Button(btn_frame, text="▶ DÉMARRER SESSION", font=('Segoe UI', 14, 'bold'),
                                      bg=self.colors['green'], fg='black', padx=30, pady=15,
                                      command=self.toggle_session, cursor='hand2')
        self.session_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        
        wall_btn = tk.Button(btn_frame, text="🖥 Ouvrir Wall", font=('Segoe UI', 12),
                             bg=self.colors['accent'], fg='white', padx=20, pady=15,
                             command=self.open_wall, cursor='hand2')
        wall_btn.pack(side=tk.RIGHT)
        
        caisse_btn = tk.Button(btn_frame, text="🛒 Mode Caisse", font=('Segoe UI', 12),
                             bg='#0ea5e9', fg='white', padx=20, pady=15,
                             command=self.open_caisse_window, cursor='hand2')
        caisse_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
    def open_caisse_window(self):
        """Open optimized POS window"""
        CaisseWindow(self)
        
    def build_krash_panel(self, parent):
        """Build KRASH control panel"""
        frame = tk.Frame(parent, bg='#2a1a1a', bd=2, relief='solid', highlightbackground=self.colors['red'])
        frame.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(frame, bg='#2a1a1a', padx=20, pady=20)
        inner.pack(fill=tk.X)
        
        tk.Label(inner, text="⚠️ ZONE DANGER", font=('Segoe UI', 14, 'bold'),
                 fg=self.colors['red'], bg='#2a1a1a').pack(anchor='w')
        
        tk.Label(inner, text="Déclenche le KRASH: Tous les prix tombent au minimum!",
                 font=('Segoe UI', 10), fg=self.colors['text_muted'], bg='#2a1a1a').pack(anchor='w', pady=(5, 0))
        
        btn_frame = tk.Frame(inner, bg='#2a1a1a')
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.krash_btn = tk.Button(btn_frame, text="💥 KRASH !", font=('Segoe UI', 16, 'bold'),
                                    bg=self.colors['red'], fg='white', padx=40, pady=15,
                                    command=self.trigger_krash, cursor='hand2')
        self.krash_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.krash_timer_label = tk.Label(inner, text="", font=('Segoe UI', 12, 'bold'),
                                           fg=self.colors['gold'], bg='#2a1a1a')
        self.krash_timer_label.pack(pady=(10, 0))
        
    def build_sales_panel(self, parent):
        """Build sales summary panel"""
        frame = tk.Frame(parent, bg=self.colors['card'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=20)
        inner.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(inner, text="💰 Ventes du Jour", font=('Segoe UI', 14, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card']).pack(anchor='w')
        
        stats = tk.Frame(inner, bg=self.colors['card'])
        stats.pack(fill=tk.X, pady=15)
        
        # Sales count
        count_frame = tk.Frame(stats, bg=self.colors['bg'], padx=20, pady=15)
        count_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.sales_count_label = tk.Label(count_frame, text="0", font=('Consolas', 28, 'bold'),
                                           fg=self.colors['green'], bg=self.colors['bg'])
        self.sales_count_label.pack()
        tk.Label(count_frame, text="Ventes", font=('Segoe UI', 10),
                 fg=self.colors['text_muted'], bg=self.colors['bg']).pack()
        
        # Sales total
        total_frame = tk.Frame(stats, bg=self.colors['bg'], padx=20, pady=15)
        total_frame.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
        self.sales_total_label = tk.Label(total_frame, text="0.00€", font=('Consolas', 28, 'bold'),
                                           fg=self.colors['green'], bg=self.colors['bg'])
        self.sales_total_label.pack()
        tk.Label(total_frame, text="Total", font=('Segoe UI', 10),
                 fg=self.colors['text_muted'], bg=self.colors['bg']).pack()
        
        # Refresh sales
        self.refresh_sales()
        
    def build_drinks_panel(self, parent):
        """Build drinks management panel"""
        frame = tk.Frame(parent, bg=self.colors['card'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(frame, bg=self.colors['card'], padx=20, pady=20)
        inner.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(inner, bg=self.colors['card'])
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🍹 Gestion des Boissons", font=('Segoe UI', 14, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT)
        
        tk.Button(header, text="➕ Ajouter", font=('Segoe UI', 10),
                  bg=self.colors['accent'], fg='white', padx=15, pady=5,
                  command=self.add_drink_dialog, cursor='hand2').pack(side=tk.RIGHT)
        
        tk.Button(header, text="✏️ Modifier", font=('Segoe UI', 10),
                  bg=self.colors['gold'], fg='black', padx=15, pady=5,
                  command=self.edit_drink_dialog, cursor='hand2').pack(side=tk.RIGHT, padx=(0, 10))
        
        tk.Button(header, text="🗑️ Supprimer", font=('Segoe UI', 10),
                  bg=self.colors['red'], fg='white', padx=15, pady=5,
                  command=self.delete_drink, cursor='hand2').pack(side=tk.RIGHT, padx=(0, 10))
        
        tk.Button(header, text="📁 Types", font=('Segoe UI', 10),
                  bg='#6366f1', fg='white', padx=15, pady=5,
                  command=self.manage_types_dialog, cursor='hand2').pack(side=tk.RIGHT, padx=(0, 10))
        
        # Drinks table
        table_frame = tk.Frame(inner, bg=self.colors['bg'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        columns = ('name', 'type', 'min', 'max', 'krash', 'current')
        self.drinks_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                         yscrollcommand=scrollbar.set)
        
        self.drinks_tree.heading('name', text='Nom')
        self.drinks_tree.heading('type', text='Type')
        self.drinks_tree.heading('min', text='Min €')
        self.drinks_tree.heading('max', text='Max €')
        self.drinks_tree.heading('krash', text='Krash €')
        self.drinks_tree.heading('current', text='Actuel €')
        
        self.drinks_tree.column('name', width=150)
        self.drinks_tree.column('type', width=80)
        self.drinks_tree.column('min', width=60)
        self.drinks_tree.column('max', width=60)
        self.drinks_tree.column('krash', width=60)
        self.drinks_tree.column('current', width=80)
        
        self.drinks_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.drinks_tree.yview)
        
        # Context menu
        self.drinks_tree.bind('<Button-3>', self.show_drink_context_menu)
        self.drinks_tree.bind('<Double-1>', self.edit_drink_dialog)
        
    def refresh_drinks(self):
        """Refresh drinks list"""
        self.drinks = get_all_drinks()
        
        # Clear tree
        for item in self.drinks_tree.get_children():
            self.drinks_tree.delete(item)
        
        # Add drinks
        for drink in self.drinks:
            self.drinks_tree.insert('', 'end', iid=drink['id'], values=(
                drink['name'],
                drink['type'],
                f"{drink['price_min']:.2f}",
                f"{drink['price_max']:.2f}",
                f"{drink['price_krash']:.2f}",
                f"{drink['price_current']:.2f}"
            ))
            
    def refresh_sales(self):
        """Refresh sales summary"""
        summary = get_sales_summary()
        self.sales_count_label.config(text=str(summary['count']))
        self.sales_total_label.config(text=f"{summary['total']:.2f}€")
        
    def toggle_session(self):
        """Start/stop trading session"""
        if self.session_active:
            self.stop_session()
        else:
            self.start_session()
            
    def start_session(self):
        """Start trading session"""
        self.session_active = True
        self.timer = PRICE_UPDATE_INTERVAL
        
        self.session_btn.config(text="⏹ ARRÊTER SESSION", bg=self.colors['red'])
        self.status_label.config(text="🟢 Session active", fg=self.colors['green'])
        
        # Start timer thread
        self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.timer_thread.start()
        
        # Notify wall
        self.emit_status()
        
    def stop_session(self):
        """Stop trading session"""
        self.session_active = False
        self.krash_active = False
        
        self.session_btn.config(text="▶ DÉMARRER SESSION", bg=self.colors['green'])
        self.status_label.config(text="⚫ Session inactive", fg=self.colors['text_muted'])
        self.krash_timer_label.config(text="")
        self.krash_btn.config(text="💥 KRASH !", bg=self.colors['red'])
        
        # Notify wall
        socketio.emit('session_stopped', {})
        
    def timer_loop(self):
        """Main timer loop"""
        while self.session_active:
            time.sleep(1)
            
            # Check krash end
            if self.krash_active and self.krash_end_time:
                if datetime.now() >= self.krash_end_time:
                    self.end_krash()
            
            # Decrement timer
            self.timer -= 1
            
            # Update UI
            self.root.after(0, self.update_timer_ui)
            
            # Emit to wall
            socketio.emit('timer_update', {
                'timer': self.timer,
                'krash_active': self.krash_active,
                'krash_remaining': self.get_krash_remaining()
            })
            
            # Update prices when timer reaches 0
            if self.timer <= 0:
                if not self.krash_active:
                    self.update_prices()
                self.timer = PRICE_UPDATE_INTERVAL
                
    def update_timer_ui(self):
        """Update timer display in UI"""
        self.timer_label.config(text=str(self.timer))
        
        if self.timer <= 10:
            self.timer_label.config(fg=self.colors['red'])
        elif self.timer <= 20:
            self.timer_label.config(fg=self.colors['gold'])
        else:
            self.timer_label.config(fg=self.colors['green'])
            
        # Update krash timer
        if self.krash_active:
            remaining = self.get_krash_remaining()
            mins = remaining // 60
            secs = remaining % 60
            self.krash_timer_label.config(text=f"⏱ KRASH en cours: {mins}:{secs:02d}")
            
    def update_prices(self):
        """Update all drink prices"""
        drinks = update_all_prices(krash_mode=False)
        
        # Emit to wall
        grouped = {}
        for drink in drinks:
            t = drink['type']
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(drink)
            
        socketio.emit('prices_update', {
            'event': 'price_update',
            'drinks': grouped
        })
        
        # Refresh local display
        self.root.after(0, self.refresh_drinks)
        
        # Update Caisse Window if open
        if self.caisse_window:
            try:
                self.caisse_window.update_prices(grouped)
            except tk.TclError:
                self.caisse_window = None
        
    def trigger_krash(self):
        """Trigger KRASH mode"""
        if not self.session_active:
            messagebox.showwarning("Session inactive", "Démarrez d'abord une session!")
            return
            
        if self.krash_active:
            # Stop krash
            self.end_krash()
            return
        
        if messagebox.askyesno("Confirmer KRASH", "Déclencher le KRASH?\nTous les prix tombent au minimum pendant 5 minutes!"):
            self.krash_active = True
            self.krash_end_time = datetime.now() + timedelta(seconds=KRASH_DURATION)
            
            self.krash_btn.config(text="🛑 ARRÊTER KRASH", bg=self.colors['gold'])
            
            # Update prices to krash
            drinks = update_all_prices(krash_mode=True)
            
            grouped = {}
            for drink in drinks:
                t = drink['type']
                if t not in grouped:
                    grouped[t] = []
                grouped[t].append(drink)
                
            socketio.emit('prices_update', {
                'event': 'krash_started',
                'drinks': grouped
            })
            
            socketio.emit('krash', {
                'active': True,
                'duration': KRASH_DURATION
            })
            
            self.refresh_drinks()
            
    def end_krash(self):
        """End KRASH mode"""
        self.krash_active = False
        self.krash_end_time = None
        
        self.root.after(0, lambda: self.krash_btn.config(text="💥 KRASH !", bg=self.colors['red']))
        self.root.after(0, lambda: self.krash_timer_label.config(text=""))
        
        # Update prices to normal
        drinks = update_all_prices(krash_mode=False)
        
        grouped = {}
        for drink in drinks:
            t = drink['type']
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(drink)
            
        socketio.emit('prices_update', {
            'event': 'krash_ended',
            'drinks': grouped
        })
        
        socketio.emit('krash', {'active': False})
        
        self.root.after(0, self.refresh_drinks)
        
    def get_krash_remaining(self):
        """Get remaining krash time"""
        if not self.krash_active or not self.krash_end_time:
            return 0
        remaining = (self.krash_end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))
        
    def emit_status(self):
        """Emit current status to wall"""
        drinks = get_drinks_by_type()
        socketio.emit('prices_update', {
            'event': 'initial',
            'drinks': drinks
        })
        socketio.emit('timer_update', {
            'timer': self.timer,
            'krash_active': self.krash_active,
            'krash_remaining': self.get_krash_remaining()
        })
        
    def open_wall(self):
        """Open wall in browser"""
        webbrowser.open('http://localhost:5000/wall')
        
    def add_drink_dialog(self):
        """Show add drink dialog"""
        dialog = DrinkDialog(self.root, "Ajouter une Boisson", self.colors)
        if dialog.result:
            add_drink(**dialog.result)
            self.refresh_drinks()
            self.emit_status()
            
    def edit_drink_dialog(self, event=None):
        """Show edit drink dialog"""
        selection = self.drinks_tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une boisson à modifier")
            return
            
        drink_id = int(selection[0])
        drink = get_drink_by_id(drink_id)
        
        if drink:
            dialog = DrinkDialog(self.root, "Modifier la Boisson", self.colors, drink)
            if dialog.result:
                update_drink(drink_id, **dialog.result)
                self.refresh_drinks()
                self.emit_status()
                
    def show_drink_context_menu(self, event):
        """Show context menu for drinks"""
        selection = self.drinks_tree.selection()
        if not selection:
            return
            
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✏️ Modifier", command=self.edit_drink_dialog)
        menu.add_command(label="🗑️ Supprimer", command=self.delete_drink)
        menu.post(event.x_root, event.y_root)
        
    def delete_drink(self):
        """Delete selected drink"""
        selection = self.drinks_tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une boisson à supprimer")
            return
            
        drink_id = int(selection[0])
        drink = get_drink_by_id(drink_id)
        
        if drink and messagebox.askyesno("Confirmer la suppression", 
                                         f"Êtes-vous sûr de vouloir supprimer '{drink['name']}'?\n\nCette action est irréversible."):
            delete_drink(drink_id)
            self.refresh_drinks()
            self.emit_status()
            messagebox.showinfo("Succès", f"'{drink['name']}' a été supprimée.")
    
    def manage_types_dialog(self):
        """Show dialog to manage drink types"""
        dialog = TypesDialog(self.root, self.colors)
        if dialog.changed:
            self.refresh_drinks()
            self.emit_status()
            
    def start_flask_server(self):
        """Start Flask server in background thread"""
        def run_flask():
            socketio.run(flask_app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
            
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        print("Wall server started at http://localhost:5000/wall")


class DrinkDialog:
    """Dialog for adding/editing drinks"""
    
    def __init__(self, parent, title, colors, drink=None):
        self.result = None
        self.colors = colors
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x500")
        self.dialog.configure(bg=colors['card'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_x() + 350, parent.winfo_y() + 100))
        
        # Form
        form = tk.Frame(self.dialog, bg=colors['card'], padx=30, pady=25)
        form.pack(fill=tk.BOTH, expand=True)
        
        # Name
        tk.Label(form, text="Nom de la boisson", bg=colors['card'], fg=colors['text'], 
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.name_entry = tk.Entry(form, font=('Segoe UI', 12), width=35)
        self.name_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Type - Dynamic from database
        tk.Label(form, text="Type", bg=colors['card'], fg=colors['text'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        
        # Get types from database
        self.drink_types = get_drink_type_names()
        if not self.drink_types:
            self.drink_types = ["Bière", "Soft", "Cocktail"]
        
        self.type_var = tk.StringVar(value=self.drink_types[0] if self.drink_types else "Bière")
        type_frame = tk.Frame(form, bg=colors['card'])
        type_frame.pack(fill=tk.X, pady=(5, 15))
        
        # Use OptionMenu for dynamic types
        self.type_menu = ttk.Combobox(type_frame, textvariable=self.type_var, 
                                       values=self.drink_types, state='readonly',
                                       font=('Segoe UI', 11), width=20)
        self.type_menu.pack(side=tk.LEFT)
        
        # Prices section label
        tk.Label(form, text="Prix (en €)", bg=colors['card'], fg=colors['gold'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(10, 5))
        
        # Prices frame - row 1: Min and Max
        prices1 = tk.Frame(form, bg=colors['card'])
        prices1.pack(fill=tk.X, pady=(0, 10))
        
        # Min price
        min_frame = tk.Frame(prices1, bg=colors['card'])
        min_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        tk.Label(min_frame, text="Prix Min", bg=colors['card'], fg=colors['text']).pack(anchor='w')
        self.min_entry = tk.Entry(min_frame, font=('Segoe UI', 12), width=12)
        self.min_entry.pack(fill=tk.X, pady=3)
        
        # Max price
        max_frame = tk.Frame(prices1, bg=colors['card'])
        max_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10, 0))
        tk.Label(max_frame, text="Prix Max", bg=colors['card'], fg=colors['text']).pack(anchor='w')
        self.max_entry = tk.Entry(max_frame, font=('Segoe UI', 12), width=12)
        self.max_entry.pack(fill=tk.X, pady=3)
        
        # Prices frame - row 2: Krash and TVA
        prices2 = tk.Frame(form, bg=colors['card'])
        prices2.pack(fill=tk.X, pady=(0, 15))
        
        # Krash price
        krash_frame = tk.Frame(prices2, bg=colors['card'])
        krash_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        tk.Label(krash_frame, text="Prix Krash", bg=colors['card'], fg=colors['red']).pack(anchor='w')
        self.krash_entry = tk.Entry(krash_frame, font=('Segoe UI', 12), width=12)
        self.krash_entry.pack(fill=tk.X, pady=3)
        
        # TVA
        tva_frame = tk.Frame(prices2, bg=colors['card'])
        tva_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10, 0))
        tk.Label(tva_frame, text="TVA %", bg=colors['card'], fg=colors['text']).pack(anchor='w')
        self.tva_entry = tk.Entry(tva_frame, font=('Segoe UI', 12), width=12)
        self.tva_entry.insert(0, "20")
        self.tva_entry.pack(fill=tk.X, pady=3)
        
        # Spacer
        tk.Frame(form, bg=colors['card'], height=20).pack()
        
        # Buttons
        btn_frame = tk.Frame(form, bg=colors['card'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="Annuler", font=('Segoe UI', 11),
                  bg=colors['bg'], fg=colors['text'], padx=25, pady=10,
                  command=self.dialog.destroy).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                  bg=colors['accent'], fg='white', padx=25, pady=10,
                  command=self.save).pack(side=tk.RIGHT)
        
        # Fill if editing
        if drink:
            self.name_entry.insert(0, drink['name'])
            self.type_var.set(drink['type'])
            self.min_entry.insert(0, str(drink['price_min']))
            self.max_entry.insert(0, str(drink['price_max']))
            self.krash_entry.insert(0, str(drink['price_krash']))
            self.tva_entry.delete(0, tk.END)
            self.tva_entry.insert(0, str(drink['tva']))
        
        self.dialog.wait_window()
        
    def save(self):
        """Save drink data"""
        # Validate fields are not empty
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Erreur", "Veuillez entrer un nom de boisson")
            return
            
        try:
            price_min = float(self.min_entry.get().replace(',', '.'))
            price_max = float(self.max_entry.get().replace(',', '.'))
            price_krash = float(self.krash_entry.get().replace(',', '.'))
            tva = float(self.tva_entry.get().replace(',', '.'))
            
            # Validate prices
            if price_min <= 0 or price_max <= 0 or price_krash <= 0:
                messagebox.showerror("Erreur", "Les prix doivent être supérieurs à 0")
                return
                
            if price_min > price_max:
                messagebox.showerror("Erreur", "Le prix min doit être inférieur au prix max")
                return
                
            if price_krash > price_min:
                messagebox.showerror("Erreur", "Le prix krash doit être inférieur au prix min")
                return
            
            self.result = {
                'name': name,
                'drink_type': self.type_var.get(),
                'price_min': price_min,
                'price_max': price_max,
                'price_krash': price_krash,
                'tva': tva
            }
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides\n(utilisez . ou , pour les décimales)")


class TypesDialog:
    """Dialog for managing drink types"""
    
    def __init__(self, parent, colors):
        self.changed = False
        self.colors = colors
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gérer les Types de Boissons")
        self.dialog.geometry("500x400")
        self.dialog.configure(bg=colors['card'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_x() + 300, parent.winfo_y() + 150))
        
        # Main frame
        main = tk.Frame(self.dialog, bg=colors['card'], padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(main, text="📁 Types de Boissons", font=('Segoe UI', 14, 'bold'),
                 bg=colors['card'], fg=colors['text']).pack(anchor='w')
        
        tk.Label(main, text="Gérez les catégories pour organiser vos boissons", 
                 font=('Segoe UI', 9), bg=colors['card'], fg=colors['text_muted']).pack(anchor='w', pady=(0, 15))
        
        # Types list
        list_frame = tk.Frame(main, bg=colors['bg'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('name', 'icon', 'order')
        self.types_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                        yscrollcommand=scrollbar.set, height=8)
        
        self.types_tree.heading('name', text='Nom')
        self.types_tree.heading('icon', text='Icône')
        self.types_tree.heading('order', text='Ordre')
        
        self.types_tree.column('name', width=200)
        self.types_tree.column('icon', width=80)
        self.types_tree.column('order', width=80)
        
        self.types_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.types_tree.yview)
        
        # Buttons
        btn_frame = tk.Frame(main, bg=colors['card'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        tk.Button(btn_frame, text="➕ Ajouter", font=('Segoe UI', 10),
                  bg=colors['accent'], fg='white', padx=15, pady=8,
                  command=self.add_type).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(btn_frame, text="✏️ Modifier", font=('Segoe UI', 10),
                  bg=colors['gold'], fg='black', padx=15, pady=8,
                  command=self.edit_type).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(btn_frame, text="🗑️ Supprimer", font=('Segoe UI', 10),
                  bg=colors['red'], fg='white', padx=15, pady=8,
                  command=self.delete_type).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Fermer", font=('Segoe UI', 10),
                  bg=colors['bg'], fg=colors['text'], padx=20, pady=8,
                  command=self.dialog.destroy).pack(side=tk.RIGHT)
        
        # Load types
        self.refresh_types()
        
        self.dialog.wait_window()
        
    def refresh_types(self):
        """Refresh types list"""
        for item in self.types_tree.get_children():
            self.types_tree.delete(item)
            
        types = get_all_drink_types()
        for t in types:
            self.types_tree.insert('', 'end', iid=t['id'], values=(
                t['name'], t['icon'], t['display_order']
            ))
            
    def add_type(self):
        """Add new type"""
        dialog = TypeEditDialog(self.dialog, self.colors, None)
        if dialog.result:
            add_drink_type(**dialog.result)
            self.refresh_types()
            self.changed = True
            
    def edit_type(self):
        """Edit selected type"""
        selection = self.types_tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un type à modifier")
            return
            
        type_id = int(selection[0])
        values = self.types_tree.item(selection[0])['values']
        current = {'name': values[0], 'icon': values[1], 'display_order': values[2]}
        
        dialog = TypeEditDialog(self.dialog, self.colors, current)
        if dialog.result:
            update_drink_type(type_id, dialog.result['name'], dialog.result['icon'], dialog.result['display_order'])
            self.refresh_types()
            self.changed = True
            
    def delete_type(self):
        """Delete selected type"""
        selection = self.types_tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un type à supprimer")
            return
            
        type_id = int(selection[0])
        name = self.types_tree.item(selection[0])['values'][0]
        
        if messagebox.askyesno("Confirmer", f"Supprimer le type '{name}'?\n\nLes boissons de ce type ne seront plus affichées correctement."):
            delete_drink_type(type_id)
            self.refresh_types()
            self.changed = True


class TypeEditDialog:
    """Dialog for adding/editing a drink type"""
    
    def __init__(self, parent, colors, current=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Ajouter un Type" if not current else "Modifier le Type")
        self.dialog.geometry("350x280")
        self.dialog.configure(bg=colors['card'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center
        self.dialog.geometry("+%d+%d" % (parent.winfo_x() + 75, parent.winfo_y() + 60))
        
        # Form
        form = tk.Frame(self.dialog, bg=colors['card'], padx=25, pady=25)
        form.pack(fill=tk.BOTH, expand=True)
        
        # Name
        tk.Label(form, text="Nom du type", bg=colors['card'], fg=colors['text'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.name_entry = tk.Entry(form, font=('Segoe UI', 12), width=25)
        self.name_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Icon
        tk.Label(form, text="Icône (emoji)", bg=colors['card'], fg=colors['text'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.icon_entry = tk.Entry(form, font=('Segoe UI', 14), width=5)
        self.icon_entry.insert(0, "🍷")
        self.icon_entry.pack(anchor='w', pady=(5, 15))
        
        # Order
        tk.Label(form, text="Ordre d'affichage", bg=colors['card'], fg=colors['text'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.order_entry = tk.Entry(form, font=('Segoe UI', 12), width=8)
        self.order_entry.insert(0, "10")
        self.order_entry.pack(anchor='w', pady=(5, 20))
        
        # Fill if editing
        if current:
            self.name_entry.insert(0, current['name'])
            self.icon_entry.delete(0, tk.END)
            self.icon_entry.insert(0, current['icon'])
            self.order_entry.delete(0, tk.END)
            self.order_entry.insert(0, str(current['display_order']))
        
        # Buttons
        btn_frame = tk.Frame(form, bg=colors['card'])
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Annuler", font=('Segoe UI', 10),
                  bg=colors['bg'], fg=colors['text'], padx=20, pady=8,
                  command=self.dialog.destroy).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="💾 Sauvegarder", font=('Segoe UI', 10, 'bold'),
                  bg=colors['accent'], fg='white', padx=20, pady=8,
                  command=self.save).pack(side=tk.RIGHT)
        
        self.dialog.wait_window()
        
    def save(self):
        name = self.name_entry.get().strip()
        icon = self.icon_entry.get().strip() or "🍷"
        
        if not name:
            messagebox.showerror("Erreur", "Veuillez entrer un nom pour le type")
            return
            
        try:
            order = int(self.order_entry.get())
        except ValueError:
            order = 99
            
        self.result = {
            'name': name,
            'icon': icon,
            'display_order': order
        }
        self.dialog.destroy()


class PaymentDialog:
    """Dialog for payment method selection"""
    
    def __init__(self, parent, total, colors):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Paiement")
        self.dialog.geometry("400x350")
        self.dialog.configure(bg=colors['card'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center
        self.dialog.geometry("+%d+%d" % (parent.winfo_x() + 50, parent.winfo_y() + 50))
        
        # Header
        tk.Label(self.dialog, text="Total à Payer", font=('Segoe UI', 12),
                 bg=colors['card'], fg=colors['text_muted']).pack(pady=(20, 5))
                 
        tk.Label(self.dialog, text=f"{total:.2f} €", font=('Orbitron', 36, 'bold'),
                 bg=colors['card'], fg=colors['green']).pack(pady=(0, 20))
                 
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg=colors['card'], padx=20)
        btn_frame.pack(fill=tk.BOTH, expand=True)
        
        def set_payment(method):
            self.result = method
            self.dialog.destroy()
            
        tk.Button(btn_frame, text="💵 ESPÈCES", font=('Segoe UI', 14, 'bold'),
                  bg=colors['accent'], fg='white', pady=15,
                  command=lambda: set_payment('ESPÈCES')).pack(fill=tk.X, pady=5)
                  
        tk.Button(btn_frame, text="💳 CARTE BANCAIRE", font=('Segoe UI', 14, 'bold'),
                  bg=colors['accent'], fg='white', pady=15,
                  command=lambda: set_payment('CB')).pack(fill=tk.X, pady=5)
                  
        tk.Button(btn_frame, text="Annuler", font=('Segoe UI', 12),
                  bg=colors['bg'], fg=colors['text_muted'], pady=10,
                  command=self.dialog.destroy).pack(fill=tk.X, pady=15)
        
        self.dialog.wait_window()


class CaisseWindow:
    """Window for POS (Point of Sale) for bartenders"""
    
    def __init__(self, parent_app):
        self.app = parent_app
        self.colors = parent_app.colors
        self.cart = [] 
        self.prices_frozen = False # Freeze prices while taking an order
        
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Bar Traders - Caisse")
        self.window.state('zoomed') # Maximize
        self.window.configure(bg=self.colors['bg'])
        
        # Main Layout
        main = tk.Frame(self.window, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True)
        
        # -- LEFT: DRINKS GRID (70%) --
        left_panel = tk.Frame(main, bg=self.colors['bg'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable Main Canvas
        self.canvas = tk.Canvas(left_panel, bg=self.colors['bg'], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas, bg=self.colors['bg'])
        
        self.scrollable.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel scroll
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # -- RIGHT: TICKET (30%) --
        right_panel = tk.Frame(main, bg=self.colors['card'], width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        right_panel.pack_propagate(False)
        
        # Ticket Header
        header_frame = tk.Frame(right_panel, bg=self.colors['card'])
        header_frame.pack(fill=tk.X, pady=(20, 10))
        tk.Label(header_frame, text="🛒 Ticket en cours", font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['card'], fg=self.colors['text']).pack()
        
        self.frozen_label = tk.Label(header_frame, text="", font=('Segoe UI', 10, 'italic'),
                                     bg=self.colors['card'], fg=self.colors['gold'])
        self.frozen_label.pack()
                 
        # Cart List
        cart_frame = tk.Frame(right_panel, bg=self.colors['bg'])
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        cart_scroll = ttk.Scrollbar(cart_frame)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('name', 'price', 'type')
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show='tree', 
                                      yscrollcommand=cart_scroll.set)
        self.cart_tree.pack(fill=tk.BOTH, expand=True)
        cart_scroll.config(command=self.cart_tree.yview)
        
        self.cart_tree.column('#0', width=0, stretch=tk.NO)
        self.cart_tree.column('name', width=180, anchor='w')
        self.cart_tree.column('price', width=80, anchor='e')
        self.cart_tree.column('type', width=0, stretch=tk.NO)
        
        self.cart_tree.bind('<Double-1>', self.remove_item)
        
        # Total
        total_frame = tk.Frame(right_panel, bg=self.colors['card'], padx=20, pady=20)
        total_frame.pack(fill=tk.X)
        
        tk.Label(total_frame, text="Total à payer:", font=('Segoe UI', 12),
                 bg=self.colors['card'], fg=self.colors['text_muted']).pack(anchor='w')
        
        self.total_label = tk.Label(total_frame, text="0.00 €", font=('Orbitron', 32, 'bold'),
                 bg=self.colors['card'], fg=self.colors['green'])
        self.total_label.pack(anchor='e')
        
        # Actions
        btn_frame = tk.Frame(right_panel, bg=self.colors['card'], padx=10, pady=10)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="🗑️ Annuler", font=('Segoe UI', 12),
                  bg=self.colors['red'], fg='white', padx=10, pady=15,
                  command=self.clear_cart).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
                  
        tk.Button(btn_frame, text="✅ Valider", font=('Segoe UI', 12, 'bold'),
                  bg=self.colors['green'], fg='black', padx=10, pady=15,
                  command=self.validate_cart).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
                  
        self.refresh_grid()
        self.app.caisse_window = self

    def refresh_grid(self):
        """Refresh drink buttons"""
        # Clear existing
        for widget in self.scrollable.winfo_children():
            widget.destroy()
            
        drinks = get_drinks_by_type()
        self.drink_buttons = {}
        
        types_config = {t['name']: t for t in get_all_drink_types()}
        sorted_cats = sorted(drinks.keys(), key=lambda x: types_config.get(x, {}).get('display_order', 99))
        
        for category in sorted_cats:
            items = drinks[category]
            if not items: continue
            
            # Category Header
            icon = types_config.get(category, {}).get('icon', '')
            header = tk.Label(self.scrollable, text=f"{icon} {category}", 
                             font=('Segoe UI', 14, 'bold'),
                             bg=self.colors['bg'], fg=self.colors['gold'], anchor='w')
            header.pack(fill=tk.X, pady=(15, 5), padx=5)
            
            # Grid Frame for this category
            grid_frame = tk.Frame(self.scrollable, bg=self.colors['bg'])
            grid_frame.pack(fill=tk.X, padx=5)
            
            # Configure grid columns
            for i in range(5): # 5 columns
                grid_frame.columnconfigure(i, weight=1)
            
            cols = 5
            for i, drink in enumerate(items):
                row = i // cols
                col = i % cols
                
                btn_container = tk.Frame(grid_frame, bg=self.colors['bg'], padx=3, pady=3)
                btn_container.grid(row=row, column=col, sticky='nsew')
                
                price_text = f"{drink['price_current']:.2f}€"
                
                # Capture current price in closure
                btn = tk.Button(btn_container, text=f"{drink['name']}\n\n{price_text}", 
                                font=('Segoe UI', 10, 'bold'),
                                bg=self.colors['card'], fg=self.colors['text'],
                                height=4, width=15, wraplength=120, bd=1, relief='raised',
                                activebackground=self.colors['accent'],
                                activeforeground='white',
                                command=lambda d=drink: self.add_to_cart(d))
                btn.pack(fill=tk.BOTH, expand=True)
                
                self.drink_buttons[drink['id']] = btn
                
    def update_prices(self, drinks_data):
        """Update prices on buttons"""
        # IF FROZEN: DO NOT UPDATE DISPLAY
        if self.prices_frozen:
            return

        for category in drinks_data.values():
            for drink in category:
                btn = self.drink_buttons.get(drink['id'])
                if btn:
                    price_text = f"{drink['price_current']:.2f}€"
                    btn.config(text=f"{drink['name']}\n\n{price_text}")
                    # Update command with new drink data (price)
                    btn.config(command=lambda d=drink: self.add_to_cart(d))
                    
    def add_to_cart(self, drink):
        """Add drink to cart with price snapshot"""
        # If cart was empty, freeze prices!
        if not self.cart:
            self.prices_frozen = True
            self.frozen_label.config(text="🔒 PRIX FIGÉS")

        # Snapshot: copy drink data with frozen price at moment of click
        item = dict(drink)
        item['price_snapshot'] = drink['price_current']
        self.cart.append(item)

        name = f"{drink['name']}"
        price = f"{item['price_snapshot']:.2f} €"
        self.cart_tree.insert('', 'end', iid=len(self.cart)-1, values=(name, price, drink['type']))
        self.update_total()
        
    def remove_item(self, event):
        """Remove item from cart"""
        selection = self.cart_tree.selection()
        if selection:
            idx = int(selection[0])
            del self.cart[idx]
            
            # If cart empty, unfreeze
            if not self.cart:
                self.prices_frozen = False
                self.frozen_label.config(text="")
                # Refresh grid to show active prices immediately
                self.refresh_grid()
            
            for item in self.cart_tree.get_children():
                self.cart_tree.delete(item)
            for i, d in enumerate(self.cart):
                self.cart_tree.insert('', 'end', iid=i, values=(d['name'], f"{d['price_snapshot']:.2f} €", d['type']))
                
            self.update_total()
            
    def clear_cart(self):
        self.cart = []
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.update_total()
        
        # Unfreeze prices
        self.prices_frozen = False
        self.frozen_label.config(text="")
        self.refresh_grid()
        
    def update_total(self):
        total = sum(d['price_snapshot'] for d in self.cart)
        self.total_label.config(text=f"{total:.2f} €")

    def validate_cart(self):
        if not self.cart:
            return

        total = round(sum(d['price_snapshot'] for d in self.cart), 2)

        # Open Payment Dialog
        dialog = PaymentDialog(self.window, total, self.colors)

        if dialog.result:
            # Create Ticket
            ticket_id = create_ticket(total, dialog.result)

            # Record sales linked to ticket (using snapshot price)
            for item in self.cart:
                record_sale(item['id'], item['name'], item['price_snapshot'], quantity=1, ticket_id=ticket_id)
                
            messagebox.showinfo("Vente", f"TICKET PAYÉ ({dialog.result})\nTotal: {total:.2f} €")
            
            # Clear and unfreeze
            self.clear_cart()
            
            self.app.refresh_sales()


# ==================== MAIN ====================

if __name__ == '__main__':
    root = tk.Tk()
    app = BarTradersApp(root)
    
    print("\n" + "="*50)
    print("BAR TRADERS - Application Caisse/Admin")
    print("="*50)
    print("\nWall Display: http://localhost:5000/wall")
    print("\n" + "="*50 + "\n")
    
    root.mainloop()

