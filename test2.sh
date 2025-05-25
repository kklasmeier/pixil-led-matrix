python -c "
from database import PixilMetricsDB
db = PixilMetricsDB()
with db.get_connection() as conn:
    # Check latest entry
    cursor = conn.execute('SELECT script_name, start_time, execution_reason FROM script_metrics ORDER BY start_time DESC LIMIT 3')
    print('Latest entries:')
    for row in cursor.fetchall():
        print(f'  {row[0]} - {row[1]} - {row[2]}')
    
    # Check column count
    cursor = conn.execute('PRAGMA table_info(script_metrics)')
    columns = cursor.fetchall()
    print(f'\nTotal columns in table: {len(columns)}')
    print('Columns:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')
"