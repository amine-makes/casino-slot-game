// Game Statistics Tracker
class GameStats {
    constructor() {
        this.load();
    }
    
    load() {
        const saved = localStorage.getItem('cosmicFortunesStats');
        if (saved) {
            const data = JSON.parse(saved);
            this.totalSpins = data.totalSpins || 0;
            this.totalWagered = data.totalWagered || 0;
            this.totalWon = data.totalWon || 0;
            this.biggestWin = data.biggestWin || 0;
            this.winCount = data.winCount || 0;
            this.sessionStart = data.sessionStart || Date.now();
        } else {
            this.reset();
        }
    }
    
    save() {
        localStorage.setItem('cosmicFortunesStats', JSON.stringify({
            totalSpins: this.totalSpins,
            totalWagered: this.totalWagered,
            totalWon: this.totalWon,
            biggestWin: this.biggestWin,
            winCount: this.winCount,
            sessionStart: this.sessionStart
        }));
    }
    
    recordSpin(bet, win) {
        this.totalSpins++;
        this.totalWagered += bet;
        
        if (win > 0) {
            this.totalWon += win;
            this.winCount++;
            if (win > this.biggestWin) {
                this.biggestWin = win;
            }
        }
        
        this.save();
        this.updateDisplay();
    }
    
    updateDisplay() {
        const winRate = this.totalSpins > 0 ? (this.winCount / this.totalSpins * 100).toFixed(1) : 0;
        const netProfit = this.totalWon - this.totalWagered;
        
        document.getElementById('totalSpins').textContent = this.totalSpins;
        document.getElementById('winRate').textContent = `${winRate}%`;
        document.getElementById('biggestWin').textContent = `$${this.biggestWin.toFixed(2)}`;
        document.getElementById('netProfit').textContent = `$${netProfit.toFixed(2)}`;
        document.getElementById('netProfit').style.color = netProfit >= 0 ? '#4ade80' : '#ff6b6b';
    }
    
    reset() {
        this.totalSpins = 0;
        this.totalWagered = 0;
        this.totalWon = 0;
        this.biggestWin = 0;
        this.winCount = 0;
        this.sessionStart = Date.now();
        this.save();
        this.updateDisplay();
    }
}

// Create global stats tracker
const gameStats = new GameStats();

// Auto-spin functionality
class AutoSpin {
    constructor() {
        this.isRunning = false;
        this.remaining = 0;
        this.stopOnWin = false;
    }
    
    start(count, stopOnWin = false) {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.remaining = count;
        this.stopOnWin = stopOnWin;
        
        this.updateDisplay();
        this.runNext();
    }
    
    stop() {
        this.isRunning = false;
        this.remaining = 0;
        this.updateDisplay();
    }
    
    async runNext() {
        if (!this.isRunning || this.remaining <= 0) {
            this.stop();
            return;
        }
        
        // Trigger spin
        await spin();
        
        // Check if we should stop
        if (this.stopOnWin && lastResult && lastResult.total_win > 0) {
            this.stop();
            return;
        }
        
        this.remaining--;
        this.updateDisplay();
        
        // Wait a bit before next spin
        if (this.isRunning && this.remaining > 0) {
            setTimeout(() => this.runNext(), 1500);
        } else {
            this.stop();
        }
    }
    
    updateDisplay() {
        const autoSpinBtn = document.getElementById('autoSpinBtn');
        if (this.isRunning) {
            autoSpinBtn.textContent = `Stop (${this.remaining} left)`;
            autoSpinBtn.classList.add('auto-active');
            document.getElementById('spinBtn').disabled = true;
        } else {
            autoSpinBtn.textContent = 'Auto Spin';
            autoSpinBtn.classList.remove('auto-active');
            if (!isSpinning) {
                document.getElementById('spinBtn').disabled = false;
            }
        }
    }
}

// Create global auto-spin manager
const autoSpinner = new AutoSpin();

// Show auto-spin modal
function showAutoSpinModal() {
    soundManager.playClickSound();
    document.getElementById('autoSpinModal').style.display = 'block';
}

// Start auto-spin
function startAutoSpin() {
    const count = parseInt(document.getElementById('autoSpinCount').value);
    const stopOnWin = document.getElementById('stopOnWin').checked;
    
    if (count < 1 || count > 1000) {
        alert('Please enter a number between 1 and 1000');
        return;
    }
    
    closeModal('autoSpinModal');
    autoSpinner.start(count, stopOnWin);
}

// Stop auto-spin
function stopAutoSpin() {
    soundManager.playClickSound();
    autoSpinner.stop();
}

// Reset statistics
function resetStats() {
    if (confirm('Are you sure you want to reset all statistics?')) {
        gameStats.reset();
        soundManager.playClickSound();
    }
}
