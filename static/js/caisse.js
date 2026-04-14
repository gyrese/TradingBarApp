/**
 * Caisse.js - Staff Point of Sale Interface
 * For recording sales and triggering KRASH mode
 */

// Socket connection
const socket = io();

// State
let drinks = {};
let krashActive = false;

// DOM Elements
const timerEl = document.getElementById('timer');
const timerValueEl = document.getElementById('timer-value');
const drinksContainer = document.getElementById('drinks-container');
const krashBanner = document.getElementById('krash-banner');
const krashRemaining = document.getElementById('krash-remaining');
const krashBtn = document.getElementById('krash-btn');
const mainContent = document.getElementById('main-content');
const connectionStatus = document.getElementById('connection-status');

const salesCountEl = document.getElementById('sales-count');
const salesTotalEl = document.getElementById('sales-total');
const salesListEl = document.getElementById('sales-list');

// Category icons
const categoryIcons = {
    'Bière': '🍺',
    'Soft': '🥤',
    'Cocktail': '🍹'
};

// ==================== SOCKET HANDLERS ====================

socket.on('connect', () => {
    console.log('✅ Connected to Bar Traders');
    connectionStatus.className = 'status-indicator connected';
    connectionStatus.innerHTML = '<span class="status-dot"></span><span>Connecté</span>';
});

socket.on('disconnect', () => {
    console.log('❌ Disconnected from server');
    connectionStatus.className = 'status-indicator disconnected';
    connectionStatus.innerHTML = '<span class="status-dot"></span><span>Déconnecté</span>';
});

socket.on('prices_update', (data) => {
    drinks = data.drinks;
    renderDrinks();

    // Handle krash events
    if (data.event === 'krash_started') {
        krashActive = true;
        showKrashBanner();
        updateKrashButton();
    } else if (data.event === 'krash_ended') {
        krashActive = false;
        hideKrashBanner();
        updateKrashButton();
    }
});

socket.on('timer_update', (data) => {
    updateTimer(data.timer);

    if (data.krash_active) {
        krashActive = true;
        updateKrashTimer(data.krash_remaining);
        showKrashBanner();
    } else if (krashActive) {
        krashActive = false;
        hideKrashBanner();
    }
    updateKrashButton();
});

socket.on('krash', (data) => {
    krashActive = data.active;
    if (data.active) {
        showKrashBanner();
    } else {
        hideKrashBanner();
    }
    updateKrashButton();
});

socket.on('status', (data) => {
    updateTimer(data.timer);
    krashActive = data.krash_active;
    if (krashActive) {
        updateKrashTimer(data.krash_remaining);
        showKrashBanner();
    }
    updateKrashButton();
});

socket.on('sale_recorded', (data) => {
    showToast(`Vente: ${data.drink_name} à ${data.price}€`, 'success');
    loadSales();
});

// ==================== TIMER ====================

function updateTimer(seconds) {
    timerValueEl.textContent = seconds;

    timerEl.classList.remove('warning', 'critical');

    if (seconds <= 10) {
        timerEl.classList.add('critical');
    } else if (seconds <= 20) {
        timerEl.classList.add('warning');
    }
}

// ==================== KRASH BANNER ====================

function showKrashBanner() {
    krashBanner.classList.add('active');
    mainContent.style.paddingTop = '160px';
}

function hideKrashBanner() {
    krashBanner.classList.remove('active');
    mainContent.style.paddingTop = '100px';
}

