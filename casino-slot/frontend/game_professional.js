// Professional Cosmic Fortunes - Game Logic
// Use nginx reverse proxy in prod (/api). Fallback to localhost:5000 in dev on port 8000.
const API_BASE = (location.port === '8000') ? 'http://localhost:5000/api' : '/api';
let sessionId = null;
let balance = 0.00; // wallet-backed
let betAmount = 1.50;
let lotSize = 1; // bet multiplier ("lot")
let isSpinning = false;
let autoSpinCount = 0;
let autoSpinActive = false;
let supportConversationId = null;

// ---- Analytics ----
async function track(name, props = {}) {
    try {
        await fetch(`${API_BASE}/analytics/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, name, props })
        });
    } catch (_) { /* ignore analytics errors */ }
}

// Initialize game
async function initGame() {
    try {
        const response = await fetch(`${API_BASE}/game/new`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        sessionId = data.session_id;
        console.log('Game initialized:', sessionId);
        await refreshWallet();
        await refreshBankroll();
    } catch (error) {
        console.error('Failed to initialize game:', error);
        alert('Backend unavailable. Please start the API and reload.');
        disableUIForBackendDown();
    }
}

// Update display
function updateDisplay() {
    document.getElementById('balance').textContent = formatUsd(balance);
    document.getElementById('betDisplay').textContent = betAmount.toFixed(2);
    const total = betAmount * lotSize;
    document.getElementById('totalBetDisplay').textContent = formatUsd(total);
    const lotEl = document.getElementById('lotDisplay');
    if (lotEl) lotEl.textContent = String(lotSize);
}

function formatUsd(v) { return `$${Number(v || 0).toFixed(2)}`; }

// Bet controls
document.getElementById('betUpBtn').addEventListener('click', () => {
    if (betAmount < 100) {
        betAmount += 0.50;
        updateDisplay();
    }
});

document.getElementById('betDownBtn').addEventListener('click', () => {
    if (betAmount > 0.10) {
        betAmount -= 0.50;
        updateDisplay();
    }
});

// Lot controls
const lotUpBtn = document.getElementById('lotUpBtn');
const lotDownBtn = document.getElementById('lotDownBtn');
if (lotUpBtn) lotUpBtn.addEventListener('click', () => { if (lotSize < 100) { lotSize += 1; updateDisplay(); } });
if (lotDownBtn) lotDownBtn.addEventListener('click', () => { if (lotSize > 1) { lotSize -= 1; updateDisplay(); } });

// Spin function
async function spin() {
    if (isSpinning) return;
    const wager = betAmount * lotSize;
    if (balance < wager) {
        alert('Insufficient balance!');
        return;
    }

    isSpinning = true;
    const spinBtn = document.getElementById('spinBtn');
    spinBtn.disabled = true;
    spinBtn.textContent = 'SPIN...';

    try {
        // Animate reels
        animateReels();

        // Track spin attempt
        track('spin_attempt', { wager, betAmount, lotSize });

        // Get result from API
        const response = await fetch(`${API_BASE}/game/spin/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_amount: betAmount * lotSize })
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ error: 'Spin failed' }));
            throw new Error(err.error || 'Spin failed');
        }
        const result = await response.json();

        // Display result after animation
        setTimeout(() => {
            displayResult(result);
            // Trust server wallet balance
            balance = Number(result.wallet_balance || balance);
            updateDisplay();

            // Show win if any
            if (result.total_win > 0) {
                showWin(result.total_win);
            }
            // Update wallet modal quick stats
            updateWalletQuickStats(result);

            // Track spin result
            track('spin_result', {
                total_win: result.total_win,
                profit: result.profit,
                wager,
                nonce: result.nonce
            });

            isSpinning = false;
            spinBtn.disabled = false;
            spinBtn.textContent = 'SPIN';

            // Continue auto-spin if active
            if (autoSpinActive && autoSpinCount > 0) {
                autoSpinCount--;
                document.getElementById('autoSpinCount').textContent = autoSpinCount;
                if (autoSpinCount > 0) {
                    setTimeout(spin, 1000);
                } else {
                    stopAutoSpin();
                }
            }
        }, 1500);

    } catch (error) {
        console.error('Spin error:', error);
        track('spin_failed', { message: error.message, wager, betAmount, lotSize });
        alert(error.message || 'Spin failed');
        isSpinning = false;
        spinBtn.disabled = false;
        spinBtn.textContent = 'SPIN';
    }
}

