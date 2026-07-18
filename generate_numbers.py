#!/usr/bin/env python3
"""
Generate optimal number combinations based on historical data and simulations
"""

import requests
import random
from collections import Counter
import json

BASE_URL = "https://lottolab.omchat.ovh/api/v1"

def get_hot_numbers():
    """Get the most frequent numbers from historical data"""
    response = requests.get(f"{BASE_URL}/draws/stats/frequencies")
    data = response.json()
    
    frequencies = data['frequencies']
    sorted_numbers = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    
    hot_numbers = [int(num) for num, count in sorted_numbers[:10]]
    cold_numbers = [int(num) for num, count in sorted_numbers[-10:]]
    
    return hot_numbers, cold_numbers

def generate_balanced_tickets(hot_numbers, cold_numbers, num_tickets=50):
    """Generate tickets with balanced hot/cold numbers"""
    tickets = []
    
    for i in range(num_tickets):
        # Choose strategy based on ticket number
        if i < num_tickets // 3:
            # Hot numbers strategy - mostly hot numbers
            pool = hot_numbers[:8]
            ticket = sorted(random.sample(pool, 6))
        elif i < 2 * num_tickets // 3:
            # Balanced strategy - mix of hot and cold
            hot_pool = random.sample(hot_numbers, 3)
            cold_pool = random.sample(cold_numbers, 3)
            ticket = sorted(hot_pool + cold_pool)
        else:
            # Random strategy - completely random
            ticket = sorted(random.sample(range(1, 50), 6))
        
        tickets.append(ticket)
    
    return tickets

def get_frequency_analysis():
    """Get frequency analysis from API"""
    response = requests.get(f"{BASE_URL}/draws/stats/frequencies")
    return response.json()

def analyze_tickets(tickets):
    """Analyze ticket distribution"""
    all_numbers = []
    for ticket in tickets:
        all_numbers.extend(ticket)
    
    counter = Counter(all_numbers)
    return counter

def main():
    print("=" * 60)
    print("🎯 Generating Optimal Number Combinations")
    print("=" * 60)
    
    # Get hot and cold numbers
    hot_numbers, cold_numbers = get_hot_numbers()
    
    print(f"\n🔥 Hot Numbers (most frequent): {hot_numbers}")
    print(f"❄️ Cold Numbers (least frequent): {cold_numbers}")
    
    # Generate tickets
    tickets = generate_balanced_tickets(hot_numbers, cold_numbers, 50)
    
    print("\n📊 Recommended Tickets for $100 Budget:")
    print("=" * 60)
    print(f"{'Ticket #':<10} {'Numbers':<30} {'Strategy':<15}")
    print("-" * 60)
    
    strategy_labels = ["Hot", "Balanced", "Random"]
    for i, ticket in enumerate(tickets, 1):
        strategy = "Hot" if i <= 16 else ("Balanced" if i <= 33 else "Random")
        print(f"#{i:<9} {str(ticket):<30} {strategy:<15}")
    
    # Analyze ticket distribution
    counter = analyze_tickets(tickets)
    print("\n📈 Number Distribution in Generated Tickets:")
    print("=" * 60)
    print(f"{'Number':<10} {'Frequency':<12} {'Status':<10}")
    print("-" * 60)
    
    for num in range(1, 50):
        freq = counter.get(num, 0)
        status = "🔥" if num in hot_numbers else ("❄️" if num in cold_numbers else "•")
        if freq > 0:
            print(f"{num:<10} {freq:<12} {status:<10}")
    
    print("\n🎯 RECOMMENDED TOP 5 TICKETS:")
    print("=" * 60)
    for i, ticket in enumerate(tickets[:5], 1):
        print(f"{i}. {ticket}")
    
    # Save tickets to file
    with open('recommended_tickets.json', 'w') as f:
        json.dump({
            'hot_numbers': hot_numbers,
            'cold_numbers': cold_numbers,
            'tickets': tickets,
            'date': str(datetime.now())
        }, f, indent=2)
    
    print("\n💾 Tickets saved to: recommended_tickets.json")

if __name__ == "__main__":
    from datetime import datetime
    main()
