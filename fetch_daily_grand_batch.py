#!/usr/bin/env python3
"""
Fetch Daily Grand data from OLG API in batches
"""

import requests
import json
import csv
from datetime import datetime, timedelta

def fetch_daily_grand(start_date, end_date):
    """Fetch Daily Grand data from OLG API"""
    
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
            print(f"❌ Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
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
        print(f"❌ Error parsing: {e}")
    
    return draws

def main():
    print("=" * 60)
    print("🎯 Fetch Daily Grand Data")
    print("=" * 60)
    
    # Date range - Daily Grand started Oct 17, 2016
    start_date = "2016-10-17"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Fetching: {start_date} to {end_date}")
    
    data = fetch_daily_grand(start_date, end_date)
    
    if data:
        draws = parse_draws(data)
        if draws:
            print(f"\n✅ Found {len(draws)} draws")
            
            # Save to CSV
            filename = 'daily_grand_data.csv'
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
                writer.writeheader()
                writer.writerows(draws)
            
            print(f"✅ Saved to {filename}")
            print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
        else:
            print("❌ No draws found")
    else:
        print("❌ Failed to fetch data")

if __name__ == "__main__":
    main()