function updateKrashTimer(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    krashRemaining.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function updateKrashButton() {
    if (krashActive) {
        krashBtn.classList.add('active');
        krashBtn.innerHTML = '🛑 ARRÊTER LE KRASH';
        krashBtn.onclick = stopKrash;
    } else {
        krashBtn.classList.remove('active');
        krashBtn.innerHTML = 'KRASH ! 💥';
        krashBtn.onclick = triggerKrash;
    }
}

// ==================== RENDER DRINKS ====================


function renderDrinks() {
    const categoryOrder = ['Bière', 'Soft', 'Cocktail'];
    const sortedCategories = Object.keys(drinks).sort((a, b) => {
        const ia = categoryOrder.indexOf(a);
        const ib = categoryOrder.indexOf(b);
        return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });

    let html = '';

    for (const category of sortedCategories) {
        const categoryDrinks = drinks[category];
        if (!categoryDrinks || categoryDrinks.length === 0) continue;

        html += `
            <div class="caisse-section">
                <h3 class="caisse-section-title">
                    <span class="icon">${categoryIcons[category] || '🍷'}</span>
                    ${category}s
                </h3>
                <div class="caisse-grid" data-category="${category}">
        `;

        for (const drink of categoryDrinks) {
            html += renderDrinkButton(drink);
        }

        html += `
                </div>
            </div>
        `;
    }

    drinksContainer.innerHTML = html;
    initDragAndDrop();
}

function renderDrinkButton(drink) {
    return `
        <div class="caisse-btn ${krashActive ? 'krash' : ''}"
             data-drink-id="${drink.id}"
             data-drink-name="${drink.name.replace(/"/g, '&quot;')}"
             data-drink-price="${drink.price_current}">
            <div class="name">${drink.name}</div>
            <div class="price">${drink.price_current.toFixed(2)}€</div>
        </div>
    `;
}

// ==================== DRAG & DROP (touch + mouse) ====================

let longPressTimer = null;
let dragEl = null;
let dragGhost = null;
let dragGrid = null;
let dragStarted = false;
const LONG_PRESS_MS = 500;

function initDragAndDrop() {
    document.querySelectorAll('.caisse-btn').forEach(btn => {
        btn.addEventListener('touchstart', onPointerDown, { passive: false });
        btn.addEventListener('mousedown', onPointerDown);
    });
}

function onPointerDown(e) {
    const btn = this;
    const isTouch = e.type === 'touchstart';
    dragStarted = false;

    // Start long-press timer
    longPressTimer = setTimeout(() => {
        dragStarted = true;
        startDrag(btn, isTouch ? e.touches[0] : e);
    }, LONG_PRESS_MS);

    const moveEvt = isTouch ? 'touchmove' : 'mousemove';
    const endEvt = isTouch ? 'touchend' : 'mouseup';

    const onMove = (ev) => {
        // If still waiting for long press, cancel if finger moved too much
        if (!dragStarted) {
            const pt = ev.touches ? ev.touches[0] : ev;
            const startPt = isTouch ? e.touches[0] : e;
            const dx = pt.clientX - startPt.clientX;
            const dy = pt.clientY - startPt.clientY;
            if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                clearTimeout(longPressTimer);
                cleanup();
            }
            return;
        }
        ev.preventDefault();
        moveDrag(ev.touches ? ev.touches[0] : ev);
    };

    const onEnd = () => {
        clearTimeout(longPressTimer);
        if (dragStarted) {
            endDrag();
        } else {
            // Short tap = vente
            const id = parseInt(btn.dataset.drinkId);
            const name = btn.dataset.drinkName;
            const price = parseFloat(btn.dataset.drinkPrice);
            recordSale(id, name, price);
        }
        cleanup();
    };

    function cleanup() {
        document.removeEventListener(moveEvt, onMove);
        document.removeEventListener(endEvt, onEnd);
        if (isTouch) document.removeEventListener('touchcancel', onEnd);
    }

    document.addEventListener(moveEvt, onMove, { passive: false });
    document.addEventListener(endEvt, onEnd, { once: true });
    if (isTouch) document.addEventListener('touchcancel', onEnd, { once: true });
}

function startDrag(btn, point) {
    dragEl = btn;
    dragGrid = btn.closest('.caisse-grid');
    btn.classList.add('dragging');

    // Ghost element that follows the finger
    dragGhost = btn.cloneNode(true);
    dragGhost.classList.add('drag-ghost');
    const rect = btn.getBoundingClientRect();
    dragGhost.style.width = rect.width + 'px';
    dragGhost.style.height = rect.height + 'px';
    dragGhost.style.left = point.clientX - rect.width / 2 + 'px';
    dragGhost.style.top = point.clientY - rect.height / 2 + 'px';
    document.body.appendChild(dragGhost);

    // Vibrate on mobile if available
    if (navigator.vibrate) navigator.vibrate(30);
}

function moveDrag(point) {
    if (!dragGhost) return;

    // Move ghost
    const rect = dragGhost.getBoundingClientRect();
    dragGhost.style.left = point.clientX - rect.width / 2 + 'px';
    dragGhost.style.top = point.clientY - rect.height / 2 + 'px';

    // Highlight drop target
    document.querySelectorAll('.caisse-btn.drag-over').forEach(el => el.classList.remove('drag-over'));
    const target = getDropTarget(point);
    if (target && target !== dragEl) {
        target.classList.add('drag-over');
    }
}

function getDropTarget(point) {
    // Temporarily hide ghost so elementFromPoint finds what's underneath
    if (dragGhost) dragGhost.style.pointerEvents = 'none';
    const el = document.elementFromPoint(point.clientX, point.clientY);
    if (dragGhost) dragGhost.style.pointerEvents = '';
    if (!el) return null;
    const btn = el.closest('.caisse-btn');
    if (!btn || !dragGrid || !dragGrid.contains(btn)) return null;
    return btn;
}

