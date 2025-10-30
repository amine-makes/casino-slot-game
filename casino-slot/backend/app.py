"""
Flask API for Casino Slot Game
Provides endpoints for gameplay, RNG verification, and game state
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
import secrets
from threading import Lock
from time import time
from slot_game import SlotGame
from rng import ProvablyFairRNG
import sqlite3
import json
import os
import hmac
import hashlib
try:
    import requests  # Optional; used for AI support chat
except Exception:  # pragma: no cover - optional dependency
    requests = None

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Security: configurable CORS origins (comma-separated). Default to '*' for local dev.
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')  # Optional admin token for protected endpoints
ALLOWED_ADMIN_IPS = [ip.strip() for ip in os.environ.get('ALLOWED_ADMIN_IPS', '').split(',') if ip.strip()]
SIGNING_SECRET = os.environ.get('SIGNING_SECRET')  # Optional HMAC secret
SIGNING_REQUIRED_ADMIN = os.environ.get('SIGNING_REQUIRED_ADMIN', 'false').lower() in ('1','true','yes')
# AI support chat configuration (OpenAI-compatible API; works with DeepSeek or local vLLM endpoints)
AI_API_BASE = os.environ.get('AI_API_BASE')  # e.g., https://api.deepseek.com or http://localhost:8000
AI_API_KEY = os.environ.get('AI_API_KEY')
AI_MODEL = os.environ.get('AI_MODEL', 'deepseek-chat')
if ALLOWED_ORIGINS == '*':
    CORS(app)
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(',') if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

# Limit max request size (1 MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

# Store active games (in production, use Redis or database)
games = {}

# --- SQLite persistence (replaces in-memory for wallets/transactions/bankroll) ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'casino.db')
_lock = Lock()

# Simple in-memory rate limiting per IP/category
_rate = {}

def _client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'

def _check_rate(category: str, limit: int, window_sec: int = 60):
    now = int(time())
    ip = _client_ip()
    key = (ip, category)
    slot = _rate.get(key)
    if not slot or now >= slot['reset']:
        _rate[key] = {'count': 1, 'reset': now + window_sec}
        return True, _rate[key]['reset']
    if slot['count'] >= limit:
        return False, slot['reset']
    slot['count'] += 1
    return True, slot['reset']


def _require_admin():
    """Simple admin auth using a bearer token or X-Admin-Token header.
    Returns (ok: bool, error_response: tuple|None)
    """
    # If no ADMIN_TOKEN configured, deny by default
    if not ADMIN_TOKEN:
        return False, (jsonify({'error': 'Admin token not configured'}), 403)
    # Optional IP allowlist
    admin_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ALLOWED_ADMIN_IPS and admin_ip not in ALLOWED_ADMIN_IPS:
        return False, (jsonify({'error': 'Admin access not allowed from this IP'}), 403)
    # Accept either Authorization: Bearer <token> or X-Admin-Token header
    auth = request.headers.get('Authorization', '')
    token = None
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1].strip()
    if not token:
        token = request.headers.get('X-Admin-Token')
    if token != ADMIN_TOKEN:
        return False, (jsonify({'error': 'Unauthorized'}), 401)
    # Basic rate limit for admin endpoints
    ok, reset = _check_rate('admin', limit=120, window_sec=60)
    if not ok:
        return False, (jsonify({'error': 'Too many admin requests', 'retry_after': reset - int(time())}), 429)
    return True, None


def _verify_signature_if_required(for_admin: bool = False):
    """Optional HMAC verification for requests.
    Uses headers: X-Timestamp (epoch seconds) and X-Signature (hex of HMAC-SHA256 over method|path|body|timestamp).
    Only enforced for admin endpoints if SIGNING_REQUIRED_ADMIN is True and SIGNING_SECRET is set.
    Returns (ok: bool, error_response: tuple|None).
    """
    if for_admin:
        if not SIGNING_REQUIRED_ADMIN:
            return True, None
        if not SIGNING_SECRET:
            return False, (jsonify({'error': 'Signing required but secret not configured'}), 500)
    else:
        # Not enforcing for non-admin paths by default
        return True, None

    try:
        ts_hdr = request.headers.get('X-Timestamp')
        sig_hdr = request.headers.get('X-Signature')
        if not ts_hdr or not sig_hdr:
            return False, (jsonify({'error': 'Missing signature headers'}), 401)
        ts = int(ts_hdr)
        now = int(time())
        if abs(now - ts) > 300:
            return False, (jsonify({'error': 'Stale request'}), 401)
        body = request.get_data(as_text=True) or ''
        msg = f"{request.method}\n{request.path}\n{body}\n{ts}"
        mac = hmac.new(SIGNING_SECRET.encode(), msg.encode(), digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, sig_hdr):
            return False, (jsonify({'error': 'Invalid signature'}), 401)
        return True, None
    except Exception:
        return False, (jsonify({'error': 'Signature verification error'}), 401)


def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Improve durability/concurrency defaults
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn


def _init_db():
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_ts INTEGER NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                session_id TEXT PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0,
                updated_ts INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                method TEXT,
                balance_after REAL NOT NULL,
                meta TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bankroll (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                ts INTEGER NOT NULL,
                name TEXT NOT NULL,
                props TEXT,
                ua TEXT,
                ip TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                session_id TEXT,
                ts INTEGER NOT NULL,
                request_hash TEXT,
                response TEXT
            )
            """
        )
        # Support chat messages (by conversation)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                session_id TEXT,
                ts INTEGER NOT NULL,
                role TEXT NOT NULL,          -- user | assistant | admin
                content TEXT NOT NULL
            )
            """
        )
        # Helpful indices
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_session_ts ON transactions(session_id, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_session_ts ON events(session_id, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_name_ts ON events(name, ts)")
        # Ensure bankroll row exists
        cur.execute("INSERT OR IGNORE INTO bankroll(key, value) VALUES('house_pool', 0.0)")
        conn.commit()


_init_db()



def _ensure_wallet(session_id: str):
    now = int(time())
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO sessions(session_id, created_ts) VALUES(?, ?)", (session_id, now))
        cur.execute("INSERT OR IGNORE INTO wallets(session_id, balance, updated_ts) VALUES(?, 0.0, ?)", (session_id, now))
        conn.commit()


def _log_tx(session_id: str, tx_type: str, amount: float, method: str|None=None, meta: dict|None=None):
    tx_id = secrets.token_hex(8)
    ts_now = int(time())
    meta_txt = json.dumps(meta or {})
    with _db() as conn:
        cur = conn.cursor()
        # Read current balance to record balance_after in tx
        cur.execute("SELECT balance FROM wallets WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        balance_after = float(row['balance']) if row else 0.0
        cur.execute(
            """
            INSERT INTO transactions(id, session_id, ts, type, amount, method, balance_after, meta)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tx_id, session_id, ts_now, tx_type, round(float(amount), 2), method, round(balance_after, 2), meta_txt)
        )
        conn.commit()
    return {
        'id': tx_id,
        'ts': ts_now,
        'type': tx_type,
        'amount': round(float(amount), 2),
        'method': method,
        'balance_after': round(balance_after, 2),
        'meta': meta or {}
    }


