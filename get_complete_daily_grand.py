#!/usr/bin/env python3
"""
Complete Daily Grand Data Collection
Fetches from multiple sources to get 2016-2026 data
"""

import requests
import csv
import json
import time
from datetime import datetime
import sys

def fetch_from_lottonumbers(year):
    """Try to fetch from lottonumbers.com with better parsing"""
    print(f"  🔍 Trying lottonumbers.com for {year}...")
    
    url = f"https://ca.lottonumbers.com/daily-grand/numbers/{year}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
        
        # Try to find JSON data in the page
        content = response.text
        
        # Look for results in the HTML
        import re
        # Find all date patterns
        dates = re.findall(r'<td[^>]*date-row[^>]*>.*?<br>(.*?)</td>', content, re.DOTALL)
        # Find all number patterns
        numbers = re.findall(r'<li class="ball[^"]*">(\d+)</li>', content)
        
        if not dates or not numbers:
            return []
        
        draws = []
        # Process each date with its numbers
        num_idx = 0
        for date_str in dates:
            date_str = date_str.strip()
            try:
                # Parse date like "December 29 2025"
                for fmt in ['%B %d %Y', '%b %d %Y', '%d %B %Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        draw_date = date_obj.strftime('%Y-%m-%d')
                        break
                    except:
                        continue
                else:
                    continue
                
                # Get 6 numbers for this draw
                if num_idx + 6 > len(numbers):
                    break
                
                draw_nums = numbers[num_idx:num_idx+6]
                num_idx += 6
                
                draws.append({
                    'Date': draw_date,
                    'Num1': draw_nums[0],
                    'Num2': draw_nums[1],
                    'Num3': draw_nums[2],
                    'Num4': draw_nums[3],
                    'Num5': draw_nums[4],
                    'Grand': draw_nums[5]
                })
            except:
                continue
        
        return draws
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []

def use_known_data():
    """Use known data we've already collected"""
    print("\n📊 Using previously collected data...")
    
    # Data we have from various sources
    known_draws = [
        # 2025 Data (from lottonumbers.com)
        {"Date": "2025-12-29", "Num1": "6", "Num2": "22", "Num3": "27", "Num4": "32", "Num5": "47", "Grand": "4"},
        {"Date": "2025-12-25", "Num1": "24", "Num2": "30", "Num3": "33", "Num4": "38", "Num5": "44", "Grand": "3"},
        {"Date": "2025-12-22", "Num1": "13", "Num2": "25", "Num3": "36", "Num4": "41", "Num5": "44", "Grand": "5"},
        {"Date": "2025-12-18", "Num1": "4", "Num2": "5", "Num3": "31", "Num4": "36", "Num5": "47", "Grand": "4"},
        {"Date": "2025-12-15", "Num1": "5", "Num2": "12", "Num3": "31", "Num4": "44", "Num5": "46", "Grand": "3"},
        {"Date": "2025-12-11", "Num1": "20", "Num2": "22", "Num3": "28", "Num4": "33", "Num5": "41", "Grand": "1"},
        {"Date": "2025-12-08", "Num1": "6", "Num2": "23", "Num3": "31", "Num4": "32", "Num5": "37", "Grand": "6"},
        {"Date": "2025-12-04", "Num1": "11", "Num2": "12", "Num3": "36", "Num4": "37", "Num5": "42", "Grand": "2"},
        {"Date": "2025-12-01", "Num1": "4", "Num2": "24", "Num3": "43", "Num4": "44", "Num5": "45", "Grand": "5"},
        {"Date": "2025-11-27", "Num1": "5", "Num2": "8", "Num3": "21", "Num4": "36", "Num5": "43", "Grand": "2"},
        {"Date": "2025-11-24", "Num1": "8", "Num2": "26", "Num3": "27", "Num4": "33", "Num5": "47", "Grand": "2"},
        {"Date": "2025-11-20", "Num1": "2", "Num2": "5", "Num3": "8", "Num4": "36", "Num5": "46", "Grand": "6"},
        {"Date": "2025-11-17", "Num1": "11", "Num2": "12", "Num3": "24", "Num4": "33", "Num5": "39", "Grand": "3"},
        {"Date": "2025-11-13", "Num1": "7", "Num2": "27", "Num3": "28", "Num4": "39", "Num5": "43", "Grand": "2"},
        {"Date": "2025-11-10", "Num1": "2", "Num2": "10", "Num3": "21", "Num4": "37", "Num5": "40", "Grand": "3"},
        {"Date": "2025-11-06", "Num1": "3", "Num2": "10", "Num3": "17", "Num4": "21", "Num5": "28", "Grand": "3"},
        {"Date": "2025-11-03", "Num1": "2", "Num2": "6", "Num3": "15", "Num4": "29", "Num5": "34", "Grand": "1"},
        {"Date": "2025-10-30", "Num1": "7", "Num2": "25", "Num3": "38", "Num4": "39", "Num5": "48", "Grand": "1"},
        {"Date": "2025-10-27", "Num1": "16", "Num2": "37", "Num3": "42", "Num4": "45", "Num5": "46", "Grand": "1"},
        {"Date": "2025-10-23", "Num1": "3", "Num2": "5", "Num3": "10", "Num4": "34", "Num5": "39", "Grand": "4"},
        {"Date": "2025-10-20", "Num1": "2", "Num2": "22", "Num3": "25", "Num4": "35", "Num5": "43", "Grand": "7"},
        {"Date": "2025-10-16", "Num1": "1", "Num2": "6", "Num3": "19", "Num4": "25", "Num5": "33", "Grand": "6"},
        {"Date": "2025-10-13", "Num1": "5", "Num2": "21", "Num3": "25", "Num4": "32", "Num5": "35", "Grand": "7"},
        {"Date": "2025-10-09", "Num1": "4", "Num2": "24", "Num3": "26", "Num4": "45", "Num5": "48", "Grand": "6"},
        {"Date": "2025-10-06", "Num1": "14", "Num2": "18", "Num3": "19", "Num4": "39", "Num5": "49", "Grand": "2"},
        {"Date": "2025-10-02", "Num1": "1", "Num2": "4", "Num3": "18", "Num4": "28", "Num5": "35", "Grand": "1"},
        # Add more months as you find them
    ]
    
    return known_draws

def main():
    print("=" * 60)
    print("🎯 Complete Daily Grand Data Collection")
    print("=" * 60)
    
    all_draws = []
    
    # Try to fetch from lottonumbers.com for each year
    print("\n📥 Trying to fetch from lottonumbers.com...")
    for year in range(2016, 2027):
        draws = fetch_from_lottonumbers(year)
        if draws:
            print(f"  ✅ {year}: {len(draws)} draws")
            all_draws.extend(draws)
        else:
            print(f"  ⚠️  {year}: No data found")
        time.sleep(1)
    
    # If we didn't get enough data, use known data
    if len(all_draws) < 100:
        print("\n📥 Using known data sources...")
        known = use_known_data()
        all_draws.extend(known)
    
    # Remove duplicates
    seen = set()
    unique_draws = []
    for draw in all_draws:
        key = draw['Date']
        if key not in seen:
            seen.add(key)
            unique_draws.append(draw)
    
    if unique_draws:
        unique_draws.sort(key=lambda x: x['Date'])
        
        print(f"\n📊 Total unique draws: {len(unique_draws)}")
        print(f"📅 Date range: {unique_draws[0]['Date']} to {unique_draws[-1]['Date']}")
        
        # Save to CSV
        filename = 'daily_grand_complete.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
            writer.writeheader()
            writer.writerows(unique_draws)
        
        print(f"✅ Saved to {filename}")
        print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
        
        # Show sample
        print("\n📋 Latest 10 draws:")
        for draw in unique_draws[-10:]:
            print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
        
        # Count by year
        from collections import Counter
        years = Counter([d['Date'][:4] for d in unique_draws])
        print("\n📊 Draws by year:")
        for year in sorted(years.keys()):
            print(f"  {year}: {years[year]} draws")
    else:
        print("❌ No data collected")

if __name__ == "__main__":
    main()
