#!/usr/bin/env python3
"""
Import Daily Grand historical data
Source: OLG (Ontario Lottery and Gaming)
"""

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import os

DB_URL = "mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
engine = create_engine(DB_URL)

def scrape_daily_grand_olg():
    """Scrape Daily Grand results from OLG website"""
    print("📥 Fetching Daily Grand data from OLG...")
    
    # OLG Daily Grand past results page
    url = "https://www.olg.ca/en/lottery/play-daily-grand/past-results.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            print("✅ Successfully connected to OLG")
            # Parse HTML would go here
            # For now, let's check if there's a data API
            return None
        else:
            print(f"❌ Failed to fetch: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_daily_grand_from_api():
    """Try to get Daily Grand data from public API"""
    print("🔍 Searching for Daily Grand data sources...")
    
    # Try known data sources
    sources = [
        "https://raw.githubusercontent.com/datasets/lottery-daily-grand/main/data.csv",
        "https://data.olg.ca/api/daily-grand/results",
    ]
    
    for url in sources:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Found data at: {url}")
                return response.text
        except:
            continue
    
    print("❌ No public data sources found")
    return None

def sample_daily_grand_data():
    """Create sample Daily Grand data (real data starts Oct 2016)"""
    print("📊 Creating sample Daily Grand data (2016-2026)...")
    
    sample_data = [
        # Year, Grand Prize winners
        (2016, 1),  # First year, 1 winner
        (2017, 2),
        (2018, 3),
        (2019, 4),
        (2020, 5),
        (2021, 6),
        (2022, 7),
        (2023, 8),
        (2024, 9),
        (2025, 10),
    ]
    
    print("\n📈 Daily Grand Winners Over Time:")
    print(f"{'Year':<10} {'Winners':<15}")
    print("-" * 25)
    for year, winners in sample_data:
        print(f"{year:<10} {winners:<15}")
    
    return sample_data

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 Daily Grand Data Import")
    print("=" * 50)
    
    # Check existing data sources
    data = get_daily_grand_from_api()
    
    if data:
        print("✅ Data found!")
    else:
        print("⚠️  No Daily Grand data found in public sources")
        print("\n💡 Options:")
        print("  1. Manual entry from OLG website")
        print("  2. Use sample data for analysis")
        print("  3. Wait for dataset availability")
        
        # Show sample data anyway
        sample_daily_grand_data()
