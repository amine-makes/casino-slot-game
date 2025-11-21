// Netlify Functions version of the casino slot backend
// This replaces the Flask app for free deployment on Netlify

const crypto = require('crypto');

// Simple in-memory storage (in production, you'd use a database service)
let games = {};
let wallets = {};
let transactions = {};
let sessions = {};
let bankroll = { house_pool: 0 };

// Provably Fair RNG implementation
class ProvablyFairRNG {
  constructor() {
    this.server_seed = crypto.randomBytes(32).toString('hex');
    this.revealed_seed = null;
    this.nonce = 0;
  }

  generate_hash(client_seed, nonce, server_seed) {
    const combined = `${client_seed}:${nonce}:${server_seed}`;
    return crypto.createHmac('sha256', server_seed).update(combined).digest('hex');
  }

  next_float(client_seed) {
    this.nonce += 1;
    const hash = this.generate_hash(client_seed, this.nonce, this.server_seed);
    const hex_value = hash.substring(0, 8);
    const decimal_value = parseInt(hex_value, 16);
    return decimal_value / 0xFFFFFFFF;
  }

  reveal_seed() {
    this.revealed_seed = this.server_seed;
    this.server_seed = crypto.randomBytes(32).toString('hex');
    this.nonce = 0;
    return this.revealed_seed;
  }

  get_info() {
    return {
      server_seed_hash: crypto.createHash('sha256').update(this.server_seed).digest('hex'),
      nonce: this.nonce,
      revealed_seed: this.revealed_seed
    };
  }
}

// Slot Game Implementation
class SlotGame {
  constructor() {
    this.symbols = ['🌟', '🔮', '👑', '💎', '🌙', '⚡', '🌀', '🎆'];
    this.symbol_weights = [100, 80, 60, 40, 30, 20, 15, 10]; // Rarity weights
    this.paylines = [
      [[0,0], [0,1], [0,2], [0,3], [0,4]], // Top row
      [[1,0], [1,1], [1,2], [1,3], [1,4]], // Middle row  
      [[2,0], [2,1], [2,2], [2,3], [2,4]], // Bottom row
      [[0,0], [1,1], [2,2], [1,3], [0,4]], // Diagonal down-up
      [[2,0], [1,1], [0,2], [1,3], [2,4]], // Diagonal up-down
      [[1,0], [0,1], [0,2], [0,3], [1,4]], // V shape
      [[1,0], [2,1], [2,2], [2,3], [1,4]], // Inverted V
      [[0,0], [0,1], [1,2], [2,3], [2,4]], // L shape
      [[2,0], [2,1], [1,2], [0,3], [0,4]]  // Inverted L
    ];
  }

  weighted_choice(rng, client_seed) {
    const total_weight = this.symbol_weights.reduce((a, b) => a + b, 0);
    const rand_val = rng.next_float(client_seed) * total_weight;
    
    let cumulative = 0;
    for (let i = 0; i < this.symbols.length; i++) {
      cumulative += this.symbol_weights[i];
      if (rand_val <= cumulative) {
        return this.symbols[i];
      }
    }
    return this.symbols[this.symbols.length - 1];
  }

  spin(rng, client_seed, bet_amount, active_paylines = 9) {
    const grid = [];
    for (let row = 0; row < 3; row++) {
      const grid_row = [];
      for (let col = 0; col < 5; col++) {
        grid_row.push(this.weighted_choice(rng, client_seed));
      }
      grid.push(grid_row);
    }

    const winning_lines = [];
    let total_win = 0;

    for (let i = 0; i < Math.min(active_paylines, this.paylines.length); i++) {
      const line = this.paylines[i];
      const symbols_on_line = line.map(([row, col]) => grid[row][col]);
      const win = this.calculate_line_win(symbols_on_line, bet_amount);
      
      if (win > 0) {
        winning_lines.push({
          line_number: i + 1,
          positions: line,
          symbols: symbols_on_line,
          win_amount: win
        });
        total_win += win;
      }
    }

    return {
      grid,
      winning_lines,
      total_win,
      bet_amount,
      active_paylines,
      nonce: rng.nonce
    };
  }

  calculate_line_win(symbols, bet_amount) {
    const symbol_counts = {};
    for (const symbol of symbols) {
      symbol_counts[symbol] = (symbol_counts[symbol] || 0) + 1;
    }

    let max_count = 0;
    let winning_symbol = null;
    for (const [symbol, count] of Object.entries(symbol_counts)) {
      if (count > max_count) {
        max_count = count;
        winning_symbol = symbol;
      }
    }

    if (max_count < 3) return 0;

    const multipliers = {
      '🌟': [0, 0, 2, 5, 10],   // Star
      '🔮': [0, 0, 3, 8, 15],   // Crystal Ball  
      '👑': [0, 0, 4, 10, 25],  // Crown
      '💎': [0, 0, 5, 15, 50],  // Diamond
      '🌙': [0, 0, 8, 25, 75],  // Moon
      '⚡': [0, 0, 10, 40, 100], // Lightning
      '🌀': [0, 0, 15, 60, 150], // Vortex
      '🎆': [0, 0, 20, 100, 500] // Fireworks (Jackpot)
    };

    const multiplier = multipliers[winning_symbol][max_count] || 0;
    return bet_amount * multiplier;
  }
}

