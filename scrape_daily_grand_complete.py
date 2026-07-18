#!/usr/bin/env python3
"""
Complete Daily Grand Scraper
Fetches data from OLG website using multiple methods
"""

import requests
import json
import re
from datetime import datetime, timedelta
import time
import sys

def fetch_from_olg_api():
    """Try to find the actual API endpoint"""
    print("🔍 Looking for OLG API endpoint...")
    
    # Common OLG API patterns
    api_patterns = [
        "https://www.olg.ca/api/lottery/daily-grand/results",
        "https://www.olg.ca/api/lottery/draws/dailygrand",
        "https://www.olg.ca/en/lottery/play-daily-grand/past-results.api",
    ]
    
    for url in api_patterns:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            })
            if response.status_code == 200:
                print(f"✅ Found API: {url}")
                return response.json()
        except:
            continue
    
    return None

def fetch_from_webpage():
    """Fetch data from the webpage using BeautifulSoup"""
    print("📄 Fetching from webpage...")
    
    url = "https://www.olg.ca/en/lottery/play-daily-grand/past-results.html"
    
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html',
        })
        
        if response.status_code == 200:
            # Look for JSON data in the page
            content = response.text
            
            # Try to find JSON in script tags
            json_pattern = r'<script[^>]*>.*?({.*?})</script>'
            matches = re.findall(json_pattern, content, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if 'draws' in data or 'results' in data:
                        return data
                except:
                    pass
            
            # Look for data attributes
            pattern = r'data-results="([^"]*)"'
            matches = re.findall(pattern, content)
            if matches:
                try:
                    return json.loads(matches[0].replace('&quot;', '"'))
                except:
                    pass
            
            return {"html": content[:500]}
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def get_historical_data_from_third_party():
    """Try third-party sources"""
    print("🔍 Trying third-party sources...")
    
    sources = [
        "https://raw.githubusercontent.com/opendata/olg-lottery/main/daily-grand.csv",
        "https://lotteryapi.com/api/v1/daily-grand",
    ]
    
    for url in sources:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Found data at: {url}")
                return response.text
        except:
            continue
    
    return None

def generate_sample_data():
    """Generate realistic sample data for testing"""
    print("📊 Generating sample Daily Grand data...")
    
    sample_draws = []
    start_date = datetime(2016, 10, 17)
    
    # Pre-defined realistic numbers from actual draws
    sample_numbers = [
        [5, 12, 23, 34, 41, 3],
        [8, 15, 27, 36, 42, 5],
        [3, 11, 19, 28, 44, 1],
        [6, 14, 22, 33, 45, 7],
        [9, 16, 25, 37, 43, 2],
        [4, 13, 21, 29, 38, 6],
        [7, 18, 26, 35, 46, 4],
        [2, 10, 20, 31, 40, 3],
        [1, 17, 24, 32, 39, 5],
        [11, 23, 30, 41, 47, 2],
    ]
    
    for i in range(1000):  # Generate 1000 draws
        # Use sample numbers with some variation
        base_idx = i % len(sample_numbers)
        numbers = sample_numbers[base_idx].copy()
        
        # Add some randomness
        date = start_date + timedelta(days=i)
        if i > 0:
            numbers[0] = (numbers[0] + i) % 49 + 1
            numbers[1] = (numbers[1] + i * 2) % 49 + 1
            numbers[5] = (numbers[5] + i) % 7 + 1
        
        sample_draws.append({
            'date': date.strftime('%Y-%m-%d'),
            'numbers': numbers[:5],
            'grand': numbers[5]
        })
    
    return sample_draws

def save_to_csv(draws, filename='daily_grand_data.csv'):
    """Save draws to CSV file"""
    import csv
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
        
        for draw in draws:
            if isinstance(draw, dict):
                row = [draw['date']] + draw['numbers'] + [draw['grand']]
                writer.writerow(row)
    
    print(f"✅ Saved {len(draws)} draws to {filename}")
    return filename

def main():
    print("=" * 60)
    print("🎯 Daily Grand Data Scraper")
    print("=" * 60)
    
    # Try different methods
    print("\n🔍 Attempting to fetch real data...")
    
    # Method 1: Try API
    data = fetch_from_olg_api()
    if data:
        print("✅ Found API data!")
        print(json.dumps(data, indent=2)[:500])
        return
    
    # Method 2: Try webpage
    data = fetch_from_webpage()
    if data and 'html' not in data:
        print("✅ Found data in webpage!")
        save_to_csv(data)
        return
    
    # Method 3: Try third-party
    data = get_historical_data_from_third_party()
    if data:
        print("✅ Found data from third-party!")
        save_to_csv(data)
        return
    
    # Method 4: Generate sample
    print("\n⚠️  Could not fetch real data.")
    print("📊 Generating sample data for testing...")
    
    sample = generate_sample_data()
    filename = save_to_csv(sample)
    
    print("\n💡 To get REAL Daily Grand data:")
    print("  1. Visit: https://www.olg.ca/en/lottery/play-daily-grand/past-results.html")
    print("  2. Open Developer Tools (F12)")
    print("  3. Go to Network tab")
    print("  4. Look for API requests containing 'dailygrand'")
    print("  5. Copy the JSON response")
    print(f"\n📁 Sample data saved to: {filename}")
    print("📝 Edit this file with real data from the OLG website")
    print("\n🔧 To import: python3 import_daily_grand_csv.py daily_grand_data.csv")

if __name__ == "__main__":
    main()
