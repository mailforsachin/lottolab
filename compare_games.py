#!/usr/bin/env python3
"""
Compare Lotto 6/49 vs Daily Grand
"""

from sqlalchemy import create_engine, text
import json
from collections import Counter

DB_URL = "mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
engine = create_engine(DB_URL)

print("=" * 60)
print("🎯 LOTTO 6/49 vs DAILY GRAND COMPARISON")
print("=" * 60)

# Use a single connection for all queries
with engine.connect() as conn:
    # Get Lotto 6/49 stats
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as draws,
            MIN(draw_date) as first,
            MAX(draw_date) as last
        FROM draws 
        WHERE lottery_type = '6/49'
    """))
    lotto = result.fetchone()
    
    # Get Daily Grand stats
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as draws,
            MIN(draw_date) as first,
            MAX(draw_date) as last
        FROM draws 
        WHERE lottery_type = 'Daily Grand'
    """))
    daily = result.fetchone()
    
    # Get Daily Grand frequency
    result = conn.execute(text("""
        SELECT numbers FROM draws WHERE lottery_type = 'Daily Grand'
    """))
    draws = result.fetchall()

print(f"\n{'Metric':<20} {'Lotto 6/49':<20} {'Daily Grand':<20}")
print("-" * 60)
print(f"{'Total Draws':<20} {lotto[0]:<20} {daily[0]:<20}")
print(f"{'First Draw':<20} {lotto[1].strftime('%Y-%m-%d') if lotto[1] else 'N/A':<20} {daily[1].strftime('%Y-%m-%d') if daily[1] else 'N/A':<20}")
print(f"{'Last Draw':<20} {lotto[2].strftime('%Y-%m-%d') if lotto[2] else 'N/A':<20} {daily[2].strftime('%Y-%m-%d') if daily[2] else 'N/A':<20}")
print(f"{'Years':<20} {lotto[2].year - lotto[1].year + 1 if lotto[1] and lotto[2] else 0:<20} {daily[2].year - daily[1].year + 1 if daily[1] and daily[2] else 0:<20}")

# Analyze Daily Grand numbers
main_numbers = []
grand_numbers = []
for draw in draws:
    nums = json.loads(draw[0])
    if len(nums) >= 6:
        main_numbers.extend(nums[:5])
        grand_numbers.append(nums[5])

main_freq = Counter(main_numbers)
grand_freq = Counter(grand_numbers)

print("\n🎯 DAILY GRAND TOP 10 MAIN NUMBERS:")
for num, count in main_freq.most_common(10):
    pct = (count / len(draws)) * 100 if draws else 0
    print(f"  #{num:2d}: {count:3d} times ({pct:5.1f}%)")

print("\n🎯 DAILY GRAND GRAND NUMBER FREQUENCY:")
for num in range(1, 8):
    count = grand_freq.get(num, 0)
    pct = (count / len(draws)) * 100 if draws else 0
    bar = "█" * int(count / max(grand_freq.values()) * 20) if grand_freq else ""
    print(f"  Grand #{num}: {count:3d} times ({pct:5.1f}%) {bar}")

best_main = [str(num) for num, _ in main_freq.most_common(5)]
best_grand = max(grand_freq.items(), key=lambda x: x[1])[0]

print("\n📈 RECOMMENDATION:")
print(f"  Best Main Numbers: {', '.join(best_main)}")
print(f"  Best Grand Number: {best_grand}")
print(f"  Daily Grand has better jackpot odds (1 in 13.3M vs 1 in 14M)")
print("=" * 60)
