"""
Casino Slot Game Engine - Professional Edition
3x5 reels with WILD feature matching screenshot design
"""

from typing import List, Dict, Tuple
from rng import ProvablyFairRNG

class SlotGame:
    """Main slot machine logic with provably fair RNG and WILD substitution"""
    
    # PROFESSIONAL THEME - 3 Main Planets + WILD (from screenshot)
    SYMBOLS = {
        '🌍': {'weight': 32, 'name': 'Earth'},          # Earth planet
        '🌙': {'weight': 28, 'name': 'Moon'},           # Moon
        '🪐': {'weight': 28, 'name': 'Rainbow Planet'}, # Rainbow planet with rings
        'WILD': {'weight': 6, 'name': 'WILD'},          # Wild symbol - Balanced frequency
        '⭐': {'weight': 10, 'name': 'Star'},           # Star bonus
        '💎': {'weight': 4, 'name': 'Diamond'},         # Diamond
        '🎰': {'weight': 2, 'name': 'JACKPOT'},         # Jackpot
    }
    
    # BALANCED PAYOUTS - Target 97% RTP = 3% house edge
    # Optimized for approximately 97% RTP with WILD substitution
    PAYOUTS = {
        '🌍': {3: 0.35, 4: 0.85, 5: 2.5},   # Earth - Very common
        '🌙': {3: 0.42, 4: 1.08, 5: 3.2},   # Moon - Common
        '🪐': {3: 0.48, 4: 1.32, 5: 4.0},   # Rainbow - Common
        'WILD': {3: 0.70, 4: 2.0, 5: 7.0},  # Wild - substitution power
        '⭐': {3: 1.80, 4: 4.9, 5: 14.0},   # Star - Good payout
        '💎': {3: 4.5, 4: 13.2, 5: 45.0},   # Diamond - High payout
        '🎰': {3: 27.0, 4: 95.0, 5: 375.0}, # JACKPOT - Maximum!
    }
    
    PAYLINES = [
        [1, 1, 1, 1, 1],  # Middle row
        [0, 0, 0, 0, 0],  # Top row
        [2, 2, 2, 2, 2],  # Bottom row
        [0, 1, 2, 1, 0],  # V shape
        [2, 1, 0, 1, 2],  # Inverted V
        [1, 0, 0, 0, 1],  # Wide V
        [1, 2, 2, 2, 1],  # Wide inverted V
        [0, 0, 1, 2, 2],  # Ascending
        [2, 2, 1, 0, 0],  # Descending
    ]
    
    def __init__(self):
        self.rng = ProvablyFairRNG()
        self.balance = 100.0
        self.total_spins = 0
        self.total_wagered = 0.0
        self.total_won = 0.0
        
    def _generate_reel(self):
        symbols = list(self.SYMBOLS.keys())
        weights = [self.SYMBOLS[s]['weight'] for s in symbols]
        total_weight = sum(weights)
        rand, _ = self.rng.generate_random_float(0, total_weight)
        cumulative = 0
        for symbol, weight in zip(symbols, weights):
            cumulative += weight
            if rand <= cumulative:
                return symbol
        return symbols[-1]
    
    def _generate_grid(self):
        grid = []
        for row in range(3):
            grid.append([self._generate_reel() for _ in range(5)])
        return grid
    
    def _check_wins(self, grid):
        """Check for wins with WILD substitution support"""
        wins = []
        for line_index, payline in enumerate(self.PAYLINES):
            symbols_on_line = [grid[row][col] for col, row in enumerate(payline)]
            
            # Find first non-WILD symbol
            first_symbol = None
            for symbol in symbols_on_line:
                if symbol != 'WILD':
                    first_symbol = symbol
                    break
            
            # If all WILDs, treat as WILD win
            if first_symbol is None:
                first_symbol = 'WILD'
            
            # Count matches (considering WILD as substitute)
            match_count = 0
            for symbol in symbols_on_line:
                if symbol == first_symbol or symbol == 'WILD':
                    match_count += 1
                else:
                    break
            
            # Check if we have a winning combination
            if match_count >= 3 and first_symbol in self.PAYOUTS:
                payout_info = self.PAYOUTS[first_symbol]
                if match_count in payout_info:
                    wins.append({
                        'payline': line_index,
                        'symbol': first_symbol,
                        'count': match_count,
                        'multiplier': payout_info[match_count],
                        'positions': [(payline[i], i) for i in range(match_count)]
                    })
        return wins
    
    def spin(self, bet_amount=1.0):
        if bet_amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= bet_amount
        self.total_wagered += bet_amount
        self.total_spins += 1
        grid = self._generate_grid()
        wins = self._check_wins(grid)
        total_win = sum(win['multiplier'] * bet_amount for win in wins)
        self.balance += total_win
        self.total_won += total_win
        return {
            'grid': grid,
            'wins': wins,
            'total_win': total_win,
            'balance': self.balance,
            'server_seed_hash': self.rng.get_server_seed_hash(),
            'client_seed': self.rng.client_seed,
            'nonce': self.rng.nonce - 1,
        }
    
    def change_client_seed(self, new_seed):
        old_server_seed = self.rng.reveal_server_seed()
        self.rng = ProvablyFairRNG(client_seed=new_seed)
        return {
            'old_server_seed': old_server_seed,
            'new_server_seed_hash': self.rng.get_server_seed_hash(),
            'new_client_seed': new_seed
        }
    
    def get_state(self):
        return {
            'balance': self.balance,
            'total_spins': self.total_spins,
            'total_wagered': self.total_wagered,
            'total_won': self.total_won,
            'server_seed_hash': self.rng.get_server_seed_hash(),
            'client_seed': self.rng.client_seed,
            'nonce': self.rng.nonce,
        }
    
    @classmethod
    def verify_result(cls, server_seed, client_seed, nonce, expected_grid):
        rng = ProvablyFairRNG(server_seed=server_seed, client_seed=client_seed)
        for _ in range(nonce):
            rng.generate_random_int(0, 100)
        symbols = list(cls.SYMBOLS.keys())
        weights = [cls.SYMBOLS[s]['weight'] for s in symbols]
        total_weight = sum(weights)
        verified_grid = []
        for row in range(3):
            verified_row = []
            for col in range(5):
                rand, _ = rng.generate_random_float(0, total_weight)
                cumulative = 0
                for symbol, weight in zip(symbols, weights):
                    cumulative += weight
                    if rand <= cumulative:
                        verified_row.append(symbol)
                        break
                else:
                    verified_row.append(symbols[-1])
            verified_grid.append(verified_row)
        return verified_grid == expected_grid
