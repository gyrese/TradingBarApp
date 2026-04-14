/**
 * Admin.js - Backoffice Administration
 * CRUD operations for drinks management
 */

// Socket connection
const socket = io();

// State
let drinks = {};
let allDrinks = [];
let editingDrinkId = null;
let drinkTypes = [];   // [{id, name, icon, display_order}]

// Icon picker state
const DRINK_EMOJIS = [
    '🍺','🍻','🥂','🍷','🥃','🍸','🍹','🧉',
    '🥤','🧃','☕','🍵','🧋','🫖','🍶','🥛',
    '🍾','🫗','🌊','🫧','🍫','🍬','🍭','🍦',
    '🌴','🌺','🌸','🍋','🍊','🍓','🍒','🍍',
    '⭐','💎','🔥','❄️','🎯','🎰','🎲','♠️',
];
let selectedIcon = null; // emoji string or image URL

// DOM Elements
const timerValueEl = document.getElementById('timer-value');
const timerEl = document.getElementById('timer');
const krashBanner = document.getElementById('krash-banner');
const krashRemaining = document.getElementById('krash-remaining');

// ==================== SOCKET HANDLERS ====================

socket.on('connect', () => {
    console.log('✅ Connected to Bar Traders');
});

socket.on('prices_update', (data) => {
    drinks = data.drinks;
    flattenDrinks();
    renderTable();
    updateStats();
});

socket.on('timer_update', (data) => {
    updateTimer(data.timer);

    if (data.krash_active) {
        updateKrashTimer(data.krash_remaining);
        showKrashBanner(false);
    } else if (data.krash_pending) {
        showKrashBanner(true);
    } else {
        hideKrashBanner();
    }
});

socket.on('status', (data) => {
    updateTimer(data.timer);
    if (data.interval) syncIntervalInput(data.interval);
    if (data.krash_active) {
        updateKrashTimer(data.krash_remaining);
        showKrashBanner(false);
    } else if (data.krash_pending) {
        showKrashBanner(true);
    }
});

