"""
Base database utilities shared across all database modules.
Provides common connection management, configuration, and utilities.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

class DatabaseConfig:
    """Centralized database configuration and path management."""
    
    @staticmethod
    def get_db_directory():
        """Get the database data directory, creating it if needed."""
        current_dir = Path(__file__).parent
        db_dir = current_dir / "data"
        db_dir.mkdir(exist_ok=True)
        return db_dir
    
    @staticmethod
    def get_backup_directory():
        """Get the backup directory, creating it if needed."""
        backup_dir = DatabaseConfig.get_db_directory() / "backups"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir
    
    @staticmethod
    def get_migrations_directory():
        """Get the migrations directory."""
        current_dir = Path(__file__).parent
        return current_dir / "migrations"

class BaseDatabase:
    """
    Base class for all database operations.
    Provides common connection handling and utilities.
    """
    
    def __init__(self, db_name: str):
        """
        Initialize database with given filename.
        
        Args:
            db_name: Database filename (e.g., "pixil_metrics.db")
        """
        self.db_path = DatabaseConfig.get_db_directory() / db_name
        
    def get_connection(self):
        """
        Get database connection with standard settings.
        
        Returns:
            sqlite3.Connection with row_factory enabled for dict-like access
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def execute_migration(self, migration_sql: str):
        """
        Execute a database migration script.
        
        Args:
            migration_sql: SQL commands to execute
        """
        with self.get_connection() as conn:
            conn.executescript(migration_sql)
            conn.commit()
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of table to check
            
        Returns:
            True if table exists, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            return cursor.fetchone() is not None
    
    def get_db_size(self) -> int:
        """
        Get database file size in bytes.
        
        Returns:
            Size of database file in bytes, or 0 if file doesn't exist
        """
        try:
            return self.db_path.stat().st_size
        except FileNotFoundError:
            return 0