# 🎰 Casino Slot Machine - Provably Fair

A complete casino slot game implementation with **provably fair** random number generation, similar to crypto casinos like Stake.com and 1xbet. Features a Flask REST API backend and an animated web frontend.

## 🌟 Features

### Provably Fair System
- **Cryptographically Secure RNG** using HMAC-SHA256
- **Server Seed** (hidden until revealed)
- **Client Seed** (customizable by player)
- **Nonce** (increments with each game)
- Full verifiability of all game outcomes

### Slot Game Features
- 3×5 slot grid with 9 paylines
- 8 unique cosmic symbols with different rarities
- Multiple winning combinations
- Adjustable bet amounts (0.1 - 100)
- Configurable active paylines
- Real-time win calculations

### 🎮 New Enhanced Features
- **🔊 Sound Effects** - Immersive audio using Web Audio API
  - Spinning sounds
  - Reel stop sounds (sequential)
  - Win celebration sounds
  - Big win fanfare
  - Button click feedback
- **🤖 Auto-Spin** - Set it and forget it!
  - Configure 1-1000 auto spins
  - Optional "stop on win" feature
  - Live counter display
- **🎆 Particle Effects** - Beautiful win animations
  - Confetti particles on wins
  - Extra particles for big wins
  - Smooth physics simulation
- **📊 Statistics Tracker** - Track your performance
  - Total spins played
  - Win rate percentage
  - Biggest win amount
  - Net profit/loss
  - Persistent storage (localStorage)
- **📱 Mobile Optimized** - Play anywhere
  - Responsive design
  - Touch-friendly controls
  - Adaptive layouts

### Web Interface
- Smooth slot reel animations
- Real-time balance tracking
- Interactive paytable
- Fairness verification tools
- Cosmic space theme with animated stars
- Sound toggle control

## 📁 Project Structure

```
casino-slot/
├── backend/
│   ├── rng.py              # Provably fair RNG implementation
│   ├── slot_game.py        # Slot machine game logic
│   ├── app.py              # Flask REST API
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── index.html          # Main page
    ├── style.css           # Styles and animations
    └── game.js             # Game logic and API calls
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd casino-slot/backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API server:**
   ```bash
   python app.py
   ```

   The API will start at `http://localhost:5000`

### Frontend Setup

1. **Open the frontend:**
   ```bash
   cd casino-slot/frontend
   ```

2. **Serve the frontend** (choose one):

   **Option A: Using Python's built-in server:**
   ```bash
   python -m http.server 8000
   ```

   **Option B: Using Node.js http-server:**
   ```bash
   npx http-server -p 8000
   ```

   **Option C: Just open the file:**
   ```bash
   # Open index.html directly in your browser
   xdg-open index.html  # Linux
   open index.html      # macOS
   start index.html     # Windows
   ```

3. **Play the game:**
   Navigate to `http://localhost:8000` (or open `index.html` directly)

## 🐳 Deploy with Docker

Requirements: Docker and Docker Compose.

1) Optional environment variables (recommended):

- `ADMIN_TOKEN`: token for admin API access
- `SIGNING_SECRET`: HMAC key if you require signed admin requests
- `SIGNING_REQUIRED_ADMIN=true`: enforce signed admin requests (optional)
- `ALLOWED_ADMIN_IPS`: comma-separated IP allowlist for admin endpoints (optional)

2) Build and start:

```bash
# Ensure the SQLite DB file exists for bind-mount persistence
touch backend/casino.db
docker compose up --build -d
```

3) Open:

- Frontend: http://localhost:8080
- Admin Dashboard: http://localhost:8080/admin.html (use your ADMIN_TOKEN)

4) Architecture

- Nginx serves the static frontend and proxies `/api` to the backend container.
- The frontend calls the API at a relative path (`/api`) to avoid CORS.
- If you serve the frontend elsewhere, set `ALLOWED_ORIGINS` on the backend accordingly.

5) Data persistence

- SQLite DB file (casino.db) is stored under `/app` in the backend container.
- The compose file uses a named volume `backend_data` to persist data across restarts.

6) Stop and cleanup

```bash
docker compose down
```

To remove the persisted data:

