#!/usr/bin/env python3
import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import PixilMetricsDB

def check_database():
    """Debug the parse_value timing in database."""
    db = PixilMetricsDB()
    
    print("=== Database Debug Check ===")
    
    with db.get_connection() as conn:
        # 1. Check if column exists
        print("1. Checking table schema...")
        cursor = conn.execute("PRAGMA table_info(script_metrics)")
        columns = cursor.fetchall()
        
        parse_value_cols = [col for col in columns if 'parse_value' in col[1]]
        print(f"Parse value columns found: {len(parse_value_cols)}")
        for col in parse_value_cols:
            print(f"   {col[1]} ({col[2]})")
        
        print()
        
        # 2. Check recent data
        print("2. Checking recent Particle_Tumbler.pix entries...")
        cursor = conn.execute('''
            SELECT script_name, start_time, parse_value_attempts, parse_value_total_time,
                   parse_value_avg_time_per_call
            FROM script_metrics 
            WHERE script_name = 'Particle_Tumbler.pix' 
            ORDER BY start_time DESC 
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        print(f"Found {len(rows)} recent entries:")
        for row in rows:
            print(f"   {row['start_time']}: attempts={row['parse_value_attempts']}, "
                  f"total_time={row['parse_value_total_time']}, "
                  f"avg_time={row['parse_value_avg_time_per_call']}")
        
        print()
        
        # 3. Check if any entries have non-zero timing
        print("3. Checking for any non-zero parse_value_total_time...")
        cursor = conn.execute('''
            SELECT COUNT(*) as total_rows,
                   SUM(CASE WHEN parse_value_total_time > 0 THEN 1 ELSE 0 END) as non_zero_rows
            FROM script_metrics
        ''')
        
        stats = cursor.fetchone()
        print(f"Total rows: {stats['total_rows']}")
        print(f"Rows with parse_value_total_time > 0: {stats['non_zero_rows']}")

if __name__ == '__main__':
    try:
        check_database()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
