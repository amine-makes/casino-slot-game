// Sound Effects Manager using Web Audio API
class SoundManager {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.volume = 0.3;
        this.initAudio();
    }
    
    initAudio() {
        // Create audio context on first user interaction
        document.addEventListener('click', () => {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
        }, { once: true });
    }
    
    // Play a tone with specific frequency and duration
    playTone(frequency, duration, type = 'sine') {
        if (!this.enabled || !this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.frequency.value = frequency;
        oscillator.type = type;
        
        gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }
    
    // Spinning sound
    playSpinSound() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.type = 'sawtooth';
        oscillator.frequency.setValueAtTime(100, now);
        oscillator.frequency.exponentialRampToValueAtTime(200, now + 0.5);
        
        gainNode.gain.setValueAtTime(this.volume * 0.5, now);
        gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
        
        oscillator.start(now);
        oscillator.stop(now + 0.5);
    }
    
    // Reel stop sound
    playStopSound(pitch = 1) {
        this.playTone(200 * pitch, 0.1, 'square');
    }
    
    // Win sound
    playWinSound(amount) {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Play a musical chord based on win amount
        const baseFreq = amount > 100 ? 523.25 : amount > 50 ? 440 : 349.23; // C5, A4, or F4
        
        [0, 0.1, 0.2].forEach((delay, i) => {
            const freq = baseFreq * [1, 1.25, 1.5][i]; // Major chord
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = freq;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(this.volume * 0.6, now + delay);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + delay + 0.8);
            
            oscillator.start(now + delay);
            oscillator.stop(now + delay + 0.8);
        });
    }
    
    // Big win sound
    playBigWinSound() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Ascending arpeggio
        [261.63, 329.63, 392, 523.25, 659.25].forEach((freq, i) => {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = freq;
            oscillator.type = 'sine';
            
            const time = now + (i * 0.1);
            gainNode.gain.setValueAtTime(this.volume, time);
            gainNode.gain.exponentialRampToValueAtTime(0.01, time + 0.3);
            
            oscillator.start(time);
            oscillator.stop(time + 0.3);
        });
    }
    
    // Button click sound
    playClickSound() {
        this.playTone(800, 0.05, 'square');
    }
    
    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
    
    setVolume(vol) {
        this.volume = Math.max(0, Math.min(1, vol));
    }
}

// Create global sound manager
const soundManager = new SoundManager();
