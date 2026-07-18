#!/usr/bin/env python3
"""
Fetch Daily Grand data for all available months
Since the API goes back to July 2025
"""

import requests
import json
import csv
from datetime import datetime, timedelta
import time

def fetch_month(year, month):
    """Fetch Daily Grand data for a specific month"""
    
    # Format dates
    start_date = f"{year}-{month:02d}-01"
    # Calculate last day of month
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.olg.ca/'
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
    print("🎯 Fetching All Daily Grand Months")
    print("=" * 60)
    
    all_draws = []
    successful_months = 0
    
    # Daily Grand API only goes back to July 2025
    # Let's try from July 2025 to current month
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
            time.sleep(1)
    
    if all_draws:
        print(f"\n✅ Total: {len(all_draws)} draws from {successful_months} months")
        
        # Save to CSV
        filename = 'daily_grand_all_months.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
            writer.writeheader()
            writer.writerows(all_draws)
        
        print(f"✅ Saved to {filename}")
        
        # Show latest draws
        print("\n📊 Latest draws:")
        for draw in all_draws[-5:]:
            print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
        
        print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
    else:
        print("❌ No draws found")

if __name__ == "__main__":
    main()
