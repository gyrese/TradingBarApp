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
        showKrashBanner();
    } else {
        hideKrashBanner();
    }
});

socket.on('status', (data) => {
    updateTimer(data.timer);
    if (data.krash_active) {
        updateKrashTimer(data.krash_remaining);
        showKrashBanner();
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

function showKrashBanner() {
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
    // Count by type
    const beers = allDrinks.filter(d => d.type === 'Bière').length;
    const softs = allDrinks.filter(d => d.type === 'Soft').length;
    const cocktails = allDrinks.filter(d => d.type === 'Cocktail').length;

    document.getElementById('stat-beers').textContent = beers;
    document.getElementById('stat-softs').textContent = softs;
    document.getElementById('stat-cocktails').textContent = cocktails;

    // Load sales stats
    fetch('/api/sales')
        .then(res => res.json())
        .then(data => {
            document.getElementById('stat-sales').textContent = data.summary.total.toFixed(2) + '€';
        });
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

    tbody.innerHTML = allDrinks.map(drink => `
        <tr>
            <td><strong>${drink.name}</strong></td>
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
    `).join('');
}

// ==================== MODAL HANDLERS ====================

function openAddModal() {
    editingDrinkId = null;
    document.getElementById('modal-title').textContent = 'Ajouter une Boisson';
    document.getElementById('modal-submit-btn').textContent = 'Ajouter';
    document.getElementById('drink-form').reset();
    document.getElementById('drink-id').value = '';
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
        tva: parseFloat(document.getElementById('drink-tva').value) || 20
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

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    loadDrinks();
});
