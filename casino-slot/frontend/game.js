// API Configuration
const API_BASE = 'http://localhost:5000/api';

// Game State
let sessionId = null;
let balance = 1000;
let isSpinning = false;
let lastResult = null;

// Initialize game on page load
window.addEventListener('DOMContentLoaded', () => {
    newGame();
    updateTotalBet();
    gameStats.updateDisplay();
    initParticles();
    
    // Add event listeners
    document.getElementById('betAmount').addEventListener('change', updateTotalBet);
    document.getElementById('activeLines').addEventListener('change', updateTotalBet);
});

// Create new game session
async function newGame() {
    try {
        const response = await fetch(`${API_BASE}/game/new`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        sessionId = data.session_id;
        
        // Update UI
        document.getElementById('sessionId').textContent = sessionId;
        document.getElementById('serverSeedHash').value = data.server_seed_hash;
        document.getElementById('clientSeed').value = data.client_seed;
        document.getElementById('nonce').value = data.nonce;
        
        // Reset balance
        balance = 1000;
        updateBalance();
        
        console.log('New game created:', data);
    } catch (error) {
        console.error('Error creating game:', error);
        alert('Failed to create game. Is the API running?');
    }
}

// Spin the slot machine
async function spin() {
    if (isSpinning) return;
    
    const betAmount = parseFloat(document.getElementById('betAmount').value);
    const activeLines = parseInt(document.getElementById('activeLines').value);
    const totalBet = betAmount * activeLines;
    
    if (balance < totalBet) {
        alert('Insufficient balance!');
        return;
    }
    
    isSpinning = true;
    document.getElementById('spinBtn').disabled = true;
    document.getElementById('winDisplay').style.display = 'none';
    
    // Play spin sound
    soundManager.playSpinSound();
    
    // Deduct bet
    balance -= totalBet;
    updateBalance();
    
    try {
        // Start spinning animation
        startSpinAnimation();
        
        // Call API
        const response = await fetch(`${API_BASE}/game/spin/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bet_amount: betAmount,
                active_paylines: activeLines
            })
        });
        
        const result = await response.json();
        lastResult = result;
        
        console.log('Spin result:', result);
        
        // Wait for animation
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Stop reels and show result
        stopSpinAnimation(result.grid);
        
        // Update RNG state
        document.getElementById('serverSeedHash').value = result.rng_state.server_seed_hash;
        document.getElementById('clientSeed').value = result.rng_state.client_seed;
        document.getElementById('nonce').value = result.rng_state.nonce;
        
        // Show wins
        if (result.total_win > 0) {
            balance += result.total_win;
            updateBalance(result.total_win);
            showWin(result);
            
            // Play win sound
            if (result.total_win > result.total_bet * 10) {
                soundManager.playBigWinSound();
                createParticles(50);
            } else {
                soundManager.playWinSound(result.total_win);
                createParticles(20);
            }
        } else {
            updateBalance(0);
        }
        
        // Record statistics
        gameStats.recordSpin(result.total_bet, result.total_win);
        
    } catch (error) {
        console.error('Error spinning:', error);
        alert('Spin failed! Refunding bet.');
        balance += totalBet;
        updateBalance();
    } finally {
        isSpinning = false;
        document.getElementById('spinBtn').disabled = false;
    }
}

// Start spinning animation
function startSpinAnimation() {
    const reels = document.querySelectorAll('.reel');
    reels.forEach((reel, index) => {
        reel.classList.add('spinning');
        
        // Randomize symbols during spin
        const interval = setInterval(() => {
            const symbols = reel.querySelectorAll('.symbol');
            const allSymbols = ['�', '⭐', '🪐', '�', '🌌', '☄️', '🌟', '🚀'];
            symbols.forEach(symbol => {
                symbol.textContent = allSymbols[Math.floor(Math.random() * allSymbols.length)];
            });
        }, 100);
        
        reel.dataset.interval = interval;
    });
}

// Stop spinning animation and show result
function stopSpinAnimation(grid) {
    const reels = document.querySelectorAll('.reel');
    
    reels.forEach((reel, colIndex) => {
        // Stop after a delay based on reel position
        setTimeout(() => {
            // Clear interval
            clearInterval(parseInt(reel.dataset.interval));
            
            // Stop spinning
            reel.classList.remove('spinning');
            reel.classList.add('stopping');
            
            // Set final symbols
            const symbols = reel.querySelectorAll('.symbol');
            symbols.forEach((symbol, rowIndex) => {
                symbol.textContent = grid[rowIndex][colIndex];
            });
            
            // Play stop sound
            soundManager.playStopSound(1 + colIndex * 0.1);
            
            // Remove stopping animation
            setTimeout(() => {
                reel.classList.remove('stopping');
            }, 500);
        }, colIndex * 200);
    });
}

// Show win animation
function showWin(result) {
    const winDisplay = document.getElementById('winDisplay');
    const winAmount = document.getElementById('winAmount');
    const winText = document.getElementById('winText');
    
    winAmount.textContent = `$${result.total_win.toFixed(2)}`;
    
    // Create win text
    const winMessages = result.wins.map(win => 
        `${win.count}× ${win.symbol} on Line ${win.payline + 1}`
    ).join(' | ');
    
    winText.textContent = winMessages;
    
    winDisplay.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        winDisplay.style.display = 'none';
    }, 5000);
}

// Update balance display
function updateBalance(lastWin = null) {
    document.getElementById('balance').textContent = `$${balance.toFixed(2)}`;
    
    if (lastWin !== null) {
        const lastWinEl = document.getElementById('lastWin');
        lastWinEl.textContent = `$${lastWin.toFixed(2)}`;
        lastWinEl.style.animation = 'none';
        setTimeout(() => {
            lastWinEl.style.animation = 'winPulse 1s ease-in-out 3';
        }, 10);
    }
}

// Update total bet display
function updateTotalBet() {
    const betAmount = parseFloat(document.getElementById('betAmount').value) || 1.0;
    const activeLines = parseInt(document.getElementById('activeLines').value) || 9;
    const totalBet = betAmount * activeLines;
    
    document.getElementById('totalBet').textContent = `$${totalBet.toFixed(2)}`;
}

// Change bet amount
function changeBet(delta) {
    soundManager.playClickSound();
    const betInput = document.getElementById('betAmount');
    let currentBet = parseFloat(betInput.value);
    currentBet = Math.max(0.1, Math.min(100, currentBet + delta));
    betInput.value = currentBet.toFixed(1);
    updateTotalBet();
}

// Toggle sound
function toggleSound() {
    const enabled = soundManager.toggle();
    const btn = document.getElementById('soundToggle');
    btn.textContent = enabled ? '🔊 ON' : '🔇 OFF';
    soundManager.playClickSound();
}

// Particle system for win effects
let particlesCanvas, particlesCtx, particles = [];

function initParticles() {
    particlesCanvas = document.getElementById('particles');
    particlesCtx = particlesCanvas.getContext('2d');
    particlesCanvas.width = window.innerWidth;
    particlesCanvas.height = window.innerHeight;
    
    window.addEventListener('resize', () => {
        particlesCanvas.width = window.innerWidth;
        particlesCanvas.height = window.innerHeight;
    });
    
    animateParticles();
}

function createParticles(count) {
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    
    for (let i = 0; i < count; i++) {
        particles.push({
            x: centerX,
            y: centerY,
            vx: (Math.random() - 0.5) * 10,
            vy: (Math.random() - 0.5) * 10 - 5,
            life: 1,
            color: `hsl(${Math.random() * 60 + 180}, 100%, 60%)`
        });
    }
}

function animateParticles() {
    particlesCtx.clearRect(0, 0, particlesCanvas.width, particlesCanvas.height);
    
    particles = particles.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.3; // Gravity
        p.life -= 0.02;
        
        if (p.life > 0) {
            particlesCtx.globalAlpha = p.life;
            particlesCtx.fillStyle = p.color;
            particlesCtx.beginPath();
            particlesCtx.arc(p.x, p.y, 3, 0, Math.PI * 2);
            particlesCtx.fill();
            return true;
        }
        return false;
    });
    
    requestAnimationFrame(animateParticles);
}

// Show paytable
async function showPaytable() {
    try {
        const response = await fetch(`${API_BASE}/paytable`);
        const data = await response.json();
        
        let html = '<h3>Symbol Payouts (multiplier × bet)</h3>';
        html += '<table><thead><tr><th>Symbol</th><th>Name</th><th>3×</th><th>4×</th><th>5×</th></tr></thead><tbody>';
        
        for (const [symbol, payoutData] of Object.entries(data.payouts)) {
            const symbolInfo = data.symbols[symbol];
            html += `<tr>
                <td style="font-size: 2em;">${symbol}</td>
                <td>${symbolInfo.name}</td>
                <td>${payoutData[3] || '-'}×</td>
                <td>${payoutData[4] || '-'}×</td>
                <td>${payoutData[5] || '-'}×</td>
            </tr>`;
        }
        
        html += '</tbody></table>';
        html += `<p style="margin-top: 20px;">Total Paylines: ${data.payline_count}</p>`;
        
        document.getElementById('paytableContent').innerHTML = html;
        document.getElementById('paytableModal').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading paytable:', error);
    }
}

// Show verify modal
function showVerifyModal() {
    if (!lastResult) {
        alert('No result to verify yet. Spin first!');
        return;
    }
    
    let html = '<h3>Last Spin Details</h3>';
    html += '<div class="verification-result">';
    html += `<p><strong>Server Seed Hash:</strong><br><code>${lastResult.rng_state.server_seed_hash}</code></p>`;
    html += `<p><strong>Client Seed:</strong><br><code>${lastResult.rng_state.client_seed}</code></p>`;
    html += `<p><strong>Nonces Used:</strong><br><code>${lastResult.nonces.join(', ')}</code></p>`;
    html += `<p><strong>Positions:</strong><br><code>${lastResult.positions.join(', ')}</code></p>`;
    html += '</div>';
    html += '<p style="margin-top: 20px;">To verify this result, you need the server seed (revealed when you change seeds).</p>';
    html += '<p>The positions were generated using HMAC-SHA256 with the seeds and nonces above.</p>';
    
    document.getElementById('verifyContent').innerHTML = html;
    document.getElementById('verifyModal').style.display = 'block';
}

// Show change seed modal
function showChangeSeedModal() {
    document.getElementById('changeSeedModal').style.display = 'block';
}

// Change client seed
async function changeClientSeed() {
    const newSeed = document.getElementById('newClientSeed').value.trim() || null;
    
    try {
        const response = await fetch(`${API_BASE}/game/change-seed/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_client_seed: newSeed })
        });
        
        const data = await response.json();
        
        // Update UI
        document.getElementById('serverSeedHash').value = data.new_server_seed_hash;
        document.getElementById('clientSeed').value = data.new_client_seed;
        document.getElementById('nonce').value = data.nonce_reset;
        
        // Show result
        let html = '<div class="verification-result success">';
        html += '<h3>✓ Seed Changed Successfully</h3>';
        html += `<p><strong>Old Server Seed (revealed):</strong><br><code>${data.old_server_seed}</code></p>`;
        html += `<p><strong>Old Server Seed Hash:</strong><br><code>${data.old_server_seed_hash}</code></p>`;
        html += '<p>You can now verify all previous spins using the revealed server seed!</p>';
        html += `<p><strong>New Server Seed Hash:</strong><br><code>${data.new_server_seed_hash}</code></p>`;
        html += `<p><strong>New Client Seed:</strong><br><code>${data.new_client_seed}</code></p>`;
        html += '</div>';
        
        document.getElementById('changeSeedResult').innerHTML = html;
        document.getElementById('newClientSeed').value = '';
        
    } catch (error) {
        console.error('Error changing seed:', error);
        alert('Failed to change seed');
    }
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
