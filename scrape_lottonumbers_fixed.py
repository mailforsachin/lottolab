#!/usr/bin/env python3
"""
Scrape Daily Grand results from ca.lottonumbers.com
Fixed parser for the actual website structure
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime

def scrape_year(year):
    """Scrape Daily Grand results for a specific year"""
    print(f"📅 Scraping {year}...")
    
    url = f"https://ca.lottonumbers.com/daily-grand/numbers/{year}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        draws = []
        
        # Find all tables with results
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if this is the results table
            if 'past-results' in str(table.get('class', [])):
                rows = table.find_all('tr')
                
                current_month = None
                
                for row in rows:
                    # Check for month header
                    month_cell = row.find('td', class_='monthRow')
                    if month_cell:
                        month_text = month_cell.get_text(strip=True)
                        current_month = month_text
                        continue
                    
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    # Look for date cell
                    date_cell = row.find('td', class_='date-row')
                    if not date_cell:
                        continue
                    
                    # Get date
                    date_text = date_cell.get_text(strip=True)
                    # Extract date from "Monday\nDecember 29 2025" format
                    date_lines = date_text.split('\n')
                    date_str = None
                    
                    for line in date_lines:
                        line = line.strip()
                        if line and not line.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                            # Try to parse date
                            try:
                                # Try various date formats
                                for fmt in ['%B %d %Y', '%b %d %Y', '%d %B %Y']:
                                    try:
                                        date_obj = datetime.strptime(line, fmt)
                                        date_str = date_obj.strftime('%Y-%m-%d')
                                        break
                                    except:
                                        continue
                            except:
                                continue
                    
                    if not date_str:
                        continue
                    
                    # Get numbers
                    balls_row = row.find('td', class_='balls-row')
                    if not balls_row:
                        continue
                    
                    # Find all ball elements
                    balls = balls_row.find_all('li', class_='ball')
                    
                    if len(balls) < 6:
                        # Try finding the numbers in another way
                        ball_elements = balls_row.find_all('li')
                        if len(ball_elements) < 6:
                            continue
                        balls = ball_elements
                    
                    # Extract numbers (first 5 are main, 6th is bonus/grand)
                    numbers = []
                    for ball in balls[:5]:
                        num_text = ball.get_text(strip=True)
                        if num_text:
                            numbers.append(num_text)
                    
                    if len(numbers) < 5:
                        continue
                    
                    grand = balls[5].get_text(strip=True) if len(balls) > 5 else ''
                    
                    # Skip if any number is missing
                    if any(not n for n in numbers) or not grand:
                        continue
                    
                    draws.append({
                        'Date': date_str,
                        'Num1': numbers[0],
                        'Num2': numbers[1],
                        'Num3': numbers[2],
                        'Num4': numbers[3],
                        'Num5': numbers[4],
                        'Grand': grand
                    })
        
        if draws:
            print(f"  ✅ Found {len(draws)} draws for {year}")
        else:
            print(f"  ⚠️  No draws found for {year}")
        
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
        time.sleep(2)  # Be nice to the server
    
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
        print("\n📋 First 5 draws:")
        for draw in all_draws[:5]:
            print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
        
        print("\n📋 Latest 5 draws:")
        for draw in all_draws[-5:]:
            print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
        
    else:
        print("❌ No data scraped")
        print("\n💡 Alternative: Use the manual data from OLG website")

if __name__ == "__main__":
    scrape_all_years()