// Animate reels
function animateReels() {
    const reels = document.querySelectorAll('.reel');
    reels.forEach(reel => {
        reel.classList.add('spinning');
    });
    
    setTimeout(() => {
        reels.forEach(reel => {
            reel.classList.remove('spinning');
        });
    }, 1500);
}

// Display result
function displayResult(result) {
    const grid = result.grid;
    const slotDisplay = document.getElementById('slotDisplay');
    
    // Clear winning classes
    document.querySelectorAll('.symbol').forEach(s => s.classList.remove('winning'));
    
    // Update symbols
    for (let col = 0; col < 5; col++) {
        const reel = document.getElementById(`reel-${col}`);
        const symbols = reel.querySelectorAll('.symbol');
        
        for (let row = 0; row < 3; row++) {
            const symbol = grid[row][col];
            const symbolDiv = symbols[row];
            
            // Clear previous content
            symbolDiv.innerHTML = '';
            
            if (symbol === 'WILD') {
                symbolDiv.innerHTML = '<div class="wild-text">WILD!</div>';
            } else {
                symbolDiv.textContent = symbol;
            }
        }
    }
    
    // Highlight winning symbols
    if (result.wins && result.wins.length > 0) {
        result.wins.forEach(win => {
            win.positions.forEach(([row, col]) => {
                const reel = document.getElementById(`reel-${col}`);
                const symbols = reel.querySelectorAll('.symbol');
                symbols[row].classList.add('winning');
            });
        });
        
        // Show bonus banner if big win
        const wagerForBanner = betAmount * lotSize;
        if (result.total_win >= wagerForBanner * 10) {
            const banner = document.getElementById('bonusBanner');
            banner.classList.add('active');
            setTimeout(() => banner.classList.remove('active'), 3000);
        }
    }
}

// Show win display
function showWin(amount) {
    const winDisplay = document.getElementById('winDisplay');
    const winAmount = document.getElementById('winAmount');
    const winText = document.getElementById('winText');
    
    winAmount.textContent = `$${amount.toFixed(2)}`;
    
    if (amount >= betAmount * lotSize * 20) {
        winText.textContent = 'MEGA WIN!';
    } else if (amount >= betAmount * lotSize * 10) {
        winText.textContent = 'BIG WIN!';
    } else if (amount >= betAmount * lotSize * 5) {
        winText.textContent = 'GREAT WIN!';
    } else {
        winText.textContent = 'WIN!';
    }
    
    winDisplay.style.display = 'block';
    
    setTimeout(() => {
        winDisplay.style.display = 'none';
    }, 2000);
}

// Simulate spin (demo mode)
// (Demo-only spin removed; backend is required.)

// Auto-spin
document.getElementById('autoplayBtn').addEventListener('click', () => {
    if (autoSpinActive) {
        stopAutoSpin();
    } else {
        startAutoSpin();
    }
});

function startAutoSpin() {
    const count = prompt('How many auto spins? (10, 25, 50, 100)', '10');
    if (!count) return;
    
    autoSpinCount = parseInt(count);
    autoSpinActive = true;
    
    document.getElementById('autoSpinIndicator').style.display = 'block';
    document.getElementById('autoSpinCount').textContent = autoSpinCount;
    document.getElementById('autoplayBtn').textContent = 'STOP\nAUTO';
    
    spin();
}

function stopAutoSpin() {
    autoSpinActive = false;
    autoSpinCount = 0;
    document.getElementById('autoSpinIndicator').style.display = 'none';
    document.getElementById('autoplayBtn').textContent = 'AUTOPLAY';
}

// Spin button
document.getElementById('spinBtn').addEventListener('click', spin);

// Bet options
document.getElementById('betOptionsBtn').addEventListener('click', () => {
    const amount = prompt('Enter bet amount (0.10 - 100):', betAmount.toFixed(2));
    if (amount && !isNaN(amount)) {
        const newBet = parseFloat(amount);
        if (newBet >= 0.10 && newBet <= 100) {
            betAmount = newBet;
            updateDisplay();
        }
    }
});

// Navigation
document.getElementById('navHome').addEventListener('click', () => {
    openModal('homeModal');
    updateModalStats();
    setActiveNav('navHome');
});

document.getElementById('navPayouts').addEventListener('click', () => {
    const statsPanel = document.getElementById('statsPanel');
    statsPanel.style.display = statsPanel.style.display === 'none' ? 'block' : 'none';
    setActiveNav('navPayouts');
});

document.getElementById('navSettings').addEventListener('click', () => {
    openModal('settingsModal');
    setActiveNav('navSettings');
});

