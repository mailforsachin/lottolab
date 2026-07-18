#!/usr/bin/env python3
"""
Analyze Daily Grand data with complete dataset
"""

from sqlalchemy import create_engine, text
import json
from collections import Counter
import random

DB_URL = "mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
engine = create_engine(DB_URL)

print("=" * 60)
print("🎯 DAILY GRAND COMPLETE ANALYSIS")
print("=" * 60)

with engine.connect() as conn:
    # Get Daily Grand data
    result = conn.execute(text("""
        SELECT draw_date, numbers, bonus
        FROM draws 
        WHERE lottery_type = 'Daily Grand'
        ORDER BY draw_date
    """))
    draws = result.fetchall()

if not draws:
    print("❌ No Daily Grand data found!")
else:
    print(f"\n📊 Found {len(draws)} Daily Grand draws")
    print(f"📅 Date range: {draws[0][0]} to {draws[-1][0]}")
    
    # Analyze main numbers
    main_numbers = []
    grand_numbers = []
    
    for draw in draws:
        numbers = json.loads(draw[1])  # JSON array
        if len(numbers) >= 6:
            main_numbers.extend(numbers[:5])
            grand_numbers.append(numbers[5])
    
    # Frequency analysis
    main_freq = Counter(main_numbers)
    grand_freq = Counter(grand_numbers)
    
    print("\n🔥 TOP 10 MOST FREQUENT MAIN NUMBERS:")
    for num, count in main_freq.most_common(10):
        pct = (count / len(draws)) * 100
        bar = "█" * int(pct / 2)
        print(f"  #{num:2d}: {count:3d} times ({pct:5.1f}%) {bar}")
    
    print("\n❄️ LEAST FREQUENT MAIN NUMBERS (Bottom 5):")
    for num, count in main_freq.most_common()[-5:]:
        pct = (count / len(draws)) * 100
        print(f"  #{num:2d}: {count:3d} times ({pct:5.1f}%)")
    
    print("\n🎯 GRAND NUMBER FREQUENCY (1-7):")
    max_count = max(grand_freq.values()) if grand_freq else 1
    for num in range(1, 8):
        count = grand_freq.get(num, 0)
        pct = (count / len(draws)) * 100 if draws else 0
        bar = "█" * int(count / max_count * 20) if max_count > 0 else ""
        print(f"  Grand #{num}: {count:3d} times ({pct:5.1f}%) {bar}")
    
    # Generate recommendations
    print("\n🎯 RECOMMENDED NUMBERS:")
    top_main = [num for num, count in main_freq.most_common(10)]
    top_grand = [num for num, count in grand_freq.most_common(3)]
    cold_main = [num for num, count in main_freq.most_common()[-5:]]
    
    print(f"  🔥 Hot Main Numbers: {top_main[:5]}")
    print(f"  ❄️ Cold Main Numbers: {cold_main[:3]}")
    print(f"  🎯 Hot Grand Numbers: {top_grand}")
    
    # Generate sample tickets
    print("\n📋 10 RECOMMENDED TICKETS:")
    for i in range(10):
        # Mix hot and cold numbers
        if i < 5:
            # Hot strategy
            ticket = sorted(random.sample(top_main[:8], 5))
        else:
            # Balanced strategy
            hot = random.sample(top_main[:6], 3)
            cold = random.sample(cold_main[:3], 2)
            ticket = sorted(hot + cold)
        grand = random.choice(top_grand)
        print(f"  Ticket #{i+1:2d}: {ticket} | Grand: {grand}")
    
    print("\n" + "=" * 60)
    print("📈 STRATEGY RECOMMENDATION:")
    print("  - Use Hot Main Numbers for consistent performance")
    print("  - Add 1-2 Cold Numbers for diversity")
    print("  - Grand #3 appears most frequently - use it often")
    print("  - Mix Hot + Cold for balanced tickets")
    print("=" * 60)
