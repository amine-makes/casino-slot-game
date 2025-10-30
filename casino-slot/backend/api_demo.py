"""
API Usage Example
Demonstrates how to interact with the Casino Slot API programmatically
"""

import requests
import json
from time import sleep

# API Configuration
API_BASE = 'http://localhost:5000/api'


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    print("🎰 Casino Slot API Demo")
    
    # 1. Create a new game
    print_section("1. Creating New Game")
    response = requests.post(f'{API_BASE}/game/new')
    game_data = response.json()
    
    session_id = game_data['session_id']
    print(f"✓ Session ID: {session_id}")
    print(f"✓ Server Seed Hash: {game_data['server_seed_hash']}")
    print(f"✓ Client Seed: {game_data['client_seed']}")
    print(f"✓ Starting Nonce: {game_data['nonce']}")
    
    # 2. Get paytable
    print_section("2. Fetching Paytable")
    response = requests.get(f'{API_BASE}/paytable')
    paytable = response.json()
    
    print("Symbol Payouts:")
    for symbol, payout_data in paytable['payouts'].items():
        symbol_name = paytable['symbols'][symbol]['name']
        print(f"  {symbol} ({symbol_name:8}) - 3×: {payout_data.get(3, '-'):3}  4×: {payout_data.get(4, '-'):3}  5×: {payout_data.get(5, '-'):4}")
    
    # 3. Simulate 5 spins
    print_section("3. Simulating 5 Spins")
    
    balance = 100.0
    print(f"Starting Balance: ${balance:.2f}\n")
    
    for i in range(5):
        print(f"\nSpin #{i+1}:")
        print("-" * 40)
        
        # Spin
        response = requests.post(
            f'{API_BASE}/game/spin/{session_id}',
            json={'bet_amount': 1.0, 'active_paylines': 9}
        )
        result = response.json()
        
        # Update balance
        balance -= result['total_bet']
        balance += result['total_win']
        
        # Display grid
        print("\nReels:")
        for row in result['grid']:
            print("  " + " | ".join(row))
        
        # Display wins
        if result['wins']:
            print(f"\n🎉 Wins:")
            for win in result['wins']:
                print(f"  Line {win['payline']+1}: {win['count']}× {win['symbol']} = ${win['payout'] * result['bet_amount']:.2f}")
            print(f"\n💰 Total Win: ${result['total_win']:.2f}")
        else:
            print("\n❌ No wins")
        
        print(f"\nBalance: ${balance:.2f} (Profit: ${result['profit']:.2f})")
        
        sleep(0.5)  # Simulate thinking time
    
    # 4. Change client seed and reveal server seed
    print_section("4. Changing Client Seed (Reveals Server Seed)")
    
    response = requests.post(
        f'{API_BASE}/game/change-seed/{session_id}',
        json={'new_client_seed': 'my_custom_seed_123'}
    )
    seed_data = response.json()
    
    print(f"✓ Old Server Seed (REVEALED): {seed_data['old_server_seed']}")
    print(f"✓ Old Server Seed Hash: {seed_data['old_server_seed_hash']}")
    print(f"\n✓ New Server Seed Hash: {seed_data['new_server_seed_hash']}")
    print(f"✓ New Client Seed: {seed_data['new_client_seed']}")
    print(f"✓ Nonce Reset to: {seed_data['nonce_reset']}")
    
    # 5. Get final game state
    print_section("5. Final Game State")
    
    response = requests.get(f'{API_BASE}/game/state/{session_id}')
    state = response.json()
    
    print(f"Server Seed Hash: {state['server_seed_hash']}")
    print(f"Client Seed: {state['client_seed']}")
    print(f"Current Nonce: {state['nonce']}")
    
    # 6. Display statistics
    print_section("6. Session Statistics")
    
    response = requests.get(f'{API_BASE}/stats/{session_id}')
    stats = response.json()
    
    print(f"Total Spins: {stats['total_spins']}")
    print(f"Final Balance: ${balance:.2f}")
    print(f"Total Profit/Loss: ${balance - 100:.2f}")
    
    print_section("Demo Complete!")
    print("You can verify all previous spins using the revealed server seed.")
    print("See the verification documentation in the README.")


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server")
        print("Please make sure the backend is running:")
        print("  cd backend && python app.py")
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
