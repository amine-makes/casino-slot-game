"""
Provably Fair Random Number Generator
Similar to crypto casinos like Stake.com and 1xbet
Uses server seed, client seed, and nonce for verifiable randomness
"""

import hashlib
import hmac
import secrets
from typing import Tuple, List


class ProvablyFairRNG:
    """
    Cryptographically secure RNG for casino games.
    Implements provably fair system where outcomes can be verified.
    """
    
    def __init__(self, server_seed: str = None, client_seed: str = None):
        """
        Initialize RNG with server and client seeds.
        
        Args:
            server_seed: Server's secret seed (hidden until revealed)
            client_seed: Client's public seed (can be changed by player)
        """
        self.server_seed = server_seed or self._generate_server_seed()
        self.client_seed = client_seed or self._generate_client_seed()
        self.nonce = 0
        
    def _generate_server_seed(self) -> str:
        """Generate a cryptographically secure server seed"""
        return secrets.token_hex(32)  # 64 character hex string
    
    def _generate_client_seed(self) -> str:
        """Generate a default client seed"""
        return secrets.token_hex(16)  # 32 character hex string
    
    def get_server_seed_hash(self) -> str:
        """
        Get SHA-256 hash of server seed.
        This can be shown to player before game starts.
        """
        return hashlib.sha256(self.server_seed.encode()).hexdigest()
    
    def _generate_hash(self, nonce: int) -> str:
        """
        Generate HMAC-SHA256 hash using server seed, client seed, and nonce.
        
        Args:
            nonce: Number used once (increments with each game)
            
        Returns:
            Hex digest of the hash
        """
        message = f"{self.client_seed}:{nonce}"
        return hmac.new(
            self.server_seed.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def generate_random_float(self, min_val: float = 0.0, max_val: float = 1.0) -> Tuple[float, int]:
        """
        Generate a provably fair random float.
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (exclusive)
            
        Returns:
            Tuple of (random_value, nonce_used)
        """
        hash_result = self._generate_hash(self.nonce)
        
        # Take first 8 characters (32 bits) of hash
        hash_int = int(hash_result[:8], 16)
        
        # Normalize to 0-1 range
        normalized = hash_int / 0xFFFFFFFF
        
        # Scale to desired range
        result = min_val + (normalized * (max_val - min_val))
        
        current_nonce = self.nonce
        self.nonce += 1
        
        return result, current_nonce
    
    def generate_random_int(self, min_val: int, max_val: int) -> Tuple[int, int]:
        """
        Generate a provably fair random integer.
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Tuple of (random_value, nonce_used)
        """
        random_float, nonce = self.generate_random_float()
        result = min_val + int(random_float * (max_val - min_val + 1))
        
        # Ensure we don't exceed max_val due to floating point issues
        result = min(result, max_val)
        
        return result, nonce
    
    def generate_multiple_ints(self, count: int, min_val: int, max_val: int) -> Tuple[List[int], List[int]]:
        """
        Generate multiple random integers (useful for slot reels).
        
        Args:
            count: Number of random integers to generate
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Tuple of ([random_values], [nonces_used])
        """
        values = []
        nonces = []
        
        for _ in range(count):
            val, nonce = self.generate_random_int(min_val, max_val)
            values.append(val)
            nonces.append(nonce)
        
        return values, nonces
    
    def verify_result(self, server_seed: str, client_seed: str, nonce: int, expected_hash: str) -> bool:
        """
        Verify that a game result was generated fairly.
        
        Args:
            server_seed: The revealed server seed
            client_seed: The client seed used
            nonce: The nonce used for this game
            expected_hash: The hash that should be produced
            
        Returns:
            True if verification passes
        """
        temp_rng = ProvablyFairRNG(server_seed, client_seed)
        temp_rng.nonce = nonce
        generated_hash = temp_rng._generate_hash(nonce)
        
        return generated_hash == expected_hash
    
    def get_game_state(self) -> dict:
        """Get current RNG state for transparency"""
        return {
            "server_seed_hash": self.get_server_seed_hash(),
            "client_seed": self.client_seed,
            "nonce": self.nonce
        }
    
    def reveal_server_seed(self) -> str:
        """Reveal server seed (typically done when changing seeds)"""
        return self.server_seed


# Example usage and testing
if __name__ == "__main__":
    print("=== Provably Fair RNG Demo ===\n")
    
    # Create RNG instance
    rng = ProvablyFairRNG()
    
    print(f"Server Seed Hash: {rng.get_server_seed_hash()}")
    print(f"Client Seed: {rng.client_seed}")
    print(f"Starting Nonce: {rng.nonce}\n")
    
    # Generate some random numbers
    print("Generating 5 slot reel positions (0-9):")
    positions, nonces = rng.generate_multiple_ints(5, 0, 9)
    for i, (pos, nonce) in enumerate(zip(positions, nonces)):
        print(f"  Reel {i+1}: Position {pos} (Nonce: {nonce})")
    
    print(f"\n✓ Server Seed (revealed): {rng.reveal_server_seed()}")
    print("\nYou can now verify these results using the server seed!")