function endDrag() {
    if (!dragEl || !dragGrid) return;

    // Find current drop target from ghost position
    let target = null;
    if (dragGhost) {
        const ghostRect = dragGhost.getBoundingClientRect();
        const cx = ghostRect.left + ghostRect.width / 2;
        const cy = ghostRect.top + ghostRect.height / 2;
        target = getDropTarget({ clientX: cx, clientY: cy });
    }

    if (target && target !== dragEl) {
        const allBtns = [...dragGrid.querySelectorAll('.caisse-btn')];
        const fromIdx = allBtns.indexOf(dragEl);
        const toIdx = allBtns.indexOf(target);
        if (fromIdx < toIdx) {
            target.after(dragEl);
        } else {
            target.before(dragEl);
        }
        saveDrinkOrder();
    }

    // Cleanup
    dragEl.classList.remove('dragging');
    document.querySelectorAll('.caisse-btn.drag-over').forEach(el => el.classList.remove('drag-over'));
    if (dragGhost) { dragGhost.remove(); dragGhost = null; }
    dragEl = null;
    dragGrid = null;
    dragStarted = false;
}

function saveDrinkOrder() {
    const orderList = [];
    document.querySelectorAll('.caisse-grid').forEach(grid => {
        grid.querySelectorAll('.caisse-btn').forEach((btn, idx) => {
            orderList.push({ id: parseInt(btn.dataset.drinkId), order: idx });
        });
    });

    fetch('/api/drinks/order', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderList)
    }).then(res => {
        if (res.ok) showToast('Ordre sauvegardé', 'success');
    }).catch(() => showToast('Erreur sauvegarde ordre', 'error'));
}

// ==================== SALES ====================

async function recordSale(drinkId, drinkName, price) {
    try {
        const response = await fetch('/api/sale', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                drink_id: drinkId,
                drink_name: drinkName,
                price: price,
                quantity: 1
            })
        });

        if (!response.ok) throw new Error('Failed to record sale');

        // Feedback will come from socket event

    } catch (error) {
        console.error('Error recording sale:', error);
        showToast('Erreur lors de l\'enregistrement', 'error');
    }
}

async function loadSales() {
    try {
        const response = await fetch('/api/sales');
        const data = await response.json();

        // Update summary
        salesCountEl.textContent = data.summary.count;
        salesTotalEl.textContent = data.summary.total.toFixed(2) + '€';

        // Update list
        if (data.sales.length === 0) {
            salesListEl.innerHTML = '<p class="text-muted" style="text-align: center; padding: var(--spacing-lg);">Aucune vente aujourd\'hui</p>';
        } else {
            salesListEl.innerHTML = data.sales.slice(0, 20).map(sale => `
                <div class="sale-item">
                    <div>
                        <strong>${sale.drink_name}</strong>
                        <br>
                        <small class="text-muted">${formatTime(sale.sold_at)}</small>
                    </div>
                    <div style="font-family: var(--font-mono); color: var(--green-bright);">
                        ${sale.total.toFixed(2)}€
                    </div>
                </div>
            `).join('');
        }

    } catch (error) {
        console.error('Error loading sales:', error);
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// ==================== KRASH ====================

function triggerKrash() {
    document.getElementById('confirm-modal').classList.add('active');
}

function confirmKrash() {
    closeModal();

    fetch('/api/krash', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
        .then(res => {
            if (res.ok) {
                showToast('🔥 KRASH déclenché!', 'warning');
            } else {
                throw new Error('Failed to trigger krash');
            }
        })
        .catch(err => {
            console.error('Error triggering krash:', err);
            showToast('Erreur lors du déclenchement', 'error');
        });
}

function stopKrash() {
    fetch('/api/krash', { method: 'DELETE' })
        .then(res => {
            if (res.ok) {
                showToast('KRASH arrêté', 'success');
            }
        })
        .catch(err => {
            console.error('Error stopping krash:', err);
        });
}

function closeModal() {
    document.getElementById('confirm-modal').classList.remove('active');
}

// ==================== TOAST ====================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}</span>
        <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    // Load drinks
    fetch('/api/drinks')
        .then(res => res.json())
        .then(data => {
            drinks = data;
            renderDrinks();
        })
        .catch(err => {
            console.error('Error loading drinks:', err);
            drinksContainer.innerHTML = '<p style="text-align: center; color: var(--red-bright);">Erreur de chargement</p>';
        });

    // Load sales
    loadSales();

    // Refresh sales every 30 seconds
    setInterval(loadSales, 30000);
});
