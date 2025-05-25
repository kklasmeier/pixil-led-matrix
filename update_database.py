import sys
import os
# Add the parent directory to the path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import PixilMetricsDB

def update_database_schema():
    """One-time function to add parse value columns to database"""
    
    db = PixilMetricsDB()
    with db.get_connection() as conn:
        # Add the new columns
        columns_to_add = [
            "ALTER TABLE script_metrics ADD COLUMN parse_value_attempts INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN parse_value_ultra_fast_hits INTEGER DEFAULT 0", 
            "ALTER TABLE script_metrics ADD COLUMN parse_value_fast_hits INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN parse_value_hit_rate REAL DEFAULT 0.0",
            "ALTER TABLE script_metrics ADD COLUMN parse_value_time_saved REAL DEFAULT 0.0",
            "ALTER TABLE script_metrics ADD COLUMN direct_integer_hits INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN direct_color_hits INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN direct_string_hits INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN simple_array_hits INTEGER DEFAULT 0",
            "ALTER TABLE script_metrics ADD COLUMN simple_arithmetic_hits INTEGER DEFAULT 0"
        ]
        
        for sql in columns_to_add:
            try:
                conn.execute(sql)
                print(f"✓ Added column: {sql.split('ADD COLUMN ')[1].split(' ')[0]}")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print(f"⚠ Column already exists: {sql.split('ADD COLUMN ')[1].split(' ')[0]}")
                else:
                    print(f"✗ Error: {e}")
        
        conn.commit()
        print("Database schema update complete!")

if __name__ == '__main__':
    update_database_schema()