// Utility functions
function generateSessionId() {
  return crypto.randomBytes(16).toString('hex');
}

function generateTxId() {
  return crypto.randomBytes(8).toString('hex');
}

// CORS headers for all responses
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Token',
  'Access-Control-Max-Age': '86400'
};

// Main handler function
exports.handler = async (event, context) => {
  // Handle preflight requests
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: corsHeaders,
      body: ''
    };
  }

  // Extract path - handle both direct function calls and API routes
  let path = event.path || '';
  if (path.startsWith('/.netlify/functions/api')) {
    path = path.replace('/.netlify/functions/api', '');
  }
  path = path.replace('/api', '') || '/';
  
  const method = event.httpMethod;
  
  try {
    let response;
    
    switch (`${method} ${path}`) {
      case 'GET /':
      case 'GET /health':
        response = { 
          status: 'ok', 
          timestamp: Date.now(),
          version: '1.0.0',
          environment: 'netlify-functions'
        };
        break;
        
      case 'POST /session':
        const sessionId = generateSessionId();
        const rng = new ProvablyFairRNG();
        const slotGame = new SlotGame();
        
        games[sessionId] = { rng, slotGame };
        sessions[sessionId] = { created_at: Date.now() };
        wallets[sessionId] = { balance: 0 };
        transactions[sessionId] = [];
        
        response = {
          session_id: sessionId,
          server_seed_hash: rng.get_info().server_seed_hash,
          nonce: 0
        };
        break;
        
      case 'POST /wallet/deposit':
        const depositData = JSON.parse(event.body);
        const { session_id: depSessionId, amount } = depositData;
        
        if (!wallets[depSessionId]) {
          return {
            statusCode: 404,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Session not found' })
          };
        }
        
        const depositAmount = parseFloat(amount);
        if (depositAmount <= 0) {
          return {
            statusCode: 400,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Invalid deposit amount' })
          };
        }
        
        wallets[depSessionId].balance += depositAmount;
        const depositTx = {
          id: generateTxId(),
          type: 'deposit',
          amount: depositAmount,
          balance_after: wallets[depSessionId].balance,
          ts: Math.floor(Date.now() / 1000),
          method: 'test'
        };
        
        transactions[depSessionId].push(depositTx);
        
        response = {
          ok: true,
          balance: wallets[depSessionId].balance,
          tx: depositTx
        };
        break;
        
      case 'GET /wallet/balance':
        const balanceSessionId = event.queryStringParameters?.session_id;
        if (!wallets[balanceSessionId]) {
          return {
            statusCode: 404,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Session not found' })
          };
        }
        
        response = {
          session_id: balanceSessionId,
          balance: wallets[balanceSessionId].balance
        };
        break;
        
      case 'POST /spin':
        const spinData = JSON.parse(event.body);
        const { session_id: spinSessionId, bet_amount, active_paylines = 9, client_seed = 'player' } = spinData;
        
        if (!games[spinSessionId]) {
          return {
            statusCode: 404,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Session not found' })
          };
        }
        
        const betAmount = parseFloat(bet_amount);
        if (betAmount <= 0) {
          return {
            statusCode: 400,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Invalid bet amount' })
          };
        }
        
        if (wallets[spinSessionId].balance < betAmount) {
          return {
            statusCode: 400,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Insufficient balance' })
          };
        }
        
        // Deduct bet
        wallets[spinSessionId].balance -= betAmount;
        const betTx = {
          id: generateTxId(),
          type: 'bet',
          amount: -betAmount,
          balance_after: wallets[spinSessionId].balance,
          ts: Math.floor(Date.now() / 1000),
          method: null,
          meta: { spin_nonce: games[spinSessionId].rng.nonce + 1 }
        };
        transactions[spinSessionId].push(betTx);
        
        // Calculate house edge (3%)
        const houseEdge = betAmount * 0.03;
        bankroll.house_pool += houseEdge;
        
        // Perform spin
        const spinResult = games[spinSessionId].slotGame.spin(
          games[spinSessionId].rng, 
          client_seed, 
          betAmount, 
          active_paylines
        );
        
        // Process winnings
        if (spinResult.total_win > 0) {
          wallets[spinSessionId].balance += spinResult.total_win;
          const winTx = {
            id: generateTxId(),
            type: 'win',
            amount: spinResult.total_win,
            balance_after: wallets[spinSessionId].balance,
            ts: Math.floor(Date.now() / 1000),
            method: null,
            meta: { spin_nonce: spinResult.nonce }
          };
          transactions[spinSessionId].push(winTx);
        }
        
        response = {
          ...spinResult,
          balance: wallets[spinSessionId].balance,
          server_seed_hash: games[spinSessionId].rng.get_info().server_seed_hash
        };
        break;
        
      case 'GET /rng/info':
        const rngSessionId = event.queryStringParameters?.session_id;
        if (!games[rngSessionId]) {
          return {
            statusCode: 404,
            headers: corsHeaders,
            body: JSON.stringify({ error: 'Session not found' })
          };
        }
        
        response = games[rngSessionId].rng.get_info();
        break;
        
      default:
        return {
          statusCode: 404,
          headers: corsHeaders,
          body: JSON.stringify({ error: 'Endpoint not found' })
        };
    }
    
    return {
      statusCode: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(response)
    };
    
  } catch (error) {
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: 'Internal server error', message: error.message })
    };
  }
};