"""
Casino Math Analysis - House Edge & RTP Calculator
Analyzes the expected return and house edge of the slot game
"""

from slot_game import SlotGame

def calculate_rtp():
    """Calculate the theoretical Return to Player (RTP) percentage"""
    
    print("🎲 CASINO MATH ANALYSIS 🎲")
    print("=" * 60)
    
    # Get symbol distribution
    symbols = SlotGame.SYMBOLS
    payouts = SlotGame.PAYOUTS
    
    # Calculate total weight
    total_weight = sum(data['weight'] for data in symbols.values())
    
    print("\n📊 Symbol Distribution:")
    print("-" * 60)
    for symbol, data in symbols.items():
        probability = data['weight'] / total_weight
        print(f"{symbol} {data['name']:12} - Probability: {probability:.2%} (Weight: {data['weight']}/{total_weight})")
    
    print("\n" + "=" * 60)
    print("💰 PAYOUT ANALYSIS")
    print("=" * 60)
    
    # Calculate expected value for each symbol on a single payline
    total_ev = 0
    
    for symbol, payout_data in payouts.items():
        prob = symbols[symbol]['weight'] / total_weight
        
        # Probability of getting 3, 4, or 5 in a row
        prob_3 = prob ** 3
        prob_4 = prob ** 4
        prob_5 = prob ** 5
        
        # Expected value for this symbol
        ev_3 = prob_3 * payout_data.get(3, 0)
        ev_4 = prob_4 * payout_data.get(4, 0)
        ev_5 = prob_5 * payout_data.get(5, 0)
        
        symbol_ev = ev_3 + ev_4 + ev_5
        total_ev += symbol_ev
        
        print(f"\n{symbol} {symbols[symbol]['name']}:")
        print(f"  3× match: {prob_3:.6f} × {payout_data.get(3, 0):4}× = {ev_3:.6f}")
        print(f"  4× match: {prob_4:.6f} × {payout_data.get(4, 0):4}× = {ev_4:.6f}")
        print(f"  5× match: {prob_5:.6f} × {payout_data.get(5, 0):4}× = {ev_5:.6f}")
        print(f"  Symbol EV: {symbol_ev:.6f}")
    
    # Multiply by number of paylines
    num_paylines = len(SlotGame.PAYLINES)
    total_ev_all_lines = total_ev * num_paylines
    
    # Calculate RTP (Return to Player)
    # This is the percentage of money returned to players over time
    rtp_percentage = total_ev_all_lines * 100
    house_edge = 100 - rtp_percentage
    
    print("\n" + "=" * 60)
    print("📈 FINAL RESULTS")
    print("=" * 60)
    print(f"\nExpected Value per line: {total_ev:.6f}")
    print(f"Number of paylines: {num_paylines}")
    print(f"Total Expected Value: {total_ev_all_lines:.6f}")
    print(f"\n{'🎯 RTP (Return to Player):':<30} {rtp_percentage:.2f}%")
    print(f"{'🏠 House Edge:':<30} {house_edge:.2f}%")
    
    print("\n" + "=" * 60)
    print("💡 WHAT THIS MEANS:")
    print("=" * 60)
    
    if rtp_percentage > 100:
        print(f"⚠️  WARNING: RTP is {rtp_percentage:.2f}%!")
        print("   Players will WIN money over time!")
        print("   The house will LOSE money!")
        print("\n   This is NOT sustainable for a casino business.")
        print("   You need to adjust symbol weights or payouts.")
    elif rtp_percentage > 97:
        print(f"✅ RTP is {rtp_percentage:.2f}% - VERY player-friendly")
        print("   This is generous, similar to top online casinos")
        print("   House edge is low, good for attracting players")
    elif rtp_percentage > 92:
        print(f"✅ RTP is {rtp_percentage:.2f}% - Standard casino range")
        print("   This is typical for online slots")
        print("   Balanced between player enjoyment and profitability")
    else:
        print(f"⚠️  RTP is {rtp_percentage:.2f}% - Low for players")
        print("   This is tight, players may not enjoy it")
        print("   House edge is high")
    
    print("\n" + "=" * 60)
    print("💵 PROFIT SIMULATION")
    print("=" * 60)
    
    # Simulate what happens with $10,000 wagered
    total_wagered = 10000
    expected_return = total_wagered * (rtp_percentage / 100)
    house_profit = total_wagered - expected_return
    
    print(f"\nIf players wager: ${total_wagered:,.2f}")
    print(f"Expected return:  ${expected_return:,.2f}")
    print(f"House keeps:      ${house_profit:,.2f}")
    print(f"House profit:     {house_edge:.2f}%")
    
    return rtp_percentage, house_edge


def suggest_adjustments(target_rtp=95.0):
    """Suggest symbol weight adjustments to achieve target RTP"""
    
    print("\n\n" + "=" * 60)
    print(f"🎯 ADJUSTMENTS FOR {target_rtp}% RTP")
    print("=" * 60)
    
    print(f"\nTo achieve a {target_rtp}% RTP (house edge {100-target_rtp:.1f}%), you can:")
    print("\n1. REDUCE HIGH-VALUE SYMBOL WEIGHTS:")
    print("   Current: 🚀 Rocket (weight: 1)")
    print("   Suggestion: Keep at 1 (already rare)")
    print("\n   Current: 🌟 Supernova (weight: 1)")
    print("   Suggestion: Keep at 1")
    
    print("\n2. INCREASE COMMON SYMBOL WEIGHTS:")
    print("   Current: 🌙 Moon (weight: 5)")
    print("   Suggestion: Increase to 7-8")
    print("\n   Current: ⭐ Star (weight: 5)")
    print("   Suggestion: Increase to 7-8")
    
    print("\n3. REDUCE PAYOUT MULTIPLIERS:")
    print("   Example: Reduce 🚀 Rocket from 1000× to 500×")
    print("   Example: Reduce ☄️ Comet from 200× to 150×")
    
    print("\n4. RECOMMENDED SETTINGS for 95% RTP:")
    print("   " + "-" * 56)
    print("   Symbol    | Weight | 3×   | 4×   | 5×")
    print("   " + "-" * 56)
    print("   🌙 Moon   |   7    |  5×  |  10× |  20×")
    print("   ⭐ Star   |   7    |  5×  |  10× |  20×")
    print("   🪐 Saturn |   5    |  8×  |  15× |  40×")
    print("   🌍 Earth  |   5    |  8×  |  15× |  40×")
    print("   🌌 Galaxy |   3    |  12× |  30× |  80×")
    print("   ☄️ Comet  |   2    |  20× |  60× |  150×")
    print("   🌟 Nova   |   1    |  40× |  120×|  400×")
    print("   🚀 Rocket |   1    |  80× |  400×|  800×")
    print("   " + "-" * 56)


if __name__ == "__main__":
    rtp, house_edge = calculate_rtp()
    
    if rtp < 92 or rtp > 98:
        suggest_adjustments(95.0)
    
    print("\n" + "=" * 60)
    print("✅ Analysis Complete!")
    print("=" * 60)