def _idem_lookup(key: str):
    if not key:
        return None
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT response FROM idempotency_keys WHERE key=?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row['response'])
        except Exception:
            return None


def _idem_store(key: str, category: str, session_id: str|None, response: dict):
    if not key:
        return
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO idempotency_keys(key, category, session_id, ts, request_hash, response)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (key, category, session_id, int(time()), None, json.dumps(response))
        )
        conn.commit()


def get_or_create_game(session_id: str) -> SlotGame:
    """Get existing game or create new one for session"""
    if session_id not in games:
        games[session_id] = SlotGame(ProvablyFairRNG())
    return games[session_id]


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'casino-slot-api'})


@app.route('/api/game/new', methods=['POST'])
def new_game():
    # Rate limit session creation by IP
    ok, reset = _check_rate('new_game', limit=30, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many requests', 'retry_after': reset - int(time())}), 429
    """
    Create a new game session with fresh RNG seeds.
    
    Request body (optional):
        {
            "client_seed": "custom_client_seed"  // Optional
        }
    
    Returns:
        {
            "session_id": "...",
            "server_seed_hash": "...",
            "client_seed": "...",
            "nonce": 0
        }
    """
    session_id = secrets.token_hex(16)
    
    # Get custom client seed if provided
    data = request.get_json() or {}
    client_seed = data.get('client_seed')
    
    # Create new RNG and game
    rng = ProvablyFairRNG(client_seed=client_seed)
    game = SlotGame()
    game.rng = rng
    games[session_id] = game
    # Initialize empty wallet (no demo seeding)
    _ensure_wallet(session_id)
    
    return jsonify({
        'session_id': session_id,
        **game.rng.get_game_state()
    })


@app.route('/api/game/state/<session_id>', methods=['GET'])
def get_game_state(session_id: str):
    """
    Get current game state.
    
    Returns:
        {
            "server_seed_hash": "...",
            "client_seed": "...",
            "nonce": 123,
            "last_result": {...}  // Last spin result if available
        }
    """
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[session_id]
    state = game.rng.get_game_state()
    
    if game.last_spin_result:
        state['last_result'] = game.last_spin_result
    
    return jsonify(state)


@app.route('/api/game/spin/<session_id>', methods=['POST'])
def spin(session_id: str):
    # Rate limit spins per IP
    ok, reset = _check_rate('spin', limit=60, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many spin requests', 'retry_after': reset - int(time())}), 429
    """
    Spin the slot machine.
    
    Request body:
        {
            "bet_amount": 1.0,       // Bet per payline (default: 1.0)
            "active_paylines": 9     // Number of active paylines (default: all)
        }
    
    Returns:
        {
            "grid": [[...], [...], [...]],  // 3x5 grid of symbols
            "bet_amount": 1.0,
            "total_bet": 9.0,
            "active_paylines": 9,
            "wins": [...],
            "total_win": 15.0,
            "profit": 6.0,
            "rng_state": {...},
            "positions": [...],      // For verification
            "nonces": [...]          // For verification
        }
    """
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[session_id]
    data = request.get_json() or {}
    idem_key = request.headers.get('Idempotency-Key') or data.get('idempotency_key')
    cached = _idem_lookup(idem_key)
    if cached:
        return jsonify(cached)
    
    bet_amount = data.get('bet_amount', 1.0)
    active_paylines = data.get('active_paylines')
    
    # Validate bet amount (total wager from frontend, after lot multiplier)
    if bet_amount <= 0 or bet_amount > 10000:
        return jsonify({'error': 'Invalid bet amount (0.01 - 10000)'}), 400

    # Wallet/bankroll handling
    _ensure_wallet(session_id)
    with _lock, _db() as conn:
        cur = conn.cursor()
        # Acquire write lock early
        cur.execute('BEGIN IMMEDIATE')
        # Fetch wallet balance
        cur.execute("SELECT balance FROM wallets WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        player_balance = float(row['balance']) if row else 0.0
        if player_balance < bet_amount:
            return jsonify({'error': 'Insufficient wallet balance'}), 402

        # Mirror game balance to wallet for internal check
        game.balance = player_balance

        # Perform spin (pure function against RNG/game state)
        result = game.spin(bet_amount=bet_amount)
        total_win = float(result.get('total_win', 0.0))

        # Settle: wallet and bankroll
        new_balance = round(player_balance - bet_amount + total_win, 2)
        now_ts = int(time())
        cur.execute("UPDATE wallets SET balance=?, updated_ts=? WHERE session_id=?", (new_balance, now_ts, session_id))

        # Update bankroll house_pool
        cur.execute("SELECT value FROM bankroll WHERE key='house_pool'")
        r = cur.fetchone()
        house_pool = float(r['value']) if r else 0.0
        house_pool = round(house_pool + bet_amount - total_win, 2)
        cur.execute("UPDATE bankroll SET value=? WHERE key='house_pool'", (house_pool,))
        conn.commit()

        # Log transactions reflecting post-update balances
        _log_tx(session_id, 'bet', -bet_amount, meta={'spin_nonce': result.get('nonce')})
        if total_win > 0:
            _log_tx(session_id, 'payout', total_win, meta={'wins': result.get('wins', [])})

        response = {
            **result,
            'bet_amount': bet_amount,
            'total_bet': bet_amount,
            'active_paylines': active_paylines or len(SlotGame.PAYLINES),
            'profit': round(total_win - bet_amount, 2),
            'wallet_balance': new_balance,
            'house_pool': house_pool
        }
        # Store idempotent response if key provided
        _idem_store(idem_key, 'spin', session_id, response)
    
    return jsonify(response)


@app.route('/api/game/change-seed/<session_id>', methods=['POST'])
def change_client_seed(session_id: str):
    """
    Change client seed (reveals current server seed).
    
    Request body:
        {
            "new_client_seed": "custom_seed"  // Optional
        }
    
    Returns:
        {
            "old_server_seed": "...",         // Revealed for verification
            "old_server_seed_hash": "...",
            "new_server_seed_hash": "...",
            "new_client_seed": "...",
            "nonce_reset": 0
        }
    """
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[session_id]
    data = request.get_json() or {}
    
    # Save old seeds for verification
    old_server_seed = game.rng.reveal_server_seed()
    old_server_seed_hash = game.rng.get_server_seed_hash()
    
    # Create new RNG with new seeds
    new_client_seed = data.get('new_client_seed')
    new_rng = ProvablyFairRNG(client_seed=new_client_seed)
    
    # Replace RNG in game
    game.rng = new_rng
    
    return jsonify({
        'old_server_seed': old_server_seed,
        'old_server_seed_hash': old_server_seed_hash,
        'new_server_seed_hash': new_rng.get_server_seed_hash(),
        'new_client_seed': new_rng.client_seed,
        'nonce_reset': new_rng.nonce
    })


@app.route('/api/verify', methods=['POST'])
def verify_result():
    """
    Verify a previous game result.
    
    Request body:
        {
            "server_seed": "...",
            "client_seed": "...",
            "nonce": 123,
            "expected_positions": [...]
        }
    
    Returns:
        {
            "valid": true/false,
            "regenerated_positions": [...],
            "message": "..."
        }
    """
    data = request.get_json()
    
    required = ['server_seed', 'client_seed', 'nonce', 'expected_positions']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Create temporary RNG with provided seeds
    temp_rng = ProvablyFairRNG(
        server_seed=data['server_seed'],
        client_seed=data['client_seed']
    )
    temp_rng.nonce = data['nonce']
    
    # Regenerate the positions
    reel_count = len(data['expected_positions'])
    regenerated_positions, _ = temp_rng.generate_multiple_ints(
        reel_count, 0, 24  # Assuming 25 symbols in reel strip
    )
    
    # Compare
    valid = regenerated_positions == data['expected_positions']
    
    return jsonify({
        'valid': valid,
        'regenerated_positions': regenerated_positions,
        'expected_positions': data['expected_positions'],
        'message': 'Result verified successfully!' if valid else 'Verification failed!'
    })


@app.route('/api/paytable', methods=['GET'])
def get_paytable():
    """
    Get slot machine paytable information.
    
    Returns:
        {
            "symbols": {...},
            "payouts": {...},
            "paylines": [...]
        }
    """
    return jsonify({
        'symbols': SlotGame.SYMBOLS,
        'payouts': SlotGame.PAYOUTS,
        'paylines': SlotGame.PAYLINES,
        'payline_count': len(SlotGame.PAYLINES)
    })


# ---------------- Support Chat (AI-assisted) ----------------

def _ai_enabled():
    return bool(AI_API_BASE and AI_API_KEY and AI_MODEL and requests)

def _call_ai(messages: list[dict]) -> str:
    """Call an OpenAI-compatible Chat Completions API and return the assistant text.
    messages: [{role: 'system'|'user'|'assistant', content: '...'}]
    """
    url = f"{AI_API_BASE.rstrip('/')}/v1/chat/completions"
    headers = {
        'Authorization': f"Bearer {AI_API_KEY}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': AI_MODEL,
        'messages': messages,
        'temperature': 0.3,
        'stream': False,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code != 200:
            return "I'm having trouble reaching support AI right now. A human will follow up."
        data = resp.json()
        # OpenAI-compatible format
        content = data.get('choices', [{}])[0].get('message', {}).get('content')
        if not content:
            return "Support AI returned an empty response."
        return content.strip()
    except Exception:
        return "Support AI is temporarily unavailable. Please try again later."


def _save_support_message(conversation_id: str, session_id: str|None, role: str, content: str):
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO support_messages(id, conversation_id, session_id, ts, role, content)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (secrets.token_hex(8), conversation_id, session_id, int(time()), role, content[:8000])
        )
        conn.commit()


@app.route('/api/support/chat', methods=['POST'])
def support_chat():
    """User support chat endpoint.
    Body: { session_id, message, conversation_id? }
    Returns: { conversation_id, reply }
    """
    ok, reset = _check_rate('support', limit=30, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many requests', 'retry_after': reset - int(time())}), 429
    data = request.get_json() or {}
    session_id = data.get('session_id')
    message = (data.get('message') or '').strip()
    conversation_id = data.get('conversation_id') or secrets.token_hex(8)
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    # Ensure session exists in DB (decoupled from in-memory game state)
    _ensure_wallet(session_id)
    if not message:
        return jsonify({'error': 'Message required'}), 400
    # Persist user message
    _save_support_message(conversation_id, session_id, 'user', message)
    # Build context: last 10 messages for this conversation
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role, content FROM support_messages WHERE conversation_id=? ORDER BY ts ASC LIMIT 20",
            (conversation_id,)
        )
        rows = cur.fetchall()
        msgs = [{'role': r['role'], 'content': r['content']} for r in rows]
    # Prepend a system prompt for the assistant
    system = {
        'role': 'system',
        'content': (
            "You are Support AI for a provably fair slot game. "
            "Be concise, friendly, and helpful. Never promise guaranteed wins. "
            "You can explain RTP (~97%), wallet, deposits/withdrawals, and fairness verification. "
            "If asked about private or admin-only info, politely decline and suggest contacting support."
        )
    }
    ai_reply = (
        _call_ai([system] + msgs) if _ai_enabled()
        else "Hi! Our support AI is not configured yet. Please describe your issue and an agent will follow up."
    )
    _save_support_message(conversation_id, session_id, 'assistant', ai_reply)
    return jsonify({'conversation_id': conversation_id, 'reply': ai_reply})


@app.route('/api/support/history', methods=['GET'])
def support_history():
    session_id = request.args.get('session_id')
    conversation_id = request.args.get('conversation_id')
    try:
        limit = int(request.args.get('limit') or 50)
        limit = max(1, min(limit, 200))
    except Exception:
        return jsonify({'error': 'Invalid limit'}), 400
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    params = []
    where = ['session_id = ?']
    params.append(session_id)
    if conversation_id:
        where.append('conversation_id = ?')
        params.append(conversation_id)
    query = (
        'SELECT conversation_id, ts, role, content FROM support_messages '
        f"WHERE {' AND '.join(where)} ORDER BY ts ASC LIMIT ?"
    )
    params.append(limit)
    out = []
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        for r in cur.fetchall():
            out.append({
                'conversation_id': r['conversation_id'],
                'ts': int(r['ts']),
                'role': r['role'],
                'content': r['content'],
            })
    return jsonify({'messages': out})


@app.route('/api/stats/<session_id>', methods=['GET'])
def get_stats(session_id: str):
    """Get basic game statistics (would be more comprehensive in production)"""
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[session_id]
    
    return jsonify({
        'total_spins': game.rng.nonce // 15,  # Each spin uses 15 nonces
        'current_nonce': game.rng.nonce,
        'rng_state': game.rng.get_game_state()
    })


# ---------------- Wallet & Bankroll Endpoints ----------------

@app.route('/api/wallet/balance/<session_id>', methods=['GET'])
def wallet_balance(session_id: str):
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    _ensure_wallet(session_id)
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM wallets WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        bal = float(row['balance']) if row else 0.0
    return jsonify({'session_id': session_id, 'balance': bal})


@app.route('/api/wallet/transactions/<session_id>', methods=['GET'])
def wallet_transactions(session_id: str):
    if session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    _ensure_wallet(session_id)
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ts, type, amount, method, balance_after, meta FROM transactions WHERE session_id=? ORDER BY ts ASC LIMIT 500", (session_id,))
        rows = cur.fetchall()
        txs = []
        for r in rows:
            txs.append({
                'id': r['id'],
                'ts': r['ts'],
                'type': r['type'],
                'amount': float(r['amount']),
                'method': r['method'],
                'balance_after': float(r['balance_after']),
                'meta': json.loads(r['meta'] or '{}')
            })
    return jsonify({'session_id': session_id, 'transactions': txs[-200:]})


@app.route('/api/wallet/deposit', methods=['POST'])
def wallet_deposit():
    ok, reset = _check_rate('wallet', limit=30, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many requests', 'retry_after': reset - int(time())}), 429
    data = request.get_json() or {}
    idem_key = request.headers.get('Idempotency-Key') or data.get('idempotency_key')
    # Fast path if already processed
    cached = _idem_lookup(idem_key)
    if cached:
        return jsonify(cached)
    session_id = data.get('session_id')
    amount = float(data.get('amount', 0))
    method = data.get('method', 'demo')
    if not session_id or session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    if amount <= 0 or amount > 100000:
        return jsonify({'error': 'Invalid deposit amount'}), 400
    _ensure_wallet(session_id)
    with _lock, _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM wallets WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        bal = float(row['balance']) if row else 0.0
        new_bal = round(bal + amount, 2)
        now_ts = int(time())
        cur.execute("UPDATE wallets SET balance=?, updated_ts=? WHERE session_id=?", (new_bal, now_ts, session_id))
        conn.commit()
        # log tx after balance update so balance_after reflects new balance
    tx = _log_tx(session_id, 'deposit', amount, method=method)
    resp = {'ok': True, 'balance': new_bal, 'tx': tx}
    _idem_store(idem_key, 'wallet_deposit', session_id, resp)
    return jsonify(resp)


@app.route('/api/wallet/withdraw', methods=['POST'])
def wallet_withdraw():
    ok, reset = _check_rate('wallet', limit=30, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many requests', 'retry_after': reset - int(time())}), 429
    data = request.get_json() or {}
    idem_key = request.headers.get('Idempotency-Key') or data.get('idempotency_key')
    cached = _idem_lookup(idem_key)
    if cached:
        return jsonify(cached)
    session_id = data.get('session_id')
    amount = float(data.get('amount', 0))
    method = data.get('method', 'demo')
    if not session_id or session_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    if amount <= 0:
        return jsonify({'error': 'Invalid withdraw amount'}), 400
    _ensure_wallet(session_id)
    with _lock, _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM wallets WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        bal = float(row['balance']) if row else 0.0
        if bal < amount:
            return jsonify({'error': 'Insufficient wallet balance'}), 402
        new_bal = round(bal - amount, 2)
        now_ts = int(time())
        cur.execute("UPDATE wallets SET balance=?, updated_ts=? WHERE session_id=?", (new_bal, now_ts, session_id))
        conn.commit()
    tx = _log_tx(session_id, 'withdraw', -amount, method=method)
    resp = {'ok': True, 'balance': new_bal, 'tx': tx}
    _idem_store(idem_key, 'wallet_withdraw', session_id, resp)
    return jsonify(resp)


@app.route('/api/bankroll', methods=['GET'])
def get_bankroll():
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM bankroll WHERE key='house_pool'")
        row = cur.fetchone()
        hp = float(row['value']) if row else 0.0
    return jsonify({'house_pool': hp})


# ---------------- Analytics ----------------

@app.route('/api/analytics/event', methods=['POST'])
def analytics_event():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    name = data.get('name')
    props = data.get('props') or {}
    # basic validation & truncation
    if not isinstance(name, str) or len(name) > 64:
        return jsonify({'error': 'Invalid name'}), 400
    # enforce size limits on props
    try:
        props_txt = json.dumps(props)
    except Exception:
        return jsonify({'error': 'Invalid props'}), 400
    if len(props_txt.encode('utf-8')) > 4096:
        props_txt = props_txt[:4096]
    ok, reset = _check_rate('analytics', limit=120, window_sec=60)
    if not ok:
        return jsonify({'error': 'Too many events', 'retry_after': reset - int(time())}), 429
    if not name:
        return jsonify({'error': 'Missing name'}), 400
    # ensure session row if provided
    if session_id:
        _ensure_wallet(session_id)  # creates session row if needed
    ua = request.headers.get('User-Agent')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ev_id = secrets.token_hex(8)
    ts_now = int(time())
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO events(id, session_id, ts, name, props, ua, ip)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (ev_id, session_id, ts_now, name, props_txt, ua, ip)
        )
        conn.commit()
    return jsonify({'ok': True, 'id': ev_id})


@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    """Admin-only: Get aggregate analytics counts by event name and totals.
    Query params:
      - since: unix epoch seconds (default: now - 7 days)
      - until: unix epoch seconds (default: now)
      - limit: max distinct event names to return (default: 100)
    """
    ok, err = _require_admin()
    if not ok:
        return err
    ok, err = _verify_signature_if_required(for_admin=True)
    if not ok:
        return err
    try:
        now = int(time())
        since = int(request.args.get('since') or (now - 7*24*3600))
        until = int(request.args.get('until') or now)
        limit = int(request.args.get('limit') or 100)
        limit = max(1, min(limit, 1000))
    except Exception:
        return jsonify({'error': 'Invalid query params'}), 400
    with _db() as conn:
        cur = conn.cursor()
        # Totals
        cur.execute("SELECT COUNT(*) AS c FROM events WHERE ts BETWEEN ? AND ?", (since, until))
        total_events = int(cur.fetchone()['c'])
        cur.execute("SELECT COUNT(DISTINCT session_id) AS c FROM events WHERE ts BETWEEN ? AND ?", (since, until))
        distinct_sessions = int(cur.fetchone()['c'])
        # By name
        cur.execute(
            """
            SELECT name, COUNT(*) AS c
            FROM events
            WHERE ts BETWEEN ? AND ?
            GROUP BY name
            ORDER BY c DESC
            LIMIT ?
            """,
            (since, until, limit)
        )
        by_name = [{'name': r['name'], 'count': int(r['c'])} for r in cur.fetchall()]
    return jsonify({
        'since': since,
        'until': until,
        'totals': {
            'events': total_events,
            'distinct_sessions': distinct_sessions,
        },
        'by_name': by_name,
    })


@app.route('/api/analytics/events', methods=['GET'])
def analytics_events():
    """Admin-only: List recent analytics events (for debugging/QA).
    Query params:
      - name: optional filter by event name
      - limit: number of events (default 100, max 1000)
      - since/until: optional epoch seconds window
    """
    ok, err = _require_admin()
    if not ok:
        return err
    ok, err = _verify_signature_if_required(for_admin=True)
    if not ok:
        return err
    name = request.args.get('name')
    try:
        limit = int(request.args.get('limit') or 100)
        limit = max(1, min(limit, 1000))
        now = int(time())
        since = request.args.get('since')
        until = request.args.get('until')
        since = int(since) if since else None
        until = int(until) if until else now
    except Exception:
        return jsonify({'error': 'Invalid query params'}), 400
    query = "SELECT id, session_id, ts, name, props, ua, ip FROM events"
    params = []
    where = []
    if since is not None:
        where.append('ts >= ?')
        params.append(since)
    if until is not None:
        where.append('ts <= ?')
        params.append(until)
    if name:
        where.append('name = ?')
        params.append(name)
    if where:
        query += ' WHERE ' + ' AND '.join(where)
    query += ' ORDER BY ts DESC LIMIT ?'
    params.append(limit)
    out = []
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        for r in cur.fetchall():
            try:
                props = json.loads(r['props'] or '{}')
            except Exception:
                props = {}
            out.append({
                'id': r['id'],
                'session_id': r['session_id'],
                'ts': int(r['ts']),
                'name': r['name'],
                'props': props,
                'ua': r['ua'],
                'ip': r['ip'],
            })
    return jsonify({'events': out})


@app.route('/api/admin/support/threads', methods=['GET'])
def admin_support_threads():
    ok, err = _require_admin()
    if not ok:
        return err
    ok, err = _verify_signature_if_required(for_admin=True)
    if not ok:
        return err
    try:
        limit = int(request.args.get('limit') or 100)
        limit = max(1, min(limit, 500))
    except Exception:
        return jsonify({'error': 'Invalid limit'}), 400
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT conversation_id,
                   COALESCE(MAX(ts), 0) AS last_ts,
                   COUNT(*) AS count,
                   MAX(CASE WHEN role!='assistant' THEN ts ELSE 0 END) AS last_user_ts
            FROM support_messages
            GROUP BY conversation_id
            ORDER BY last_ts DESC
            LIMIT ?
            """,
            (limit,)
        )
        threads = []
        for r in cur.fetchall():
            # preview: last message content
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT role, content FROM support_messages WHERE conversation_id=? ORDER BY ts DESC LIMIT 1",
                (r['conversation_id'],)
            )
            last = cur2.fetchone()
            threads.append({
                'conversation_id': r['conversation_id'],
                'last_ts': int(r['last_ts']),
                'count': int(r['count']),
                'last_preview': (last['content'] if last else ''),
            })
    return jsonify({'threads': threads})


@app.route('/api/admin/support/messages', methods=['GET'])
def admin_support_messages():
    ok, err = _require_admin()
    if not ok:
        return err
    ok, err = _verify_signature_if_required(for_admin=True)
    if not ok:
        return err
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'error': 'conversation_id required'}), 400
    try:
        limit = int(request.args.get('limit') or 200)
        limit = max(1, min(limit, 1000))
    except Exception:
        return jsonify({'error': 'Invalid limit'}), 400
    out = []
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT ts, role, content FROM support_messages WHERE conversation_id=? ORDER BY ts ASC LIMIT ?",
            (conversation_id, limit)
        )
        for r in cur.fetchall():
            out.append({'ts': int(r['ts']), 'role': r['role'], 'content': r['content']})
    return jsonify({'messages': out})


# Security headers on all responses
@app.after_request
def apply_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Permissions-Policy'] = 'geolocation=()'
    # Strong CSP for API responses
    resp.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    # HSTS (has effect only over HTTPS)
    resp.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    return resp


if __name__ == '__main__':
    print("🎰 Starting Casino Slot API...")
    print("📡 API will be available at: http://localhost:5000")
    print("\nEndpoints:")
    print("  POST /api/game/new - Create new game")
    print("  GET  /api/game/state/<session_id> - Get game state")
    print("  POST /api/game/spin/<session_id> - Spin the slots")
    print("  POST /api/game/change-seed/<session_id> - Change client seed")
    print("  POST /api/verify - Verify game result")
    print("  GET  /api/paytable - Get paytable info")
    print("\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
