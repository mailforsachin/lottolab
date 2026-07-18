#!/usr/bin/env python3
"""
Check for and import the latest Lotto 6/49 data
"""

import kagglehub
import pandas as pd
import os
from datetime import datetime
from sqlalchemy import create_engine, text

# Database connection
DB_URL = "mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
engine = create_engine(DB_URL)

def check_latest_draws():
    print("📥 Checking Kaggle dataset for latest draws...")
    
    # Download dataset
    path = kagglehub.dataset_download("markkruger/lotto-649-historical-dataset-1982-2025")
    csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
    df = pd.read_csv(os.path.join(path, csv_files[0]))
    
    # Get latest date
    df['Date'] = pd.to_datetime(df['Date'])
    latest_date = df['Date'].max()
    print(f"📅 Latest date in dataset: {latest_date.date()}")
    
    # Check what's already in database
    with engine.connect() as conn:
        result = conn.execute(text("SELECT MAX(draw_date) FROM draws"))
        db_latest = result.scalar()
        print(f"📅 Latest date in database: {db_latest}")
    
    # Find new draws
    if db_latest:
        new_draws = df[df['Date'] > pd.to_datetime(db_latest)]
    else:
        new_draws = df
    
    if len(new_draws) > 0:
        print(f"🆕 Found {len(new_draws)} new draws to import!")
        
        # Show the new draws
        for idx, row in new_draws.iterrows():
            numbers = [int(row[f'Num{i}']) for i in range(1, 7)]
            print(f"  {row['Date'].date()}: {numbers} (Bonus: {row['Bonus']})")
        
        # Ask for confirmation
        response = input(f"\nImport {len(new_draws)} new draws? (y/n): ")
        if response.lower() == 'y':
            import_new_draws(new_draws)
    else:
        print("✅ No new draws to import")

def import_new_draws(new_draws):
    """Import new draws to database"""
    imported = 0
    with engine.connect() as conn:
        for idx, row in new_draws.iterrows():
            try:
                draw_date = row['Date'].date()
                numbers = [int(row[f'Num{i}']) for i in range(1, 7)]
                bonus = int(row['Bonus']) if pd.notna(row['Bonus']) else None
                
                # Check if exists
                check = conn.execute(
                    text("SELECT id FROM draws WHERE draw_date = :date"),
                    {'date': draw_date}
                ).first()
                
                if check:
                    continue
                
                # Insert
                conn.execute(
                    text("""
                        INSERT INTO draws 
                        (draw_date, numbers, bonus, lottery_type)
                        VALUES (:date, :numbers, :bonus, '6/49')
                    """),
                    {
                        'date': draw_date,
                        'numbers': str(numbers),
                        'bonus': bonus
                    }
                )
                imported += 1
                
                if imported % 10 == 0:
                    print(f"  Imported {imported} draws...")
                    
            except Exception as e:
                print(f"  Error importing {row['Date']}: {e}")
                continue
        
        conn.commit()
    
    print(f"✅ Imported {imported} new draws!")

if __name__ == "__main__":
    check_latest_draws()