document.getElementById('navMenu').addEventListener('click', () => {
    alert('Menu:\n\n🎰 Game Rules\n📊 Statistics\n🏆 Leaderboard\n❓ Help\n\nComing soon!');
    setActiveNav('navMenu');
});

// Wallet nav (small wallet entry)
const navWallet = document.getElementById('navWallet');
if (navWallet) navWallet.addEventListener('click', () => {
    openWalletModal('deposit');
    setActiveNav('navWallet');
});

// Modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'flex';
    modal.classList.add('show');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

// Update modal stats
function updateModalStats() {
    document.getElementById('modalBalance').textContent = `$${balance.toFixed(2)}`;
    document.getElementById('modalBet').textContent = `$${(betAmount * lotSize).toFixed(2)}`;
}

// Set active navigation
function setActiveNav(navId) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.getElementById(navId).classList.add('active');
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeModal(e.target.id);
    }
});

// Close buttons (no inline handlers; supports strict CSP)
document.addEventListener('click', (e) => {
    const btn = e.target.closest('.close-btn');
    if (!btn) return;
    const modal = btn.closest('.modal');
    if (modal && modal.id) closeModal(modal.id);
});

// ---- Marketing site JS: smooth scroll, CTAs, FAQ ----
document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-scroll]');
    if (a && a.getAttribute('href') && a.getAttribute('href').startsWith('#')) {
        e.preventDefault();
        const id = a.getAttribute('href').slice(1);
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});

;['heroPlayCta','navPlayCta'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', () => {
        track('cta_click', { source: id });
        const play = document.getElementById('play');
        if (play) play.scrollIntoView({ behavior: 'smooth' });
    });
});

;['heroDepositCta','navDepositCta'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', () => { track('cta_click', { source: id }); openWalletModal('deposit'); });
});

document.addEventListener('click', (e) => {
    const btn = e.target.closest('.faq-q');
    if (btn) {
        const item = btn.closest('.faq-item');
        if (item) item.classList.toggle('open');
    }
});

// Settings toggles
document.addEventListener('DOMContentLoaded', () => {
    // Wallet buttons
    const addBtn = document.getElementById('addFundsBtn');
    const wdBtn = document.getElementById('withdrawBtn');
    const depSubmit = document.getElementById('depositSubmit');
    const wdSubmit = document.getElementById('withdrawSubmit');
    const openSettingsBtn = document.getElementById('openSettingsBtn');
    const backBtn = document.querySelector('.balance-box .icon-btn');

    if (addBtn) addBtn.addEventListener('click', () => openWalletModal('deposit'));
    if (wdBtn) wdBtn.addEventListener('click', () => openWalletModal('withdraw'));
    if (depSubmit) depSubmit.addEventListener('click', onDepositSubmit);
    if (wdSubmit) wdSubmit.addEventListener('click', onWithdrawSubmit);
    if (openSettingsBtn) openSettingsBtn.addEventListener('click', () => openModal('settingsModal'));
    if (backBtn) backBtn.addEventListener('click', () => { openModal('homeModal'); updateModalStats(); setActiveNav('navHome'); });

    const soundToggle = document.getElementById('soundToggle');
    const musicToggle = document.getElementById('musicToggle');
    const animationsToggle = document.getElementById('animationsToggle');
    const turboModeToggle = document.getElementById('turboModeToggle');

    if (soundToggle) {
        soundToggle.addEventListener('change', (e) => {
            console.log('Sound effects:', e.target.checked ? 'ON' : 'OFF');
        });
    }

    if (musicToggle) {
        musicToggle.addEventListener('change', (e) => {
            console.log('Background music:', e.target.checked ? 'ON' : 'OFF');
        });
    }

    if (animationsToggle) {
        animationsToggle.addEventListener('change', (e) => {
            console.log('Animations:', e.target.checked ? 'ON' : 'OFF');
        });
    }

    if (turboModeToggle) {
        turboModeToggle.addEventListener('change', (e) => {
            console.log('Turbo mode:', e.target.checked ? 'ON' : 'OFF');
        });
    }
});

// Initialize on load
window.addEventListener('load', () => {
    initGame();
    updateDisplay();
    setActiveNav('navHome');
    // Footer year
    const y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
    // Start promo countdown (3 hours)
    initPromoCountdown(3 * 60 * 60);
    // Wire promo CTA
    const promoBtn = document.getElementById('promoDepositCta');
    if (promoBtn) promoBtn.addEventListener('click', () => { track('cta_click', { source: 'promoDepositCta' }); openWalletModal('deposit'); });
    // Page view
    track('page_view', { page: 'index_professional' });
    // Wire support chat button
    const supportBtn = document.getElementById('supportChatBtn');
    if (supportBtn) supportBtn.addEventListener('click', () => { openSupportChat(); });
});

