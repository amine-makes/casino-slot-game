# 🎰 Casino Slot Machine - System Architecture

## 📊 System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER / PLAYER                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Opens browser
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (HTML/CSS/JS)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Animated slot reels (3×5 grid)                        │  │
│  │  • Balance display & controls                            │  │
│  │  • Bet settings & payline selection                      │  │
│  │  • Win animations                                        │  │
│  │  • Provably fair verification UI                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/JSON (REST API)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK API SERVER (app.py)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                              │  │
│  │  • POST /api/game/new           - Create game            │  │
│  │  • POST /api/game/spin/<id>     - Spin slots             │  │
│  │  • POST /api/game/change-seed   - Change seed            │  │
│  │  • POST /api/verify             - Verify result          │  │
│  │  • GET  /api/paytable           - Get payouts            │  │
│  │  • GET  /api/game/state/<id>    - Get game state         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Uses
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SLOT GAME ENGINE (slot_game.py)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Features:                                               │  │
│  │  • Symbol definitions (8 types)                          │  │
│  │  • Payout table (3×, 4×, 5× multipliers)                 │  │
│  │  • 9 payline patterns                                    │  │
│  │  • Win calculation logic                                 │  │
│  │  • Result formatting                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Uses
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PROVABLY FAIR RNG (rng.py)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Cryptographic Components:                               │  │
│  │  • Server Seed (secret)                                  │  │
│  │  • Client Seed (player controlled)                       │  │
│  │  • Nonce (increments each use)                           │  │
│  │  • HMAC-SHA256 hashing                                   │  │
│  │  • Verification system                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Game Flow Sequence

```
┌──────┐      ┌──────────┐      ┌────────┐      ┌──────┐
│Client│      │ Frontend │      │  API   │      │  RNG │
└──┬───┘      └────┬─────┘      └───┬────┘      └───┬──┘
   │               │                 │               │
   │ 1. Load Page  │                 │               │
   │──────────────>│                 │               │
   │               │                 │               │
   │               │ 2. Create Game  │               │
   │               │────────────────>│               │
   │               │                 │ 3. Generate   │
   │               │                 │    Seeds      │
   │               │                 │──────────────>│
   │               │                 │               │
   │               │                 │ 4. Return Hash│
   │               │                 │<──────────────│
   │               │ 5. Game Data    │               │
   │               │<────────────────│               │
   │               │                 │               │
   │ 6. Show Info  │                 │               │
   │<──────────────│                 │               │
   │               │                 │               │
   │ 7. Click SPIN │                 │               │
   │──────────────>│                 │               │
   │               │ 8. Spin Request │               │
   │               │────────────────>│               │
   │               │                 │ 9. Generate   │
   │               │                 │    Random Nos │
   │               │                 │──────────────>│
   │               │                 │               │
   │               │                 │ 10. Positions │
   │               │                 │<──────────────│
   │               │                 │               │
   │               │                 │ 11. Calculate │
   │               │                 │     Wins      │
   │               │                 │               │
   │               │ 12. Result +    │               │
   │               │     Wins        │               │
   │               │<────────────────│               │
   │               │                 │               │
   │ 13. Animate   │                 │               │
   │    & Show     │                 │               │
   │<──────────────│                 │               │
   │               │                 │               │
```

## 🔐 Provably Fair Process

