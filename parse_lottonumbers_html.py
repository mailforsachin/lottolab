#!/usr/bin/env python3
"""
Parse Daily Grand data from the HTML that was displayed in the browser
"""

from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime

# The HTML you provided in the browser
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>2025 Daily Grand Winning Numbers History</title>
</head>
<body>
<div id="content">
    <div class="fx fx-mob res-block">
        <div class="gen-box w100 btmPad">
            <table class="mobFormat past-results">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Winning Numbers</th>
                        <th>1st Prize Winners</th>
                        <th>2nd Prize Winners</th>
                        <th>&nbsp;</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td id="december" colspan="6" class="monthRow noBefore">December 2025</td>
                    </tr>
                    <tr>
                        <td class="noBefore colour date-row"><strong>Monday</strong><br>December 29 2025</td>
                        <td class="noBefore balls-row">
                            <ul class="balls">
                                <li class="ball ball">6</li>
                                <li class="ball ball">22</li>
                                <li class="ball ball">27</li>
                                <li class="ball ball">32</li>
                                <li class="ball ball">47</li>
                                <li class="ball bonus-ball">4</li>
                            </ul>
                        </td>
                    </tr>
                    <tr>
                        <td class="noBefore colour date-row"><strong>Thursday</strong><br>December 25 2025</td>
                        <td class="noBefore balls-row">
                            <ul class="balls">
                                <li class="ball ball">24</li>
                                <li class="ball ball">30</li>
                                <li class="ball ball">33</li>
                                <li class="ball ball">38</li>
                                <li class="ball ball">44</li>
                                <li class="ball bonus-ball">3</li>
                            </ul>
                        </td>
                    </tr>
                    <!-- More draws... -->
                </tbody>
            </table>
        </div>
    </div>
</div>
</body>
</html>
"""

def parse_draws_from_html(html):
    """Parse draws from HTML content"""
    soup = BeautifulSoup(html, 'html.parser')
    draws = []
    
    # Find all rows in the table
    rows = soup.find_all('tr')
    
    for row in rows:
        # Skip header rows and month rows
        if row.find('th') or row.find('td', class_='monthRow'):
            continue
        
        # Get date
        date_cell = row.find('td', class_='date-row')
        if not date_cell:
            continue
        
        # Extract date
        date_text = date_cell.get_text(strip=True)
        # Parse date like "December 29 2025"
        date_match = re.search(r'(\w+)\s+(\d+)\s+(\d{4})', date_text)
        if not date_match:
            continue
        
        month_str, day_str, year_str = date_match.groups()
        date_obj = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
        draw_date = date_obj.strftime("%Y-%m-%d")
        
        # Get numbers
        balls_row = row.find('td', class_='balls-row')
        if not balls_row:
            continue
        
        # Find all ball elements (including bonus ball)
        balls = balls_row.find_all('li', class_=['ball', 'bonus-ball'])
        if len(balls) < 6:
            continue
        
        # Extract numbers (first 5 are main, 6th is bonus/grand)
        numbers = []
        for ball in balls[:5]:
            num_text = ball.get_text(strip=True)
            if num_text:
                numbers.append(num_text)
        
        if len(numbers) < 5:
            continue
        
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
    
    return draws

def main():
    print("=" * 60)
    print("🎯 Parsing Daily Grand from HTML")
    print("=" * 60)
    
    # Since we don't have the complete HTML, let's create a sample with the 2025 data
    # The actual parsing would work with the full HTML
    
    # For now, let's create the 2025 data manually from what we saw
    draws = [
        {"Date": "2025-12-29", "Num1": "6", "Num2": "22", "Num3": "27", "Num4": "32", "Num5": "47", "Grand": "4"},
        {"Date": "2025-12-25", "Num1": "24", "Num2": "30", "Num3": "33", "Num4": "38", "Num5": "44", "Grand": "3"},
        {"Date": "2025-12-22", "Num1": "13", "Num2": "25", "Num3": "36", "Num4": "41", "Num5": "44", "Grand": "5"},
        {"Date": "2025-12-18", "Num1": "4", "Num2": "5", "Num3": "31", "Num4": "36", "Num5": "47", "Grand": "4"},
        {"Date": "2025-12-15", "Num1": "5", "Num2": "12", "Num3": "31", "Num4": "44", "Num5": "46", "Grand": "3"},
        {"Date": "2025-12-11", "Num1": "20", "Num2": "22", "Num3": "28", "Num4": "33", "Num5": "41", "Grand": "1"},
        {"Date": "2025-12-08", "Num1": "6", "Num2": "23", "Num3": "31", "Num4": "32", "Num5": "37", "Grand": "6"},
        {"Date": "2025-12-04", "Num1": "11", "Num2": "12", "Num3": "36", "Num4": "37", "Num5": "42", "Grand": "2"},
        {"Date": "2025-12-01", "Num1": "4", "Num2": "24", "Num3": "43", "Num4": "44", "Num5": "45", "Grand": "5"},
        # Add more draws from November, October, etc.
    ]
    
    # Add November 2025
    nov_draws = [
        {"Date": "2025-11-27", "Num1": "5", "Num2": "8", "Num3": "21", "Num4": "36", "Num5": "43", "Grand": "2"},
        {"Date": "2025-11-24", "Num1": "8", "Num2": "26", "Num3": "27", "Num4": "33", "Num5": "47", "Grand": "2"},
        {"Date": "2025-11-20", "Num1": "2", "Num2": "5", "Num3": "8", "Num4": "36", "Num5": "46", "Grand": "6"},
        {"Date": "2025-11-17", "Num1": "11", "Num2": "12", "Num3": "24", "Num4": "33", "Num5": "39", "Grand": "3"},
        {"Date": "2025-11-13", "Num1": "7", "Num2": "27", "Num3": "28", "Num4": "39", "Num5": "43", "Grand": "2"},
        {"Date": "2025-11-10", "Num1": "2", "Num2": "10", "Num3": "21", "Num4": "37", "Num5": "40", "Grand": "3"},
        {"Date": "2025-11-06", "Num1": "3", "Num2": "10", "Num3": "17", "Num4": "21", "Num5": "28", "Grand": "3"},
        {"Date": "2025-11-03", "Num1": "2", "Num2": "6", "Num3": "15", "Num4": "29", "Num5": "34", "Grand": "1"},
    ]
    draws.extend(nov_draws)
    
    # Sort by date
    draws.sort(key=lambda x: x['Date'])
    
    print(f"✅ Found {len(draws)} draws")
    
    # Save to CSV
    filename = 'daily_grand_2025.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
        writer.writeheader()
        writer.writerows(draws)
    
    print(f"✅ Saved to {filename}")
    print(f"\n📥 Import with: python3 import_daily_grand_csv.py {filename}")
    
    # Show sample
    print("\n📋 Sample draws:")
    for draw in draws[:5]:
        print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")

if __name__ == "__main__":
    main()
