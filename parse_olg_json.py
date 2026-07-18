#!/usr/bin/env python3
"""
Parse OLG API JSON data to CSV format for Daily Grand
"""

import json
import csv
from datetime import datetime

def parse_olg_data(data):
    """Parse OLG API response data and convert to CSV format"""
    
    draws = []
    
    # Extract draws from the JSON structure
    dailygrand = data.get('response', {}).get('winnings', {}).get('dailygrand', {})
    draw_list = dailygrand.get('draw', [])
    
    print(f"📊 Found {len(draw_list)} draws in the data")
    
    for draw in draw_list:
        draw_date = draw.get('date')
        
        # Get main numbers
        main = draw.get('main', {})
        regular = main.get('regular', '')
        bonus = main.get('bonus', '')
        
        # Parse regular numbers (comma-separated)
        if regular:
            numbers = regular.split(',')
            if len(numbers) >= 5:
                draw_data = {
                    'Date': draw_date,
                    'Num1': numbers[0].strip(),
                    'Num2': numbers[1].strip(),
                    'Num3': numbers[2].strip(),
                    'Num4': numbers[3].strip(),
                    'Num5': numbers[4].strip(),
                    'Grand': bonus.strip()
                }
                draws.append(draw_data)
    
    return draws

def save_to_csv(draws, filename='daily_grand_data.csv'):
    """Save draws to CSV file"""
    if not draws:
        print("❌ No draws found!")
        return
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Date', 'Num1', 'Num2', 'Num3', 'Num4', 'Num5', 'Grand'])
        writer.writeheader()
        writer.writerows(draws)
    
    print(f"✅ Saved {len(draws)} draws to {filename}")
    return filename

def main():
    print("=" * 60)
    print("🎯 OLG Daily Grand JSON Parser")
    print("=" * 60)
    
    # Your JSON data from the API
    json_data = '''{
    "response": {
        "statusCode": "0",
        "winnings": {
            "dailygrand": {
                "draw": [
                    {
                        "date": "2026-06-29",
                        "day": "Mon",
                        "main": {
                            "regular": "09,14,15,41,42",
                            "bonus": "06"
                        }
                    },
                    {
                        "date": "2026-06-25",
                        "day": "Thu",
                        "main": {
                            "regular": "08,23,24,40,42",
                            "bonus": "03"
                        }
                    },
                    {
                        "date": "2026-06-22",
                        "day": "Mon",
                        "main": {
                            "regular": "01,03,11,19,31",
                            "bonus": "03"
                        }
                    },
                    {
                        "date": "2026-06-18",
                        "day": "Thu",
                        "main": {
                            "regular": "25,31,32,33,41",
                            "bonus": "03"
                        }
                    },
                    {
                        "date": "2026-06-15",
                        "day": "Mon",
                        "main": {
                            "regular": "12,18,19,27,39",
                            "bonus": "07"
                        }
                    },
                    {
                        "date": "2026-06-11",
                        "day": "Thu",
                        "main": {
                            "regular": "04,06,12,21,38",
                            "bonus": "02"
                        }
                    },
                    {
                        "date": "2026-06-08",
                        "day": "Mon",
                        "main": {
                            "regular": "03,11,19,36,37",
                            "bonus": "05"
                        }
                    },
                    {
                        "date": "2026-06-04",
                        "day": "Thu",
                        "main": {
                            "regular": "05,25,29,30,45",
                            "bonus": "03"
                        }
                    },
                    {
                        "date": "2026-06-01",
                        "day": "Mon",
                        "main": {
                            "regular": "05,12,27,29,43",
                            "bonus": "06"
                        }
                    }
                ]
            }
        }
    }
}'''
    
    # Parse the JSON
    try:
        data = json.loads(json_data)
        draws = parse_olg_data(data)
        
        if draws:
            print(f"\n✅ Found {len(draws)} Daily Grand draws")
            print("\n📊 Sample data:")
            for draw in draws[:5]:
                print(f"  {draw['Date']}: {draw['Num1']},{draw['Num2']},{draw['Num3']},{draw['Num4']},{draw['Num5']} | Grand: {draw['Grand']}")
            
            # Save to CSV
            save_to_csv(draws, 'daily_grand_real_data.csv')
            
            print("\n📥 To import into LottoLab:")
            print("  python3 import_daily_grand_csv.py daily_grand_real_data.csv")
        else:
            print("❌ No draws parsed")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print("💡 Make sure you have valid JSON data")

if __name__ == "__main__":
    main()
