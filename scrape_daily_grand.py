#!/usr/bin/env python3
"""
Scrape Daily Grand historical data from OLG website
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time

def scrape_daily_grand():
    """Scrape Daily Grand results from OLG"""
    print("📥 Fetching Daily Grand data from OLG...")
    
    # URL for Daily Grand past results
    url = "https://www.olg.ca/en/lottery/play-daily-grand/past-results.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for draw results in the page
        # This will need to be adjusted based on the actual page structure
        
        # Try to find tables with results
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    print(f"Found potential data: {[cell.text.strip() for cell in cells]}")
        
        # Look for JSON data in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'drawDate' in script.string:
                print("Found JSON data in script")
                # Try to extract JSON
                try:
                    json_match = re.search(r'\{.*?\}', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        print(json.dumps(data, indent=2)[:500])
                except:
                    pass
        
        print("✅ Page scraped successfully")
        print("💡 Check the page structure at: https://www.olg.ca/en/lottery/play-daily-grand/past-results.html")
        print("📝 You may need to manually extract the data or use browser DevTools")
        
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_manual_template():
    """Create a template for manual data entry"""
    print("\n📝 Manual Data Entry Template")
    print("=" * 50)
    print("Format: Date,Num1,Num2,Num3,Num4,Num5,Grand")
    print("Example: 2026-07-18,5,12,23,34,41,3")
    print("\n📊 To enter data, create a CSV file:")
    print("  Date,Num1,Num2,Num3,Num4,Num5,Grand")
    print("  2016-10-17,5,12,23,34,41,3")
    print("  2016-10-18,8,15,27,36,42,5")
    print("  ...")
    print("\n💡 Then run: python3 import_daily_grand_csv.py daily_grand_data.csv")

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 Daily Grand Data Scraper")
    print("=" * 50)
    
    # Try to scrape
    data = scrape_daily_grand()
    
    # If scraping fails, provide manual template
    if not data:
        create_manual_template()