// -------- Wallet helpers --------
async function refreshWallet() {
    if (!sessionId) return;
    try {
        const r = await fetch(`${API_BASE}/wallet/balance/${sessionId}`);
        if (r.ok) {
            const d = await r.json();
            balance = Number(d.balance || 0);
            updateDisplay();
        }
    } catch (e) { console.warn('wallet/balance failed'); }
}

async function refreshTransactions() {
    if (!sessionId) return [];
    try {
        const r = await fetch(`${API_BASE}/wallet/transactions/${sessionId}`);
        if (r.ok) {
            const d = await r.json();
            return d.transactions || [];
        }
    } catch (e) { console.warn('wallet/transactions failed'); }
    return [];
}

async function refreshBankroll() {
    try {
        const r = await fetch(`${API_BASE}/bankroll`);
        if (r.ok) {
            const d = await r.json();
            const el = document.getElementById('housePoolModal');
            if (el) el.textContent = formatUsd(d.house_pool || 0);
        }
    } catch (e) { console.warn('bankroll failed'); }
}

async function apiDeposit(amount, method) {
    const r = await fetch(`${API_BASE}/wallet/deposit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, amount, method })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Deposit failed');
    return d;
}

async function apiWithdraw(amount, method) {
    const r = await fetch(`${API_BASE}/wallet/withdraw`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, amount, method })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Withdraw failed');
    return d;
}

async function openWalletModal(preset) {
    openModal('walletModal');
    // Preset focus
    if (preset === 'deposit') {
        document.getElementById('depositAmount')?.focus();
    } else if (preset === 'withdraw') {
        document.getElementById('withdrawAmount')?.focus();
    }
    await refreshWallet();
    updateWalletQuickStats();
    const txs = await refreshTransactions();
    txCache = txs;
    currentTxFilter = 'all';
    updateTxFilterUI();
    renderTransactions(applyTxFilter(txCache));
    await refreshBankroll();
}

function updateWalletQuickStats(spinResult) {
    const balEl = document.getElementById('walletBalanceModal');
    const houseEl = document.getElementById('housePoolModal');
    if (spinResult && typeof spinResult.wallet_balance !== 'undefined') {
        balEl && (balEl.textContent = formatUsd(spinResult.wallet_balance));
        if (typeof spinResult.house_pool !== 'undefined') {
            houseEl && (houseEl.textContent = formatUsd(spinResult.house_pool));
        }
    } else {
        balEl && (balEl.textContent = formatUsd(balance));
    }
}

function renderTransactions(txs) {
    const el = document.getElementById('txList');
    if (!el) return;
    if (!txs || txs.length === 0) {
        el.innerHTML = '<div class="muted">No transactions yet.</div>';
        return;
    }
    el.innerHTML = txs.slice().reverse().map(tx => {
        const date = new Date((tx.ts || 0) * 1000).toLocaleString();
        const amt = Number(tx.amount || 0);
        const signClass = amt < 0 ? 'negative' : 'positive';
        const kind = (tx.type || '').toUpperCase();
        const desc = tx.method ? `${tx.method}` : (tx.meta && tx.meta.spin_nonce ? `Spin #${tx.meta.spin_nonce}` : '-');
        return `
        <div class="tx-item">
            <div class="tx-kind">${kind}</div>
            <div class="tx-desc">${desc}</div>
            <div class="tx-time">${date}</div>
            <div class="tx-amount ${signClass}">${formatUsd(amt)}</div>
        </div>`;
    }).join('');
}

// Transaction filter logic
let txCache = [];
let currentTxFilter = 'all';
function applyTxFilter(list) {
    if (currentTxFilter === 'all') return list;
    return list.filter(tx => (tx.type || '').toLowerCase() === currentTxFilter);
}
function updateTxFilterUI() {
    const tabs = document.querySelectorAll('#txFilters .filter-btn');
    tabs.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.kind === currentTxFilter);
    });
}
document.addEventListener('click', async (e) => {
    if (e.target && e.target.matches('#txFilters .filter-btn')) {
        currentTxFilter = e.target.dataset.kind || 'all';
        updateTxFilterUI();
        if (txCache.length === 0) txCache = await refreshTransactions();
        renderTransactions(applyTxFilter(txCache));
    }
});

