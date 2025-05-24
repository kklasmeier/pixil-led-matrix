#!/usr/bin/env python3
"""Quick database inspector to see raw data in tabular form."""

import sqlite3
import sys
from pathlib import Path

# Database path
db_path = Path("database/data/pixil_metrics.db")

if not db_path.exists():
    print("Database file not found!")
    sys.exit(1)

# Connect and query
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Enable column names

print("=== Raw Database Contents ===\n")

# Get table schema first
cursor = conn.execute("PRAGMA table_info(script_metrics)")
schema = cursor.fetchall()

print("Table Schema:")
for col in schema:
    print(f"  {col[1]} - {col[2]} (nullable: {not col[3]})")

print("\n" + "="*80)

# Get all data
cursor = conn.execute("SELECT * FROM script_metrics ORDER BY id")
rows = cursor.fetchall()

if not rows:
    print("No data found in database.")
else:
    # Print column headers
    columns = [desc[0] for desc in cursor.description]
    print("Data Contents:")
    
    # Print just the key columns to start
    key_cols = ['id', 'script_name', 'start_time', 'commands_executed', 'commands_per_second', 'fast_path_hit_rate']
    
    # Header
    header = " | ".join(f"{col:>15}" for col in key_cols)
    print(header)
    print("-" * len(header))
    
    # Data rows
    for row in rows:
        values = []
        for col in key_cols:
            val = row[col]
            # Show the actual Python type
            type_info = f"{val} ({type(val).__name__})"
            values.append(f"{type_info:>15}")
        print(" | ".join(values))

    print(f"\nTotal rows: {len(rows)}")
    
    # Show data types for all numeric fields
    print("\n=== Data Types Check ===")
    if rows:
        row = rows[0]  # Check first row
        numeric_fields = [
            'commands_executed', 'script_lines_processed', 'total_execution_time',
            'commands_per_second', 'fast_path_hit_rate', 'fast_math_hit_rate'
        ]
        
        for field in numeric_fields:
            val = row[field]
            print(f"{field}: {val} (type: {type(val).__name__})")

conn.close()