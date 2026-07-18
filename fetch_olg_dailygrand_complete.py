#!/usr/bin/env python3
"""
Fetch Daily Grand data from OLG API using browser session
Since we can access it from the browser, we'll use the same headers
"""

import requests
import json
import csv
from datetime import datetime, timedelta

def fetch_month(year, month):
    """Fetch Daily Grand data for a specific month using OLG API"""
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year}-12-31"
    else:
        next_month = datetime(year, month + 1, 1)
        end_date = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = "https://gateway.www.olg.ca/feeds/past-winning-numbers"
    
    params = {
        'game': 'dailygrand',
        'startDate': start_date,
        'endDate': end_date
    }
    
    headers = {
        'Origin': 'https://www.olg.ca',
        'Referer': 'https://www.olg.ca/',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ❌ Error {response.status_code} for {start_date}")
            return None
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None

def parse_draws(data):
    """Parse draws from API response"""
    draws = []
    
    try:
        dailygrand = data.get('response', {}).get('winnings', {}).get('dailygrand', {})
        draw_list = dailygrand.get('draw', [])
        
        for draw in draw_list:
            draw_date = draw.get('date')
            main = draw.get('main', {})
            regular = main.get('regular', '')
            bonus = main.get('bonus', '')
            
            if regular:
                numbers = regular.split(',')
                if len(numbers) >= 5:
                    draws.append({
                        'Date': draw_date,
                        'Num1': numbers[0].strip(),
                        'Num2': numbers[1].strip(),
                        'Num3': numbers[2].strip(),
                        'Num4': numbers[3].strip(),
                        'Num5': numbers[4].strip(),
                        'Grand': bonus.strip()
                    })
    except Exception as e:
        print(f"  ❌ Error parsing: {e}")
    
    return draws

def main():
    print("=" * 60)
    print("🎯 Fetching Daily Grand from OLG API")
    print("=" * 60)
    
    all_draws = []
    successful_months = 0
    
    # Try to fetch from July 2025 to current month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    for year in range(2025, current_year + 1):
        start_month = 7 if year == 2025 else 1
        end_month = current_month if year == current_year else 12
        
        for month in range(start_month, end_month + 1):
            print(f"\n📅 Fetching {year}-{month:02d}...", end=" ")
            
            data = fetch_month(year, month)
            if data:
                draws = parse_draws(data)
                if draws:
                    print(f"✅ Found {len(draws)} draws")
                    all_draws.extend(draws)
                    successful_months += 1
                else:
                    print("⚠️  No draws found")
            else:
                print("❌ Failed")
            
            # Be nice to the API
            import time
            time.sleep(1)
    
    if all_draws:
        # Sort by date
        all_draws.sort(key=lambda x: x['Date'])
        
        print(f"\n✅ Total: {len(all_draws)} draws from {successful_months} months")
        print(f"📅 Date range: {all_draws[0]['Date']} to {all_draws[-1]['Date']}")
        
        # Save to CSV
        filename = 'daily_grand_olg_complete.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
            writer.writeheader()
            writer.writerows(all_draws)
        
        print(f"✅ Saved to {filename}")
        print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
    else:
        print("❌ No draws found")

if __name__ == "__main__":
    main()