async function onDepositSubmit() {
    if (!sessionId) { alert('Start a session first.'); return; }
    const amount = parseFloat(document.getElementById('depositAmount').value || '0');
    const method = document.getElementById('depositMethod').value;
    if (!amount || amount <= 0) { alert('Enter a valid amount'); return; }
    try {
        const res = await apiDeposit(amount, method);
        balance = Number(res.balance || balance);
        updateDisplay();
        await openWalletModal('deposit');
        track('deposit_completed', { amount, method });
        alert('Deposit successful');
    } catch (e) {
        alert(e.message || 'Deposit failed');
    }
}

async function onWithdrawSubmit() {
    if (!sessionId) { alert('Start a session first.'); return; }
    const amount = parseFloat(document.getElementById('withdrawAmount').value || '0');
    const method = document.getElementById('withdrawMethod').value;
    if (!amount || amount <= 0) { alert('Enter a valid amount'); return; }
    try {
        const res = await apiWithdraw(amount, method);
        balance = Number(res.balance || balance);
        updateDisplay();
        await openWalletModal('withdraw');
        track('withdraw_requested', { amount, method });
        alert('Withdrawal requested');
    } catch (e) {
        alert(e.message || 'Withdraw failed');
    }
}

function disableUIForBackendDown() {
    try {
        const spinBtn = document.getElementById('spinBtn');
        const addBtn = document.getElementById('addFundsBtn');
        const wdBtn = document.getElementById('withdrawBtn');
        spinBtn && (spinBtn.disabled = true);
        addBtn && (addBtn.disabled = true);
        wdBtn && (wdBtn.disabled = true);
    } catch {}
}

// ---- Promo countdown helper ----
function initPromoCountdown(seconds) {
    const el = document.getElementById('promoCountdown');
    if (!el) return;
    let remaining = seconds;
    const fmt = (s) => {
        const h = Math.floor(s / 3600).toString().padStart(2, '0');
        const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
        const sec = Math.floor(s % 60).toString().padStart(2, '0');
        return `${h}:${m}:${sec}`;
    };
    el.textContent = fmt(remaining);
    const timer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
            clearInterval(timer);
            el.textContent = '00:00:00';
            return;
        }
        el.textContent = fmt(remaining);
    }, 1000);
}

// ---- Support chat helpers ----
async function openSupportChat() {
    openModal('supportChatModal');
    await loadSupportHistory();
}

async function loadSupportHistory() {
    try {
        const url = new URL(`${API_BASE}/support/history`, location.origin);
        url.searchParams.set('session_id', sessionId || '');
        const r = await fetch(url);
        if (!r.ok) return;
        const d = await r.json();
        const msgs = d.messages || [];
        if (msgs.length > 0) supportConversationId = msgs[0].conversation_id;
        renderSupportMessages(msgs);
    } catch (e) { /* ignore */ }
}

function renderSupportMessages(msgs) {
    const box = document.getElementById('supportMessages');
    if (!box) return;
    box.innerHTML = '';
    msgs.forEach(m => {
        const item = document.createElement('div');
        item.className = `support-msg ${m.role}`;
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = m.content;
        item.appendChild(bubble);
        box.appendChild(item);
    });
    box.scrollTop = box.scrollHeight;
}

async function sendSupportMessage() {
    const input = document.getElementById('supportInput');
    const text = (input.value || '').trim();
    if (!text || !sessionId) return;
    // Optimistic append user message
    const box = document.getElementById('supportMessages');
    const mine = document.createElement('div');
    mine.className = 'support-msg user';
    const b = document.createElement('div'); b.className = 'bubble'; b.textContent = text; mine.appendChild(b); box.appendChild(mine);
    box.scrollTop = box.scrollHeight;
    input.value = '';
    try {
        const payload = { session_id: sessionId, message: text };
        if (supportConversationId) payload.conversation_id = supportConversationId;
        const r = await fetch(`${API_BASE}/support/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Failed');
        supportConversationId = d.conversation_id || supportConversationId;
        // Append assistant reply
        const item = document.createElement('div'); item.className = 'support-msg assistant';
        const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = d.reply || '';
        item.appendChild(bubble); box.appendChild(item);
        box.scrollTop = box.scrollHeight;
    } catch (e) {
        const err = document.createElement('div'); err.className = 'support-msg assistant';
        const bb = document.createElement('div'); bb.className = 'bubble'; bb.textContent = 'Sorry, support is unavailable right now.';
        err.appendChild(bb); box.appendChild(err); box.scrollTop = box.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('supportSendBtn');
    const input = document.getElementById('supportInput');
    if (btn) btn.addEventListener('click', sendSupportMessage);
    if (input) input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            sendSupportMessage();
        }
    });
});

