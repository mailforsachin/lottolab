#!/usr/bin/env python3
"""
Scrape Daily Grand results from ca.lottonumbers.com
This site has data from 2016 to present
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re

def scrape_year(year):
    """Scrape Daily Grand results for a specific year"""
    print(f"📅 Scraping {year}...")
    
    url = f"https://ca.lottonumbers.com/daily-grand/numbers/{year}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        draws = []
        
        # Find the results table
        table = soup.find('table', class_='mobFormat past-results')
        if not table:
            table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')
            
            for row in rows:
                # Skip header rows
                if row.find('th'):
                    continue
                
                # Look for date row
                date_cell = row.find('td', class_='date-row')
                if not date_cell:
                    continue
                
                # Get date
                date_text = date_cell.get_text(strip=True)
                date_parts = date_text.split('\n')
                
                # Parse date
                if len(date_parts) >= 2:
                    date_str = date_parts[1].strip()
                    try:
                        # Try to parse date like "December 29 2025"
                        from datetime import datetime
                        draw_date = datetime.strptime(date_str, '%B %d %Y').strftime('%Y-%m-%d')
                    except:
                        try:
                            draw_date = datetime.strptime(date_str, '%b %d %Y').strftime('%Y-%m-%d')
                        except:
                            continue
                else:
                    continue
                
                # Get numbers
                balls_row = row.find('td', class_='balls-row')
                if not balls_row:
                    continue
                
                balls = balls_row.find_all('li', class_='ball')
                if len(balls) < 6:
                    continue
                
                # Extract numbers (first 5 are main, 6th is bonus/grand)
                numbers = []
                for ball in balls[:5]:
                    numbers.append(ball.get_text(strip=True))
                
                grand = balls[5].get_text(strip=True) if len(balls) > 5 else ''
                
                draws.append({
                    'Date': draw_date,
                    'Num1': numbers[0],
                    'Num2': numbers[1],
                    'Num3': numbers[2],
                    'Num4': numbers[3],
                    'Num5': numbers[4],
                    'Grand': grand
                })
        
        print(f"  ✅ Found {len(draws)} draws for {year}")
        return draws
        
    except Exception as e:
        print(f"  ❌ Error scraping {year}: {e}")
        return []

def scrape_all_years():
    """Scrape all available years"""
    print("=" * 60)
    print("🎯 Scraping Daily Grand Data from ca.lottonumbers.com")
    print("=" * 60)
    
    all_draws = []
    
    # Daily Grand started in 2016
    for year in range(2016, 2027):
        draws = scrape_year(year)
        all_draws.extend(draws)
        time.sleep(1)  # Be nice to the server
    
    if all_draws:
        # Sort by date
        all_draws.sort(key=lambda x: x['Date'])
        
        print(f"\n📊 Total draws: {len(all_draws)}")
        print(f"📅 Date range: {all_draws[0]['Date']} to {all_draws[-1]['Date']}")
        
        # Save to CSV
        filename = 'daily_grand_complete.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
            writer.writeheader()
            writer.writerows(all_draws)
        
        print(f"✅ Saved to {filename}")
        print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
        
        # Show sample
        print("\n📋 Latest draws:")
        for draw in all_draws[-5:]:
            print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
        
    else:
        print("❌ No data scraped")

if __name__ == "__main__":
    scrape_all_years()