socket.on('krash', (data) => {
    if (data.active) {
        showKrashBanner(false);
    } else if (data.pending) {
        showKrashBanner(true);
    } else {
        hideKrashBanner();
    }
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

function showKrashBanner(pending = false) {
    const title = document.getElementById('krash-banner-title');
    const sub = document.getElementById('krash-banner-sub');
    if (pending) {
        title.textContent = '⏳ KRASH AU PROCHAIN CYCLE…';
        if (sub) sub.style.display = 'none';
        krashBanner.style.background = 'linear-gradient(135deg, #5a3a00, #3a2800)';
    } else {
        title.textContent = '🔥 KRASH EN COURS 🔥';
        if (sub) sub.style.display = '';
        krashBanner.style.background = '';
    }
    krashBanner.classList.add('active');
}

function hideKrashBanner() {
    krashBanner.classList.remove('active');
}

function updateKrashTimer(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    krashRemaining.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// ==================== DATA HELPERS ====================

function flattenDrinks() {
    allDrinks = [];
    for (const category in drinks) {
        allDrinks.push(...drinks[category]);
    }
    allDrinks.sort((a, b) => a.name.localeCompare(b.name));
}

function updateStats() {
    const container = document.getElementById('admin-stats-container');
    // Rebuild type cards (insert before the sales card which is last)
    const salesCard = container.querySelector('.stat-card:last-child');
    // Remove all previous type cards
    container.querySelectorAll('.stat-card[data-type-card]').forEach(el => el.remove());

    drinkTypes.forEach(type => {
        const count = allDrinks.filter(d => d.type === type.name).length;
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.dataset.typeCard = type.name;
        card.innerHTML = `
            <div class="stat-icon">${type.icon || '🍹'}</div>
            <div class="stat-info">
                <div class="value">${count}</div>
                <div class="label">${type.name}</div>
            </div>`;
        container.insertBefore(card, salesCard);
    });

    // Load sales stats
    fetch('/api/sales')
        .then(res => res.json())
        .then(data => {
            document.getElementById('stat-sales').textContent = data.summary.total.toFixed(2) + '€';
        });
}

// ==================== ICON PICKER ====================

function buildEmojiGrid() {
    const grid = document.getElementById('emoji-grid');
    if (!grid) return;
    grid.innerHTML = DRINK_EMOJIS.map(e =>
        `<button type="button" class="emoji-btn" data-emoji="${e}" onclick="selectEmoji('${e}')">${e}</button>`
    ).join('');
}

function selectEmoji(emoji) {
    selectedIcon = emoji;
    document.getElementById('drink-icon').value = emoji;
    updateIconPreview();
    // Highlight selected
    document.querySelectorAll('.emoji-btn').forEach(b => {
        b.classList.toggle('selected', b.dataset.emoji === emoji);
    });
}

function switchIconTab(tab) {
    document.querySelectorAll('.icon-tab').forEach((t, i) => {
        t.classList.toggle('active', (i === 0 && tab === 'emoji') || (i === 1 && tab === 'image'));
    });
    document.getElementById('icon-panel-emoji').classList.toggle('active', tab === 'emoji');
    document.getElementById('icon-panel-image').classList.toggle('active', tab === 'image');
}

function updateIconPreview() {
    const box = document.getElementById('icon-preview-box');
    const label = document.getElementById('icon-preview-label');
    if (!selectedIcon) {
        box.textContent = '?';
        if (label) label.textContent = 'Aucune icône sélectionnée';
        return;
    }
    if (selectedIcon.startsWith('/') || selectedIcon.startsWith('http')) {
        box.innerHTML = `<img src="${selectedIcon}" alt="logo">`;
        if (label) label.textContent = 'Image uploadée';
    } else {
        box.textContent = selectedIcon;
        if (label) label.textContent = `Emoji sélectionné : ${selectedIcon}`;
    }
}

function clearIcon() {
    selectedIcon = null;
    document.getElementById('drink-icon').value = '';
    document.getElementById('icon-preview-box').textContent = '?';
    const label = document.getElementById('icon-preview-label');
    if (label) label.textContent = 'Aucune icône sélectionnée';
    document.getElementById('upload-label').innerHTML = '📁 Cliquez pour choisir une image<br><small style="opacity:0.6;">PNG, JPG, WebP, SVG</small>';
    document.getElementById('logo-file-input').value = '';
    document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
}

async function handleLogoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res = await fetch('/api/drinks/upload-logo', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur upload');
        selectedIcon = data.url;
        document.getElementById('drink-icon').value = data.url;
        document.getElementById('upload-label').textContent = `✅ ${file.name}`;
        updateIconPreview();
        // Deselect any emoji
        document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== RENDER TABLE ====================

function renderTable() {
    const tbody = document.getElementById('drinks-table-body');

    if (allDrinks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: var(--spacing-xl);">
                    Aucune boisson configurée
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = allDrinks.map(drink => {
        let iconHtml = '';
        if (drink.icon) {
            if (drink.icon.startsWith('/') || drink.icon.startsWith('http')) {
                iconHtml = `<img src="${drink.icon}" alt="" style="width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;border-radius:4px;">`;
            } else {
                iconHtml = `<span style="font-size:1.3rem;margin-right:6px;vertical-align:middle;">${drink.icon}</span>`;
            }
        }
        return `
        <tr>
            <td><strong>${iconHtml}${drink.name}</strong></td>
            <td>
                <span class="drink-type-badge ${drink.type.toLowerCase()}">${drink.type}</span>
            </td>
            <td>${drink.price_min.toFixed(2)}€</td>
            <td>${drink.price_max.toFixed(2)}€</td>
            <td style="color: var(--red-bright);">${drink.price_krash.toFixed(2)}€</td>
            <td style="color: var(--green-bright); font-family: var(--font-mono); font-weight: 700;">
                ${drink.price_current.toFixed(2)}€
            </td>
            <td>${drink.tva}%</td>
            <td class="actions">
                <button class="btn btn-sm btn-primary btn-icon" onclick="openEditModal(${drink.id})" title="Modifier">
                    ✏️
                </button>
                <button class="btn btn-sm btn-danger btn-icon" onclick="openDeleteModal(${drink.id}, '${drink.name.replace(/'/g, "\\'")}')" title="Supprimer">
                    🗑️
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

// ==================== MODAL HANDLERS ====================

function openAddModal() {
    editingDrinkId = null;
    document.getElementById('modal-title').textContent = 'Ajouter une Boisson';
    document.getElementById('modal-submit-btn').textContent = 'Ajouter';
    document.getElementById('drink-form').reset();
    document.getElementById('drink-id').value = '';
    clearIcon();
    switchIconTab('emoji');
    populateTypeSelect('');
    document.getElementById('drink-modal').classList.add('active');
}

function openEditModal(drinkId) {
    const drink = allDrinks.find(d => d.id === drinkId);
    if (!drink) return;

    editingDrinkId = drinkId;
    document.getElementById('modal-title').textContent = 'Modifier la Boisson';
    document.getElementById('modal-submit-btn').textContent = 'Sauvegarder';

    document.getElementById('drink-id').value = drink.id;
    document.getElementById('drink-name').value = drink.name;
    document.getElementById('drink-type').value = drink.type;
    document.getElementById('drink-price-min').value = drink.price_min;
    document.getElementById('drink-price-max').value = drink.price_max;
    document.getElementById('drink-price-krash').value = drink.price_krash;
    document.getElementById('drink-tva').value = drink.tva;

    // Restore icon
    clearIcon();
    if (drink.icon) {
        selectedIcon = drink.icon;
        document.getElementById('drink-icon').value = drink.icon;
        updateIconPreview();
        if (drink.icon.startsWith('/') || drink.icon.startsWith('http')) {
            switchIconTab('image');
            document.getElementById('upload-label').textContent = '✅ Logo existant';
        } else {
            switchIconTab('emoji');
            document.querySelectorAll('.emoji-btn').forEach(b => {
                b.classList.toggle('selected', b.dataset.emoji === drink.icon);
            });
        }
    } else {
        switchIconTab('emoji');
    }

    populateTypeSelect(drink.type);
    document.getElementById('drink-modal').classList.add('active');
}

function closeModal() {
    document.getElementById('drink-modal').classList.remove('active');
    editingDrinkId = null;
}

function openDeleteModal(drinkId, drinkName) {
    document.getElementById('delete-drink-name').textContent = drinkName;
    document.getElementById('confirm-delete-btn').onclick = () => deleteDrink(drinkId);
    document.getElementById('delete-modal').classList.add('active');
}

function closeDeleteModal() {
    document.getElementById('delete-modal').classList.remove('active');
}

// ==================== CRUD OPERATIONS ====================

document.getElementById('drink-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const data = {
        name: document.getElementById('drink-name').value,
        type: document.getElementById('drink-type').value,
        price_min: parseFloat(document.getElementById('drink-price-min').value),
        price_max: parseFloat(document.getElementById('drink-price-max').value),
        price_krash: parseFloat(document.getElementById('drink-price-krash').value),
        tva: parseFloat(document.getElementById('drink-tva').value) || 20,
        icon: document.getElementById('drink-icon').value || null
    };

    // Validate
    if (data.price_min > data.price_max) {
        showToast('Le prix minimum doit être inférieur au prix maximum', 'error');
        return;
    }

    if (data.price_krash > data.price_min) {
        showToast('Le prix krash doit être inférieur au prix minimum', 'error');
        return;
    }

    try {
        let response;

        if (editingDrinkId) {
            // Update
            response = await fetch(`/api/drinks/${editingDrinkId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            // Create
            response = await fetch('/api/drinks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Operation failed');
        }

        closeModal();
        showToast(editingDrinkId ? 'Boisson modifiée!' : 'Boisson ajoutée!', 'success');
        loadDrinks();

    } catch (error) {
        console.error('Error saving drink:', error);
        showToast(error.message, 'error');
    }
});

async function deleteDrink(drinkId) {
    try {
        const response = await fetch(`/api/drinks/${drinkId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Delete failed');

        closeDeleteModal();
        showToast('Boisson supprimée', 'success');
        loadDrinks();

    } catch (error) {
        console.error('Error deleting drink:', error);
        showToast('Erreur lors de la suppression', 'error');
    }
}

// ==================== LOAD DATA ====================

async function loadTypes() {
    try {
        const res = await fetch('/api/types/list');
        drinkTypes = await res.json();
        populateTypeSelect();
    } catch (e) {
        console.error('Error loading types:', e);
    }
}

function populateTypeSelect(currentValue) {
    const sel = document.getElementById('drink-type');
    if (!sel) return;
    const prev = currentValue !== undefined ? currentValue : sel.value;
    sel.innerHTML = drinkTypes
        .map(t => `<option value="${t.name}">${t.icon || ''} ${t.name}</option>`)
        .join('');
    if (prev && [...sel.options].some(o => o.value === prev)) {
        sel.value = prev;
    }
}

async function loadDrinks() {
    try {
        const response = await fetch('/api/drinks');
        drinks = await response.json();
        flattenDrinks();
        renderTable();
        updateStats();
    } catch (error) {
        console.error('Error loading drinks:', error);
    }
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

// ==================== PIN ====================

async function changePin() {
    const current = document.getElementById('pin-current').value.trim();
    const newPin = document.getElementById('pin-new').value.trim();
    const confirm = document.getElementById('pin-confirm').value.trim();

    if (!current || !newPin || !confirm) {
        showToast('Remplissez tous les champs PIN', 'error');
        return;
    }
    if (newPin !== confirm) {
        showToast('Les nouveaux PIN ne correspondent pas', 'error');
        return;
    }
    if (!/^\d{4,8}$/.test(newPin)) {
        showToast('Le PIN doit être composé de 4 à 8 chiffres', 'error');
        return;
    }

    try {
        const res = await fetch('/api/settings/pin', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_pin: current, new_pin: newPin })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur');
        document.getElementById('pin-current').value = '';
        document.getElementById('pin-new').value = '';
        document.getElementById('pin-confirm').value = '';
        showToast('Code PIN modifié avec succès', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== TYPE MODAL ====================

// Réutilise la même liste que le picker de boissons
const TYPE_EMOJIS = DRINK_EMOJIS;

function openTypeModal() {
    document.getElementById('type-name').value = '';
    document.getElementById('type-icon').value = '🍷';
    document.getElementById('type-icon-preview').textContent = '🍷';

    const grid = document.getElementById('type-emoji-grid');
    grid.innerHTML = TYPE_EMOJIS.map(e =>
        `<button type="button" class="emoji-btn" data-te="${e}" onclick="selectTypeEmoji('${e}')">${e}</button>`
    ).join('');
    // Pre-select first
    selectTypeEmoji('🍷');

    document.getElementById('type-modal').classList.add('active');
}

function closeTypeModal() {
    document.getElementById('type-modal').classList.remove('active');
}

function selectTypeEmoji(emoji) {
    document.getElementById('type-icon').value = emoji;
    document.getElementById('type-icon-preview').textContent = emoji;
    document.querySelectorAll('#type-emoji-grid .emoji-btn').forEach(b => {
        b.classList.toggle('selected', b.dataset.te === emoji);
    });
}

async function saveType(e) {
    e.preventDefault();
    const name = document.getElementById('type-name').value.trim();
    const icon = document.getElementById('type-icon').value || '🍷';
    if (!name) return;
    try {
        const res = await fetch('/api/types', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, icon })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur');
        closeTypeModal();
        showToast(`Type "${name}" créé !`, 'success');
        await loadTypes();
        // Auto-select the new type in the drink form
        populateTypeSelect(name);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== EDIT TYPE MODAL ====================

function openEditTypeModal() {
    const sel = document.getElementById('drink-type');
    const selectedName = sel.value;
    const type = drinkTypes.find(t => t.name === selectedName);
    if (!type) {
        showToast('Sélectionne un type à modifier', 'error');
        return;
    }

    document.getElementById('edit-type-id').value = type.id;
    document.getElementById('edit-type-name').value = type.name;
    document.getElementById('edit-type-icon').value = type.icon || '🍷';
    document.getElementById('edit-type-icon-preview').textContent = type.icon || '🍷';

    const grid = document.getElementById('edit-type-emoji-grid');
    grid.innerHTML = TYPE_EMOJIS.map(e =>
        `<button type="button" class="emoji-btn ${e === type.icon ? 'selected' : ''}" data-ete="${e}" onclick="selectEditTypeEmoji('${e}')">${e}</button>`
    ).join('');

    document.getElementById('edit-type-modal').classList.add('active');
}

function closeEditTypeModal() {
    document.getElementById('edit-type-modal').classList.remove('active');
}

function selectEditTypeEmoji(emoji) {
    document.getElementById('edit-type-icon').value = emoji;
    document.getElementById('edit-type-icon-preview').textContent = emoji;
    document.querySelectorAll('#edit-type-emoji-grid .emoji-btn').forEach(b => {
        b.classList.toggle('selected', b.dataset.ete === emoji);
    });
}

async function saveEditType(e) {
    e.preventDefault();
    const id = parseInt(document.getElementById('edit-type-id').value);
    const name = document.getElementById('edit-type-name').value.trim();
    const icon = document.getElementById('edit-type-icon').value || '🍷';
    const type = drinkTypes.find(t => t.id === id);
    const display_order = type ? type.display_order : 99;

    try {
        const res = await fetch(`/api/types/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, icon, display_order })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur');
        closeEditTypeModal();
        showToast(`Type "${name}" modifié !`, 'success');
        await loadTypes();
        populateTypeSelect(name);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== Z HISTORY MODAL ====================

var zAllSessions = [];
var zFilterYear = null;
var zFilterMonth = null;
var MONTHS_FR = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];

function openZModal() {
    document.getElementById('z-modal').classList.add('active');
    zFilterYear = null;
    zFilterMonth = null;
    loadZHistory();
}

function closeZModal() {
    document.getElementById('z-modal').classList.remove('active');
}

function loadZHistory() {
    var tbody = document.getElementById('z-history-body');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;"><div class="loading-spinner" style="margin:0 auto;"></div></td></tr>';

    fetch('/api/sessions')
        .then(function(res) {
            if (!res.ok) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#ff5252;padding:2rem;">Erreur ' + res.status + '</td></tr>';
                return;
            }
            return res.json();
        })
        .then(function(sessions) {
            if (!sessions || !sessions.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:2rem;">Aucun Z enregistré</td></tr>';
                document.getElementById('z-year-filters').innerHTML = '';
                document.getElementById('z-month-filters').innerHTML = '';
                return;
            }
            zAllSessions = sessions;
            buildZFilters();
            renderZTable();
        })
        .catch(function(err) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#ff5252;padding:2rem;">Erreur: ' + err.message + '</td></tr>';
        });
}

function buildZFilters() {
    var years = {}, months = {};
    zAllSessions.forEach(function(s) {
        var d = new Date(s.closed_at + 'Z');
        years[d.getFullYear()] = true;
        months[d.getMonth()] = true;
    });

    // Year buttons
    var yearHtml = '<button class="z-filter-btn' + (zFilterYear === null ? ' active' : '') + '" onclick="setZFilter(\'year\', null)">Tout</button>';
    Object.keys(years).sort().reverse().forEach(function(y) {
        yearHtml += '<button class="z-filter-btn' + (zFilterYear == y ? ' active' : '') + '" onclick="setZFilter(\'year\', ' + y + ')">' + y + '</button>';
    });
    document.getElementById('z-year-filters').innerHTML = yearHtml;

    // Month buttons
    var monthHtml = '<button class="z-filter-btn' + (zFilterMonth === null ? ' active' : '') + '" onclick="setZFilter(\'month\', null)">Tout</button>';
    Object.keys(months).sort(function(a,b){return a-b;}).forEach(function(m) {
        monthHtml += '<button class="z-filter-btn' + (zFilterMonth == m ? ' active' : '') + '" onclick="setZFilter(\'month\', ' + m + ')">' + MONTHS_FR[m] + '</button>';
    });
    document.getElementById('z-month-filters').innerHTML = monthHtml;
}

function setZFilter(type, value) {
    if (type === 'year') zFilterYear = value;
    if (type === 'month') zFilterMonth = value;
    buildZFilters();
    renderZTable();
}

function renderZTable() {
    var tbody = document.getElementById('z-history-body');
    var filtered = zAllSessions.filter(function(s) {
        var d = new Date(s.closed_at + 'Z');
        if (zFilterYear !== null && d.getFullYear() != zFilterYear) return false;
        if (zFilterMonth !== null && d.getMonth() != zFilterMonth) return false;
        return true;
    });

    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:2rem;">Aucun Z pour cette période</td></tr>';
        document.getElementById('z-filter-summary').textContent = '0 résultat';
        return;
    }

    var totalCA = filtered.reduce(function(sum, s) { return sum + s.total_revenue; }, 0);
    document.getElementById('z-filter-summary').innerHTML = filtered.length + ' Z &nbsp;|&nbsp; CA total : <strong style="color:var(--green-bright)">' + totalCA.toFixed(2) + '€</strong>';

    var html = '';
    for (var i = 0; i < filtered.length; i++) {
        var s = filtered[i];
        var idx = zAllSessions.indexOf(s);
        var d = new Date(s.closed_at + 'Z');
        var dateStr = d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});

        var breakdownHtml = '—';
        try {
            var bd = JSON.parse(s.breakdown_json);
            var methods = bd.methods || [];
            var parts = [];
            for (var j = 0; j < methods.length; j++) {
                parts.push(methods[j].payment_method + ': <strong>' + parseFloat(methods[j].revenue).toFixed(2) + '€</strong>');
            }
            if (parts.length) breakdownHtml = parts.join(' | ');
        } catch(e) {}

        var num = 'Z' + String(zAllSessions.length - idx).padStart(3, '0');
        html += '<tr>'
            + '<td style="font-family:var(--font-mono);color:var(--text-muted);">' + num + '</td>'
            + '<td>' + dateStr + '</td>'
            + '<td style="font-family:var(--font-mono);">' + s.total_tickets + '</td>'
            + '<td style="font-family:var(--font-mono);color:var(--green-bright);font-weight:700;">' + parseFloat(s.total_revenue).toFixed(2) + '€</td>'
            + '<td style="font-size:0.85rem;">' + breakdownHtml + '</td>'
            + '</tr>';
    }
    tbody.innerHTML = html;
}

// ==================== INTERVAL ====================

function syncIntervalInput(seconds) {
    const input = document.getElementById('interval-input');
    if (input) input.value = seconds;
}

async function setInterval_(event) {
    event.preventDefault();
    const input = document.getElementById('interval-input');
    const feedback = document.getElementById('interval-feedback');
    const seconds = parseInt(input.value, 10);
    if (isNaN(seconds) || seconds < 10 || seconds > 3600) {
        input.style.borderColor = '#ff5252';
        return;
    }
    input.style.borderColor = '';
    const res = await fetch('/api/interval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seconds })
    });
    if (res.ok) {
        feedback.style.display = 'inline';
        setTimeout(() => { feedback.style.display = 'none'; }, 2000);
    } else {
        input.style.borderColor = '#ff5252';
    }
}

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', async () => {
    buildEmojiGrid();
    loadTypes().then(() => loadDrinks());
    // Sync interval input with current engine value
    try {
        const res = await fetch('/api/status');
        if (res.ok) {
            const data = await res.json();
            if (data.interval) syncIntervalInput(data.interval);
        }
    } catch (_) {}
});
