"""
Pixil performance metrics database.
Stores execution statistics, optimization metrics, and performance data.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import BaseDatabase, DatabaseConfig
from database.base import BaseDatabase, DatabaseConfig

class PixilMetricsDB(BaseDatabase):
    """
    Database for storing and retrieving Pixil script performance metrics.
    
    Handles script execution timing, optimization statistics, and performance data.
    """
    
    def __init__(self):
        """Initialize Pixil metrics database."""
        super().__init__("pixil_metrics.db")
        self.init_database()
    
    def init_database(self):
        """Create tables and indexes if they don't exist."""
        # Load and execute the initial migration
        migrations_dir = DatabaseConfig.get_migrations_directory()
        migration_file = migrations_dir / "001_pixil_initial.sql"
        
        if migration_file.exists():
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            self.execute_migration(migration_sql)
        else:
            # Fallback inline schema if migration file missing
            self._create_inline_schema()
    
    def _create_inline_schema(self):
        """Fallback method to create schema inline if migration file missing."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS script_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            script_name TEXT NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            execution_reason TEXT DEFAULT 'complete',
            commands_executed INTEGER DEFAULT 0,
            script_lines_processed INTEGER DEFAULT 0,
            total_execution_time REAL DEFAULT 0.0,
            active_execution_time REAL DEFAULT 0.0,
            commands_per_second REAL DEFAULT 0.0,
            lines_per_second REAL DEFAULT 0.0,
            fast_path_attempts INTEGER DEFAULT 0,
            fast_path_hits INTEGER DEFAULT 0,
            fast_path_hit_rate REAL DEFAULT 0.0,
            fast_path_time_saved REAL DEFAULT 0.0,
            fast_math_attempts INTEGER DEFAULT 0,
            fast_math_hits INTEGER DEFAULT 0,
            fast_math_hit_rate REAL DEFAULT 0.0,
            fast_math_time_saved REAL DEFAULT 0.0,
            cache_attempts INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            cache_hit_rate REAL DEFAULT 0.0,
            cache_size INTEGER DEFAULT 0,
            cache_time_saved REAL DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_script_name ON script_metrics(script_name);
        CREATE INDEX IF NOT EXISTS idx_start_time ON script_metrics(start_time);
        CREATE INDEX IF NOT EXISTS idx_created_at ON script_metrics(created_at);
        """
        self.execute_migration(schema_sql)
    
    # Update the save_metrics method in database/pixil_metrics.py

    def save_metrics(self, script_name: str, start_time: datetime.datetime, 
                    end_time: datetime.datetime, metrics_data: Dict[str, Any], 
                    reason: str = "complete"):
        """Save performance metrics to database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO script_metrics (
                    script_name, start_time, end_time, execution_reason,
                    commands_executed, script_lines_processed,
                    total_execution_time, active_execution_time,
                    commands_per_second, lines_per_second,
                    fast_path_attempts, fast_path_hits, fast_path_hit_rate, fast_path_time_saved,
                    fast_math_attempts, fast_math_hits, fast_math_hit_rate, fast_math_time_saved,
                    cache_attempts, cache_hits, cache_hit_rate, cache_size, cache_time_saved,
                    parse_value_attempts, parse_value_ultra_fast_hits, parse_value_fast_hits, 
                    parse_value_hit_rate, parse_value_time_saved,
                    parse_value_total_time, parse_value_avg_time_per_call, 
                    direct_integer_hits, direct_color_hits, direct_string_hits,
                    simple_array_hits, simple_arithmetic_hits,
                    var_cache_attempts, var_cache_hits, var_cache_hit_rate, var_cache_time_saved,
                    ultra_fast_attempts, ultra_fast_hits, ultra_fast_hit_rate, ultra_fast_time_saved,
                    fast_path_parse_attempts, fast_path_parse_hits, fast_path_parse_hit_rate, fast_path_parse_time_saved,
                    jit_attempts, jit_hits, jit_failures, jit_hit_rate, jit_time_saved,
                    jit_line_cache_skips, failed_lines_cached, jit_skip_efficiency, jit_skip_time_saved,
                    jit_cache_size, jit_cache_utilization, jit_compilation_time,
                    condition_template_attempts, condition_template_hits, condition_template_hit_rate,
                    condition_template_time_saved, condition_template_cache_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                script_name, start_time, end_time, reason,                                    # 4 values
                metrics_data.get('commands_executed', 0),                                      # 1
                metrics_data.get('script_lines_processed', 0),                               # 1  
                metrics_data.get('total_execution_time', 0.0),                               # 1
                metrics_data.get('active_execution_time', 0.0),                              # 1
                metrics_data.get('commands_per_second', 0.0),                                # 1
                metrics_data.get('lines_per_second', 0.0),                                   # 1 = 10 total
                metrics_data.get('fast_path_attempts', 0),                                    # 1
                metrics_data.get('fast_path_hits', 0),                                       # 1
                metrics_data.get('fast_path_hit_rate', 0.0),                                 # 1
                metrics_data.get('fast_path_time_saved', 0.0),                               # 1
                metrics_data.get('fast_math_attempts', 0),                                    # 1
                metrics_data.get('fast_math_hits', 0),                                       # 1
                metrics_data.get('fast_math_hit_rate', 0.0),                                 # 1
                metrics_data.get('fast_math_time_saved', 0.0),                               # 1
                metrics_data.get('cache_attempts', 0),                                       # 1
                metrics_data.get('cache_hits', 0),                                           # 1
                metrics_data.get('cache_hit_rate', 0.0),                                     # 1
                metrics_data.get('cache_size', 0),                                           # 1
                metrics_data.get('cache_time_saved', 0.0),                                   # 1 = 23 total

                metrics_data.get('parse_value_attempts', 0),                                 # 1
                metrics_data.get('parse_value_ultra_fast_hits', 0),                          # 1
                metrics_data.get('parse_value_fast_hits', 0),                                # 1
                metrics_data.get('parse_value_hit_rate', 0.0),                               # 1
                metrics_data.get('parse_value_time_saved', 0.0),                             # 1
                metrics_data.get('parse_value_total_time', 0.0),                             # 1 - NEW
                metrics_data.get('parse_value_avg_time_per_call', 0.0),                      # 1 - NEW
                metrics_data.get('direct_integer_hits', 0),                                  # 1

                metrics_data.get('direct_color_hits', 0),                                    # 1
                metrics_data.get('direct_string_hits', 0),                                   # 1
                metrics_data.get('simple_array_hits', 0),                                    # 1
                metrics_data.get('simple_arithmetic_hits', 0),                               # 1 = 33 total
                # NEW: Variable cache metrics
                metrics_data.get('var_cache_attempts', 0),                                   # 1
                metrics_data.get('var_cache_hits', 0),                                       # 1
                metrics_data.get('var_cache_hit_rate', 0.0),                                 # 1
                metrics_data.get('var_cache_time_saved', 0.0),                               # 1
                # NEW: Ultra Fast Path metrics
                metrics_data.get('ultra_fast_attempts', 0),                                  # 1
                metrics_data.get('ultra_fast_hits', 0),                                      # 1
                metrics_data.get('ultra_fast_hit_rate', 0.0),                                # 1
                metrics_data.get('ultra_fast_time_saved', 0.0),                              # 1
                # NEW: Fast Path Parse metrics
                metrics_data.get('fast_path_parse_attempts', 0),                             # 1
                metrics_data.get('fast_path_parse_hits', 0),                                 # 1
                metrics_data.get('fast_path_parse_hit_rate', 0.0),                           # 1
                metrics_data.get('fast_path_parse_time_saved', 0.0),                         # 1 = 45 total
                # JIT metrics (existing)
                metrics_data.get('jit_attempts', 0),                                         # 1
                metrics_data.get('jit_hits', 0),                                             # 1
                metrics_data.get('jit_failures', 0),                                         # 1
                metrics_data.get('jit_hit_rate', 0.0),                                       # 1
                metrics_data.get('jit_time_saved', 0.0),                                     # 1
                metrics_data.get('jit_line_cache_skips', 0),                                 # 1
                metrics_data.get('failed_lines_cached', 0),                                  # 1
                metrics_data.get('jit_skip_efficiency', 0.0),                                # 1
                metrics_data.get('jit_skip_time_saved', 0.0),                                # 1
                metrics_data.get('jit_cache_size', 0),                                       # 1
                metrics_data.get('jit_cache_utilization', 0.0),                              # 1
                metrics_data.get('jit_compilation_time', 0.0), 
                # Conditional Templates
                metrics_data.get('condition_template_attempts', 0),                          # 1
                metrics_data.get('condition_template_hits', 0),                              # 1
                metrics_data.get('condition_template_hit_rate', 0.0),                        # 1
                metrics_data.get('condition_template_time_saved', 0.0),                      # 1
                metrics_data.get('condition_template_cache_size', 0)                         # 1 = 62 total
            ))
            conn.commit()
        
    def get_recent_metrics(self, limit: int = 10) -> List[sqlite3.Row]:
        """
        Get the most recent metrics records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of database rows with metrics data
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM script_metrics 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def get_metrics_by_script(self, script_name: str) -> List[sqlite3.Row]:
        """
        Get all metrics for a specific script.
        
        Args:
            script_name: Name of script to query
            
        Returns:
            List of database rows for the specified script
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM script_metrics 
                WHERE script_name = ? 
                ORDER BY created_at DESC
            ''', (script_name,))
            return cursor.fetchall()
    
    def get_script_count(self) -> int:
        """
        Get total number of script executions recorded.
        
        Returns:
            Total count of script execution records
        """
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM script_metrics')
            return cursor.fetchone()[0]
    
    def get_unique_scripts(self) -> List[str]:
        """
        Get list of all unique script names in database.
        
        Returns:
            List of unique script names
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT DISTINCT script_name 
                FROM script_metrics 
                ORDER BY script_name
            ''')
            return [row[0] for row in cursor.fetchall()]
    
    def delete_old_records(self, days_old: int) -> int:
        """
        Delete records older than specified number of days.
        
        Args:
            days_old: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        
        with self.get_connection() as conn:
            cursor = conn.execute('''
                DELETE FROM script_metrics 
                WHERE created_at < ?
            ''', (cutoff_date,))
            conn.commit()
            return cursor.rowcount