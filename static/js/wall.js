/**
 * Wall.js - Public Display Logic
 * Real-time price display with WebSocket synchronization
 */

// Socket connection with auto-reconnect
const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: Infinity
});

// State
let drinks = {};
let krashActive = false;

// Shared audio context (avoid creating one per KRASH)
let audioCtx = null;

// DOM Elements
const timerEl = document.getElementById('timer');
const timerValueEl = document.getElementById('timer-value');
const drinksContainer = document.getElementById('drinks-container');
const krashBanner = document.getElementById('krash-banner');
const krashRemaining = document.getElementById('krash-remaining');
const mainContent = document.getElementById('main-content');

// Category icons
const categoryIcons = {
    'Bière': '🍺',
    'Soft': '🥤',
    'Cocktail': '🍹'
};

// ==================== SOCKET HANDLERS ====================

socket.on('connect', () => {
    console.log('Connected to Bar Traders');
    document.body.classList.remove('disconnected');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    document.body.classList.add('disconnected');
});

socket.on('reconnect', () => {
    console.log('Reconnected to Bar Traders');
    document.body.classList.remove('disconnected');
    socket.emit('request_prices');
});

socket.on('prices_update', (data) => {
    console.log('📈 Prices update:', data.event);
    drinks = data.drinks;
    renderDrinks(data.event === 'price_update' || data.event === 'krash_started' || data.event === 'krash_ended');
    
    // Handle krash events
    if (data.event === 'krash_started') {
        krashActive = true;
        showKrashBanner();
        playSound('krash');
    } else if (data.event === 'krash_ended') {
        krashActive = false;
        hideKrashBanner();
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
});

socket.on('krash', (data) => {
    krashActive = data.active;
    if (data.active) {
        showKrashBanner();
    } else {
        hideKrashBanner();
    }
});

socket.on('status', (data) => {
    updateTimer(data.timer);
    krashActive = data.krash_active;
    if (krashActive) {
        updateKrashTimer(data.krash_remaining);
        showKrashBanner();
    }
});

// ==================== TIMER ====================

function updateTimer(seconds) {
    timerValueEl.textContent = seconds;
    
    // Remove all classes
    timerEl.classList.remove('warning', 'critical');
    
    // Add appropriate class
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

// ==================== RENDER DRINKS ====================

function renderDrinks(animate = false) {
    // Sort categories
    const categoryOrder = ['Bière', 'Soft', 'Cocktail'];
    const sortedCategories = Object.keys(drinks).sort((a, b) => {
        return categoryOrder.indexOf(a) - categoryOrder.indexOf(b);
    });
    
    let html = '';
    
    for (const category of sortedCategories) {
        const categoryDrinks = drinks[category];
        if (!categoryDrinks || categoryDrinks.length === 0) continue;
        
        html += `
            <section class="category-section">
                <div class="category-header">
                    <span class="category-icon">${categoryIcons[category] || '🍷'}</span>
                    <h2 class="category-title">${category}s</h2>
                </div>
                <div class="drinks-grid">
        `;
        
        for (const drink of categoryDrinks) {
            html += renderDrinkCard(drink, animate);
        }
        
        html += `
                </div>
            </section>
        `;
    }
    
    drinksContainer.innerHTML = html;
    
    // Draw sparklines
    setTimeout(() => {
        document.querySelectorAll('.sparkline').forEach(canvas => {
            const drinkId = canvas.dataset.drinkId;
            drawSparkline(canvas, drinkId);
        });
    }, 100);
}

function renderDrinkCard(drink, animate) {
    const variation = drink.price_previous ? drink.price_current - drink.price_previous : 0;
    const isRising = variation > 0;
    const isFalling = variation < 0;
    
    let cardClass = 'drink-card';
    if (krashActive) cardClass += ' krash';
    else if (isRising) cardClass += ' rising';
    else if (isFalling) cardClass += ' falling';
    
    const arrowClass = isRising ? 'up' : (isFalling ? 'down' : '');
    const arrow = isRising ? '▲' : (isFalling ? '▼' : '');
    const variationClass = isRising ? 'positive' : (isFalling ? 'negative' : '');
    const variationText = variation !== 0 ? (isRising ? '+' : '') + variation.toFixed(2) + '€' : '-';
    
    const priceClass = animate ? 'price-updating' : '';
    
    return `
        <div class="${cardClass}" data-drink-id="${drink.id}">
            <div class="drink-name">
                ${drink.name}
                <span class="drink-type">${drink.type}</span>
            </div>
            <div class="drink-price-container">
                <div class="drink-price ${priceClass}">
                    ${drink.price_current.toFixed(2)}<span class="drink-price-unit">€</span>
                </div>
                <div class="drink-variation">
                    ${arrow ? `<span class="variation-arrow ${arrowClass}">${arrow}</span>` : ''}
                    <span class="variation-amount ${variationClass}">${variationText}</span>
                </div>
            </div>
            <div class="sparkline-container">
                <canvas class="sparkline" data-drink-id="${drink.id}"></canvas>
            </div>
        </div>
    `;
}

// ==================== SPARKLINE ====================

async function drawSparkline(canvas, drinkId) {
    // Fetch price history
    try {
        const response = await fetch(`/api/history/${drinkId}?limit=15`);
        const history = await response.json();
        
        if (!history || history.length < 2) {
            // Not enough data, draw placeholder
            return;
        }
        
        const ctx = canvas.getContext('2d');
        const width = canvas.offsetWidth;
        const height = canvas.offsetHeight;
        
        canvas.width = width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        
        // Get min/max for scaling
        const prices = history.map(h => h.price).reverse();
        const min = Math.min(...prices);
        const max = Math.max(...prices);
        const range = max - min || 1;
        
        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = prices[prices.length - 1] >= prices[0] ? '#00ff88' : '#ff4757';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        const step = width / (prices.length - 1);
        
        prices.forEach((price, i) => {
            const x = i * step;
            const y = height - ((price - min) / range) * (height - 4) - 2;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        const color = prices[prices.length - 1] >= prices[0] ? 'rgba(0, 255, 136,' : 'rgba(255, 71, 87,';
        gradient.addColorStop(0, color + '0.3)');
        gradient.addColorStop(1, color + '0)');
        
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
        
    } catch (error) {
        console.error('Error fetching history:', error);
    }
}

// ==================== SOUNDS ====================

function playSound(type) {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        if (type === 'krash') {
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(220, audioCtx.currentTime + 0.5);
            gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);

            oscillator.start(audioCtx.currentTime);
            oscillator.stop(audioCtx.currentTime + 0.5);
        }
    } catch (e) {
        console.warn('Audio not available:', e);
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

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    // Initial load
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
});
