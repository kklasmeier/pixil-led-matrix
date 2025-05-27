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

    def get_jit_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get JIT line caching performance summary.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary with JIT performance statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_runs,
                    AVG(jit_hit_rate) as avg_jit_hit_rate,
                    AVG(jit_skip_efficiency) as avg_skip_efficiency,
                    SUM(jit_time_saved) as total_jit_time_saved,
                    SUM(jit_skip_time_saved) as total_skip_time_saved,
                    AVG(jit_cache_utilization) as avg_cache_utilization,
                    AVG(failed_lines_cached) as avg_failed_lines_cached,
                    SUM(jit_line_cache_skips) as total_skips,
                    SUM(jit_attempts) as total_attempts
                FROM script_metrics
                WHERE created_at >= ? AND execution_reason = 'complete'
            ''', (cutoff_date,))
            
            row = cursor.fetchone()
            result = dict(row) if row else {}
            
            # Calculate derived metrics
            if result.get('total_attempts', 0) > 0 and result.get('total_skips', 0) > 0:
                total_expressions = result['total_attempts'] + result['total_skips']
                result['overall_skip_efficiency'] = (result['total_skips'] / total_expressions) * 100
                result['total_time_saved'] = result.get('total_jit_time_saved', 0) + result.get('total_skip_time_saved', 0)
            
            return result

    def get_script_jit_comparison(self, script_name: str) -> Dict[str, Any]:
        """
        Compare JIT performance for a specific script over time.
        
        Args:
            script_name: Name of script to analyze
            
        Returns:
            Dictionary with comparison statistics
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as execution_count,
                    AVG(jit_hit_rate) as avg_hit_rate,
                    AVG(jit_skip_efficiency) as avg_skip_efficiency,
                    AVG(jit_cache_utilization) as avg_cache_util,
                    AVG(failed_lines_cached) as avg_failed_lines,
                    MIN(jit_hit_rate) as min_hit_rate,
                    MAX(jit_hit_rate) as max_hit_rate,
                    AVG(jit_time_saved + jit_skip_time_saved) as avg_total_time_saved,
                    AVG(jit_compilation_time) as avg_compilation_time
                FROM script_metrics
                WHERE script_name = ? AND execution_reason = 'complete'
            ''', (script_name,))
            
            return dict(cursor.fetchone()) if cursor.fetchone() else {}

    def get_optimization_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily optimization trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of daily optimization statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as runs,
                    AVG(jit_hit_rate) as avg_jit_hit_rate,
                    AVG(jit_skip_efficiency) as avg_skip_efficiency,
                    AVG(fast_path_hit_rate) as avg_fast_path_rate,
                    AVG(fast_math_hit_rate) as avg_fast_math_rate,
                    AVG(parse_value_hit_rate) as avg_parse_value_rate,
                    SUM(jit_time_saved + jit_skip_time_saved + 
                        fast_path_time_saved + fast_math_time_saved + 
                        parse_value_time_saved) as total_time_saved
                FROM script_metrics
                WHERE created_at >= ? AND execution_reason = 'complete'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''', (cutoff_date,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_most_optimized_scripts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get scripts with best optimization performance.
        
        Args:
            limit: Number of top scripts to return
            
        Returns:
            List of scripts ranked by optimization effectiveness
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    script_name,
                    COUNT(*) as execution_count,
                    AVG(jit_hit_rate + jit_skip_efficiency + 
                        fast_path_hit_rate + fast_math_hit_rate + 
                        parse_value_hit_rate) / 5 as avg_optimization_score,
                    AVG(jit_time_saved + jit_skip_time_saved + 
                        fast_path_time_saved + fast_math_time_saved + 
                        parse_value_time_saved) as avg_time_saved,
                    AVG(total_execution_time) as avg_execution_time
                FROM script_metrics
                WHERE execution_reason = 'complete'
                GROUP BY script_name
                HAVING execution_count >= 3
                ORDER BY avg_optimization_score DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]