#!/usr/bin/env python3
"""
Import Daily Grand data from CSV file
"""

import pandas as pd
import sys
from sqlalchemy import create_engine, text
from datetime import datetime
import json

DB_URL = "mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
engine = create_engine(DB_URL)

def import_csv(csv_file):
    print(f"📊 Importing Daily Grand data from: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Found {len(df)} rows")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    imported = 0
    skipped = 0
    
    with engine.connect() as conn:
        for idx, row in df.iterrows():
            try:
                # Parse date
                date_str = str(row['Date']).strip()
                draw_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Get numbers (5 numbers + Grand)
                numbers = [
                    int(row['Num1']),
                    int(row['Num2']),
                    int(row['Num3']),
                    int(row['Num4']),
                    int(row['Num5'])
                ]
                grand = int(row['Grand'])
                
                # Store as JSON (5 numbers + grand)
                full_numbers = numbers + [grand]
                
                # Check if already exists
                check = conn.execute(
                    text("SELECT id FROM draws WHERE draw_date = :date AND lottery_type = 'Daily Grand'"),
                    {'date': draw_date}
                ).first()
                
                if check:
                    skipped += 1
                    continue
                
                # Insert
                conn.execute(
                    text("""
                        INSERT INTO draws 
                        (draw_date, numbers, bonus, lottery_type)
                        VALUES (:date, :numbers, :bonus, 'Daily Grand')
                    """),
                    {
                        'date': draw_date,
                        'numbers': json.dumps(full_numbers),
                        'bonus': grand  # Store grand number as bonus
                    }
                )
                imported += 1
                
                if imported % 10 == 0:
                    print(f"  Imported {imported} draws...")
                    
            except Exception as e:
                print(f"  Error at row {idx}: {e}")
                continue
        
        conn.commit()
    
    print(f"\n✅ Import complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped (duplicates): {skipped}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 import_daily_grand_csv.py <csv_file>")
        print("Example: python3 import_daily_grand_csv.py daily_grand_real_data.csv")
        sys.exit(1)
    
    import_csv(sys.argv[1])