```bash
docker volume rm casino-slot_backend_data
```

## � Deploy Frontend on Netlify (with API proxy)

This project includes a Netlify Edge Function that proxies all /api/* requests to a separately hosted backend. This lets the browser call /api on the same origin (no CORS), while the Edge Function forwards to your backend.

1) Host the backend

- Option A: Docker on your VPS
  - Build the backend image from `backend/Dockerfile` and run Gunicorn on port 5000
  - Environment variables (recommended):
    - `ADMIN_TOKEN`: token for admin endpoints
    - `ALLOWED_ADMIN_IPS`: optional comma-separated IP allowlist for admin endpoints
    - `SIGNING_SECRET` + `SIGNING_REQUIRED_ADMIN=true`: require signed admin requests (optional)
- Option B: Use a PaaS (Render, Railway, Fly.io, etc.)
  - Start command: `gunicorn app:app --workers 2 --threads 4 --timeout 60`
  - Expose port 5000

2) Configure Netlify

- The file `netlify.toml` sets the publish directory to `frontend` and attaches the Edge Function
- The Edge Function is at `netlify/edge-functions/proxy.js`
- Set a Netlify environment variable:
  - `BACKEND_ORIGIN` = the full base URL of your backend, e.g. `https://your-backend.onrender.com`

3) Deploy

- Push to your repository and connect it to Netlify, or drag-drop the folder in the Netlify UI
- Netlify will publish the `frontend` folder
- All requests to `/api/*` will be proxied to `BACKEND_ORIGIN`

4) Verify

- Visit your Netlify site (by default `/` redirects to `/index_professional.html`)
- Open the browser console; you should see successful calls to `/api/health` and other endpoints
- Admin dashboard is at `/admin.html` (set and use your `ADMIN_TOKEN`)

Notes

- Because the frontend calls `/api` on the same origin, CORS is not required
- For production, serve the backend over HTTPS and set `ALLOWED_ORIGINS` only if you plan to call it directly from browsers (not needed when using the Netlify proxy)
- SQLite database is persisted on the backend host; back it up if needed

## �🎮 How to Play

1. **Start a New Game** - The game auto-creates a session with provably fair seeds
2. **Set Your Bet** - Choose bet amount per line (0.1 - 100)
3. **Select Active Lines** - Pick 1-9 paylines
4. **Spin!** - Click the SPIN button and watch the reels
5. **Win!** - Match 3+ symbols on a payline to win

## 🔒 Provably Fair Verification

### Understanding the System

The game uses a **provably fair** algorithm that ensures:
- The casino cannot manipulate results after revealing the server seed hash
- Players can verify every single spin was fair
- Complete transparency in the RNG process

### How It Works

1. **Before Playing:**
   - Server generates a secret **Server Seed**
   - Server shows you the **SHA-256 hash** of the server seed
   - You provide or generate a **Client Seed**
   - Both seeds are locked in

2. **During Each Spin:**
   - A **Nonce** (number used once) increments
   - Result = HMAC-SHA256(Server Seed, Client Seed + Nonce)
   - The hash determines reel positions

3. **Verification:**
   - Change your client seed to reveal the server seed
   - Use the revealed server seed to recalculate all previous results
   - Verify they match exactly

### API Endpoints

#### Create New Game
```http
POST /api/game/new
Content-Type: application/json

{
  "client_seed": "optional_custom_seed"
}
```

#### Spin the Slots
```http
POST /api/game/spin/<session_id>
Content-Type: application/json

{
  "bet_amount": 1.0,
  "active_paylines": 9
}
```

#### Change Client Seed (Reveals Server Seed)
```http
POST /api/game/change-seed/<session_id>
Content-Type: application/json

{
  "new_client_seed": "new_seed"
}
```

#### Verify Result
```http
POST /api/verify
Content-Type: application/json

{
  "server_seed": "revealed_seed",
  "client_seed": "your_seed",
  "nonce": 0,
  "expected_positions": [1, 5, 3, 7, 2, ...]
}
```

#### Get Paytable
```http
GET /api/paytable
```

## 💎 Symbol Paytable

| Symbol | Name      | 3× Match | 4× Match | 5× Match |
|--------|-----------|----------|----------|----------|
| �     | Moon      | 5×       | 10×      | 25×      |
| ⭐     | Star      | 5×       | 10×      | 25×      |
| 🪐     | Saturn    | 10×      | 20×      | 50×      |
| �     | Earth     | 10×      | 20×      | 50×      |
| 🌌     | Galaxy    | 15×      | 40×      | 100×     |
| ☄️     | Comet     | 25×      | 75×      | 200×     |
| 🌟     | Supernova | 50×      | 150×     | 500×     |
| 🚀     | Rocket    | 100×     | 500×     | 1000×    | �

## 🧪 Testing the RNG

### Test the RNG directly:
```bash
cd backend
python rng.py
```

### Test the slot game:
```bash
cd backend
python slot_game.py
```

### Example Output:
```
🎰 Casino Slot Machine Demo 🎰

RNG State:
  Server Seed Hash: a1b2c3d4e5f6...
  Client Seed: f6e5d4c3b2a1...

==================================================
           SLOT MACHINE SPIN
==================================================
  🍒 | 🍋 | 💎 | 🍊 | 🔔
  🍇 | 🍇 | 🍇 | ⭐ | 7️⃣
  🔔 | ⭐ | 🍊 | 🍋 | 🍒
==================================================
Bet: $9.00 (9 lines × $1.00)

🎉 WINS (1):
  Line 1: 3× 🍇 (Grape) → $10.00

💰 Total Win: $10.00
💵 Profit: $1.00
==================================================
```

## 📊 Technical Details

### RNG Algorithm
```python
# Simplified pseudocode
message = f"{client_seed}:{nonce}"
hash = HMAC-SHA256(server_seed, message)
random_value = int(hash[:8], 16) / 0xFFFFFFFF
position = int(random_value * reel_strip_length)
```

### Security Features
- Uses Python's `secrets` module for cryptographic randomness
- HMAC-SHA256 for combining seeds (industry standard)
- Server seed hidden until player changes seeds
- Complete audit trail via nonce tracking

### Paylines (Grid Positions)
```
Grid:    Paylines:
0  1  2  3  4     Line 0: [5,6,7,8,9]     (Middle row)
5  6  7  8  9     Line 1: [0,1,2,3,4]     (Top row)
10 11 12 13 14    Line 2: [10,11,12,13,14] (Bottom row)
                  Line 3: [0,6,12,8,4]     (V shape)
                  ... and 5 more
```

## 🔧 Configuration

### Adjust Symbol Weights (rng.py)
```python
SYMBOLS = {
    '🍒': {'weight': 5, 'name': 'Cherry'},  # More common
    '💎': {'weight': 1, 'name': 'Diamond'}, # Rare
}
```

### Modify Payouts (slot_game.py)
```python
PAYOUTS = {
    '7️⃣': {3: 100, 4: 500, 5: 1000},  # Jackpot!
}
```

## 🐛 Troubleshooting

### Backend won't start
- Ensure Python 3.8+ is installed: `python --version`
- Install dependencies: `pip install -r requirements.txt`
- Check if port 5000 is available

### Frontend can't connect to API
- Verify backend is running at `http://localhost:5000`
- Check browser console for CORS errors
- Try accessing `http://localhost:5000/api/health`

### Animations not working
- Use a modern browser (Chrome, Firefox, Safari, Edge)
- Check browser console for JavaScript errors
- Ensure `game.js` is loaded correctly

## 📝 License

This is a demonstration project for educational purposes. Not for commercial gambling use.

## 🎯 Future Enhancements

- [ ] User authentication and persistent balances
- [ ] Leaderboards and statistics
- [ ] Bonus rounds and free spins
- [ ] Progressive jackpots
- [ ] Sound effects and music
- [ ] Mobile app version
- [ ] Cryptocurrency payments
- [ ] Multi-language support

## 🤝 Contributing

Feel free to fork, modify, and use this project as a learning resource!

## ⚠️ Disclaimer

This is a demonstration of provably fair RNG technology for educational purposes. Online gambling may be illegal in your jurisdiction. Always gamble responsibly.

---

**Made with ❤️ for fair gaming**
