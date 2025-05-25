python -c "
import sqlite3
from database import PixilMetricsDB
db = PixilMetricsDB()
with db.get_connection() as conn:
    cursor = conn.execute('PRAGMA table_info(script_metrics)')
    columns = [col[1] for col in cursor.fetchall()]
    print('Database columns:')
    for i, col in enumerate(columns, 1):
        print(f'{i:2d}. {col}')
    print(f'Total: {len(columns)} columns')
"
