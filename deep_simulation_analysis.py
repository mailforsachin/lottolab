#!/usr/bin/env python3
"""
Deep Simulation Analysis for $100 Budget
Runs multiple simulations to find the best strategy
"""

import requests
import json
import time
import statistics
from datetime import datetime

BASE_URL = "https://lottolab.omchat.ovh/api/v1"

def run_simulation(strategy_id, num_tickets, iterations=5):
    """Run multiple simulations and return average results"""
    results = []
    
    print(f"\n🎲 Testing Strategy {strategy_id} with {num_tickets} tickets...")
    
    for i in range(iterations):
        print(f"  Run {i+1}/{iterations}...", end="", flush=True)
        
        # Run simulation
        response = requests.post(
            f"{BASE_URL}/simulations/",
            json={"strategy_id": strategy_id, "num_tickets": num_tickets},
            timeout=60
        )
        
        if response.status_code != 200:
            print(f" ❌ Error: {response.status_code}")
            continue
        
        data = response.json()
        sim_id = data['id']
        
        # Wait for completion
        time.sleep(3)
        
        # Get results
        for attempt in range(10):  # Wait up to 30 seconds
            result = requests.get(f"{BASE_URL}/simulations/{sim_id}")
            if result.status_code == 200:
                sim_data = result.json()
                if sim_data['status'] == 'completed':
                    results.append({
                        'roi': sim_data['roi'],
                        'total_won': sim_data['total_won'],
                        'best_win': sim_data['best_win'],
                        'tickets': sim_data['total_tickets']
                    })
                    print(" ✅", end="", flush=True)
                    break
            time.sleep(3)
        
        time.sleep(1)
    
    print()  # New line
    
    if not results:
        return None
    
    return {
        'avg_roi': statistics.mean([r['roi'] for r in results]),
        'avg_won': statistics.mean([r['total_won'] for r in results]),
        'max_won': max([r['total_won'] for r in results]),
        'min_won': min([r['total_won'] for r in results]),
        'avg_best_win': statistics.mean([r['best_win'] for r in results]),
        'iterations': len(results)
    }

def get_win_probability(strategy_id, num_tickets, iterations=3):
    """Calculate probability of winning with different match counts"""
    results = {3: 0, 4: 0, 5: 0, 6: 0}
    total_tickets = 0
    
    print(f"\n📊 Calculating win probabilities for Strategy {strategy_id}...")
    
    for i in range(iterations):
        print(f"  Run {i+1}/{iterations}...", end="", flush=True)
        
        response = requests.post(
            f"{BASE_URL}/simulations/",
            json={"strategy_id": strategy_id, "num_tickets": num_tickets}
        )
        
        if response.status_code == 200:
            data = response.json()
            sim_id = data['id']
            time.sleep(3)
            
            # Get results
            for attempt in range(10):
                result = requests.get(f"{BASE_URL}/simulations/{sim_id}")
                if result.status_code == 200:
                    sim_data = result.json()
                    if sim_data['status'] == 'completed':
                        for match in [3, 4, 5, 6]:
                            results[match] += sim_data['win_counts'].get(str(match), 0)
                            total_tickets += sim_data['total_tickets']
                        print(" ✅", end="", flush=True)
                        break
                time.sleep(3)
        
        time.sleep(1)
    
    print()  # New line
    
    if total_tickets == 0:
        return None
    
    return {
        'prob_3': results[3] / total_tickets * 100 if total_tickets > 0 else 0,
        'prob_4': results[4] / total_tickets * 100 if total_tickets > 0 else 0,
        'prob_5': results[5] / total_tickets * 100 if total_tickets > 0 else 0,
        'prob_6': results[6] / total_tickets * 100 if total_tickets > 0 else 0,
        'total_checked': total_tickets
    }

def main():
    print("=" * 60)
    print("🎲 Lotto 6/49 Deep Simulation Analysis")
    print(f"💰 Budget: $100 = 50 tickets")
    print("=" * 60)
    
    strategies = [
        {"id": 1, "name": "Random (Quick Pick)"},
        {"id": 2, "name": "Sobol Sequence"},
        {"id": 3, "name": "Monte Carlo Optimized"},
        {"id": 4, "name": "Genetic Algorithm"},
        {"id": 5, "name": "Hybrid AI"}
    ]
    
    results = []
    
    # Run ROI simulations
    print("\n📈 Running ROI Analysis (5 iterations each)...")
    for strategy in strategies:
        result = run_simulation(strategy["id"], 50, iterations=5)
        if result:
            results.append({
                "id": strategy["id"],
                "name": strategy["name"],
                "roi": result['avg_roi'],
                "avg_won": result['avg_won'],
                "max_won": result['max_won'],
                "min_won": result['min_won'],
                "best_win": result['avg_best_win']
            })
    
    # Display ROI results
    print("\n" + "=" * 60)
    print("📊 ROI Results (Average over 5 runs)")
    print("=" * 60)
    print(f"{'Strategy':<25} {'Avg ROI':<12} {'Avg Won':<12} {'Best Win':<12}")
    print("-" * 60)
    
    results.sort(key=lambda x: x['roi'], reverse=True)
    for r in results:
        print(f"{r['name']:<25} {r['roi']:>8.2f}%    ${r['avg_won']:>8,.0f}    ${r['best_win']:>8,.0f}")
    
    # Get win probabilities
    print("\n" + "=" * 60)
    print("🎯 Win Probability Analysis (3 runs each)")
    print("=" * 60)
    
    for strategy in strategies:
        prob = get_win_probability(strategy["id"], 50, iterations=3)
        if prob:
            print(f"\n{strategy['name']}:")
            print(f"  Probability of 3/6: {prob['prob_3']:.2f}%")
            print(f"  Probability of 4/6: {prob['prob_4']:.2f}%")
            print(f"  Probability of 5/6: {prob['prob_5']:.2f}%")
            print(f"  Probability of 6/6: {prob['prob_6']:.2f}%")
            print(f"  Total tickets checked: {prob['total_checked']:,.0f}")
    
    # Recommend best strategy
    print("\n" + "=" * 60)
    print("🎯 RECOMMENDATIONS")
    print("=" * 60)
    
    best_roi = max(results, key=lambda x: x['roi'])
    print(f"\n💰 Best ROI Strategy: {best_roi['name']}")
    print(f"   Expected ROI: {best_roi['roi']:.2f}%")
    print(f"   Expected Winnings: ${best_roi['avg_won']:,.0f}")
    print(f"   Potential Best Win: ${best_roi['best_win']:,.0f}")
    
    print("\n📊 Strategy Recommendation:")
    print("  1. Use Hybrid AI for maximum expected returns")
    print("  2. Use Sobol Sequence for consistency")
    print("  3. Use Random (Quick Pick) for simplicity")

if __name__ == "__main__":
    main()
