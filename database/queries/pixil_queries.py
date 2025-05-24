"""
Performance query helpers for Pixil metrics.
Provides advanced analytics and reporting queries for script performance data.
"""

from typing import List, Dict, Any, Optional
import sqlite3
from datetime import datetime, timedelta
from ..base import BaseDatabase

class PixilQueries(BaseDatabase):
    """
    Advanced query helper for Pixil performance metrics.
    
    Provides methods for performance analysis, trends, and comparisons
    that are commonly needed for monitoring and optimization.
    """
    
    def __init__(self):
        """Initialize with Pixil metrics database."""
        super().__init__("pixil_metrics.db")
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get performance summary for last N days.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary with summary statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_runs,
                    COUNT(DISTINCT script_name) as unique_scripts,
                    AVG(commands_per_second) as avg_commands_per_sec,
                    AVG(lines_per_second) as avg_lines_per_sec,
                    AVG(total_execution_time) as avg_execution_time,
                    AVG(fast_path_hit_rate) as avg_fast_path_hit_rate,
                    AVG(fast_math_hit_rate) as avg_fast_math_hit_rate,
                    AVG(cache_hit_rate) as avg_cache_hit_rate,
                    SUM(fast_path_time_saved + fast_math_time_saved + cache_time_saved) as total_time_saved,
                    COUNT(CASE WHEN execution_reason = 'interrupted' THEN 1 END) as interrupted_count,
                    COUNT(CASE WHEN execution_reason = 'complete' THEN 1 END) as completed_count
                FROM script_metrics
                WHERE created_at >= ?
            ''', (cutoff_date,))
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def get_optimization_effectiveness(self) -> Dict[str, Any]:
        """
        Get overall optimization effectiveness statistics.
        
        Returns:
            Dictionary with optimization performance data
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    AVG(fast_path_hit_rate) as avg_fast_path_rate,
                    AVG(fast_math_hit_rate) as avg_fast_math_rate,
                    AVG(cache_hit_rate) as avg_cache_rate,
                    SUM(fast_path_time_saved) as total_fast_path_saved,
                    SUM(fast_math_time_saved) as total_fast_math_saved,
                    SUM(cache_time_saved) as total_cache_saved,
                    AVG(fast_path_attempts) as avg_fast_path_attempts,
                    AVG(fast_math_attempts) as avg_fast_math_attempts,
                    AVG(cache_attempts) as avg_cache_attempts
                FROM script_metrics
                WHERE execution_reason = 'complete'
            ''')
            
            row = cursor.fetchone()
            return dict(row) if row else {}