```
┌─────────────────────────────────────────────────────────────────┐
│                      BEFORE PLAYING                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Server generates random Server Seed                         │
│     ServerSeed = "a1b2c3d4e5f6..."  (kept secret)               │
│                                                                  │
│  2. Server shows SHA-256 hash of Server Seed                    │
│     ServerSeedHash = SHA256(ServerSeed)                          │
│     = "9f86d081884c7d659a2feaa0c55ad015..."                     │
│     ✓ Player sees this BEFORE any spins                         │
│                                                                  │
│  3. Player provides or generates Client Seed                    │
│     ClientSeed = "player_custom_seed_123"                        │
│     ✓ Player can change this anytime                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      DURING EACH SPIN                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Nonce starts at 0, increments for each random number        │
│                                                                  │
│  2. For each of 15 reel positions:                              │
│                                                                  │
│     Message = ClientSeed + ":" + Nonce                           │
│     Hash = HMAC-SHA256(ServerSeed, Message)                      │
│     RandomValue = First 32 bits of Hash / 0xFFFFFFFF             │
│     Position = RandomValue × ReelStripLength                     │
│                                                                  │
│     Example:                                                     │
│     ┌────────────────────────────────────────────────────┐      │
│     │ Nonce 0:                                           │      │
│     │ Hash = HMAC("a1b2...", "player_seed:0")            │      │
│     │      = "7f3c9e2a..."                               │      │
│     │ Int  = 0x7f3c9e2a = 2134638122                     │      │
│     │ Norm = 2134638122 / 4294967295 = 0.497            │      │
│     │ Pos  = 0.497 × 25 = 12                             │      │
│     └────────────────────────────────────────────────────┘      │
│                                                                  │
│  3. Result is deterministic (same seeds = same result)           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        VERIFICATION                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Player changes Client Seed                                  │
│     → Server REVEALS the old Server Seed                        │
│                                                                  │
│  2. Player verifies:                                            │
│     SHA256(RevealedServerSeed) == ServerSeedHash                 │
│     ✓ Proves server didn't change the seed                      │
│                                                                  │
│  3. Player recalculates all past spins:                         │
│     For each spin (nonce 0, 1, 2, ...):                         │
│       RecalculatedHash = HMAC(RevealedSeed, ClientSeed:Nonce)   │
│       RecalculatedPosition = ...                                │
│                                                                  │
│  4. Compare recalculated vs actual results                      │
│     ✓ If match → Game was fair!                                │
│     ✗ If mismatch → Cheating detected!                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🎲 Reel Position Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                     GRID LAYOUT (3 rows × 5 reels)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│      Reel 1   Reel 2   Reel 3   Reel 4   Reel 5                │
│     ┌──────┬──────┬──────┬──────┬──────┐                       │
│ Row │      │      │      │      │      │                       │
│  1  │  0   │  1   │  2   │  3   │  4   │  ← Top Row           │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│ Row │      │      │      │      │      │                       │
│  2  │  5   │  6   │  7   │  8   │  9   │  ← Middle Row        │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│ Row │      │      │      │      │      │                       │
│  3  │  10  │  11  │  12  │  13  │  14  │  ← Bottom Row        │
│     └──────┴──────┴──────┴──────┴──────┘                       │
│                                                                  │
│  RNG generates 15 random positions (one for each cell)          │
│  Each position maps to a symbol in the reel strip               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      PAYLINE EXAMPLES                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Line 0: Middle Row [5, 6, 7, 8, 9]                             │
│     ┌──────┬──────┬──────┬──────┬──────┐                       │
│     │      │      │      │      │      │                       │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │  ●   │  ●   │  ●   │  ●   │  ●   │ ←── Winning line     │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │      │      │      │      │      │                       │
│     └──────┴──────┴──────┴──────┴──────┘                       │
│                                                                  │
│  Line 3: V-Shape [0, 6, 12, 8, 4]                               │
│     ┌──────┬──────┬──────┬──────┬──────┐                       │
│     │  ●   │      │      │      │  ●   │                       │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │      │  ●   │      │  ●   │      │                       │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │      │      │  ●   │      │      │                       │
│     └──────┴──────┴──────┴──────┴──────┘                       │
│                                                                  │
│  Line 6: Bottom Zigzag [5, 11, 7, 13, 9]                        │
│     ┌──────┬──────┬──────┬──────┬──────┐                       │
│     │      │      │      │      │      │                       │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │  ●   │      │  ●   │      │  ●   │                       │
│     ├──────┼──────┼──────┼──────┼──────┤                       │
│     │      │  ●   │      │  ●   │      │                       │
│     └──────┴──────┴──────┴──────┴──────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Symbol Distribution & RTP

```
┌─────────────────────────────────────────────────────────────────┐
│                      REEL STRIP COMPOSITION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Total symbols in reel strip: 25                                │
│                                                                  │
│  Symbol  │ Weight │ Count │ Probability │ Payout (5×)           │
│  ────────┼────────┼───────┼─────────────┼────────────           │
│  🍒      │   5    │   5   │   20.0%     │   25×                 │
│  🍋      │   5    │   5   │   20.0%     │   25×                 │
│  🍊      │   4    │   4   │   16.0%     │   50×                 │
│  🍇      │   4    │   4   │   16.0%     │   50×                 │
│  🔔      │   3    │   3   │   12.0%     │  100×                 │
│  ⭐      │   2    │   2   │    8.0%     │  200×                 │
│  💎      │   1    │   1   │    4.0%     │  500×                 │
│  7️⃣      │   1    │   1   │    4.0%     │ 1000× (JACKPOT!)      │
│                                                                  │
│  Note: Probability of specific 5-symbol combination:            │
│  P(5× Cherry) = (0.20)^5 = 0.032% per payline                   │
│  P(5× Seven)  = (0.04)^5 = 0.0000001024% per payline 💎         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🏗️ Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  • HTML5           - Structure                                  │
│  • CSS3            - Styling & animations                       │
│  • JavaScript ES6  - Logic & API calls                          │
│  • Fetch API       - HTTP requests                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
├─────────────────────────────────────────────────────────────────┤
│  • Python 3.8+     - Core language                              │
│  • Flask 3.0       - Web framework                              │
│  • Flask-CORS      - Cross-origin support                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       CRYPTOGRAPHY                               │
├─────────────────────────────────────────────────────────────────┤
│  • HMAC-SHA256     - Hash-based message authentication          │
│  • secrets module  - Cryptographically secure random            │
│  • hashlib         - SHA-256 hashing                            │
└─────────────────────────────────────────────────────────────────┘
```

---
**End of Architecture Documentation**
