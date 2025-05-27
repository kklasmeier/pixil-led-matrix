#!/usr/bin/env python3
"""
Manual database migration script for Pixil metrics.
Usage: python migrate.py [migration_number]
"""
import sys
import argparse
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path so we can import from database package
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.base import DatabaseConfig
from database.pixil_metrics import PixilMetricsDB

def apply_migration(migration_number):
    """Apply a specific migration by number."""
    migrations_dir = DatabaseConfig.get_migrations_directory()
    migration_file = migrations_dir / f"{migration_number:03d}_*.sql"
    
    # Find the migration file
    migration_files = list(migrations_dir.glob(f"{migration_number:03d}_*.sql"))
    
    if not migration_files:
        print(f"Migration {migration_number:03d} not found")
        return False
    
    migration_file = migration_files[0]
    print(f"Applying migration: {migration_file.name}")
    
    try:
        db = PixilMetricsDB()
        
        # Check if migration was already applied
        if migration_already_applied(db, migration_number):
            print(f"Migration {migration_number:03d} already applied")
            return True
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        db.execute_migration(migration_sql)
        
        # Record that migration was applied
        record_migration(db, migration_number, migration_file.name)
        
        print(f"✓ Migration {migration_number:03d} applied successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False

def migration_already_applied(db, migration_number):
    """Check if migration was already applied."""
    try:
        with db.get_connection() as conn:
            # Try to query for JIT columns to see if migration 002 was applied
            if migration_number == 2:
                cursor = conn.execute("PRAGMA table_info(script_metrics)")
                columns = [row[1] for row in cursor.fetchall()]
                return 'jit_attempts' in columns
            return False
    except Exception:
        return False

def record_migration(db, migration_number, filename):
    """Record that a migration was applied (optional tracking)."""
    # For now, just print - you could create a migrations table if desired
    print(f"Recorded migration {migration_number:03d}: {filename}")

def list_pending_migrations():
    """List migrations that haven't been applied."""
    migrations_dir = DatabaseConfig.get_migrations_directory()
    
    print("Available migrations:")
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        print(f"  {migration_file.name}")

def main():
    parser = argparse.ArgumentParser(description='Apply database migrations')
    parser.add_argument('migration', type=int, nargs='?',
                       help='Migration number to apply (e.g., 2 for 002_add_jit_line_caching.sql)')
    parser.add_argument('--list', action='store_true',
                       help='List available migrations')
    
    args = parser.parse_args()
    
    if args.list:
        list_pending_migrations()
        return
    
    if not args.migration:
        print("Usage: python migrate.py <migration_number>")
        print("       python migrate.py --list")
        return
    
    success = apply_migration(args.migration)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()