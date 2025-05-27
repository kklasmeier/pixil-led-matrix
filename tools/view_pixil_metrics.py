#!/usr/bin/env python3
"""
View Pixil performance metrics from database.
Usage: python view_pixil_metrics.py [options]
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path so we can import from database package
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PixilMetricsDB
from database.queries.pixil_queries import PixilQueries

def safe_get_column(row, column_name, default=0):
    """Safely get a column value from sqlite3.Row, handling missing columns."""
    try:
        return row[column_name] if row[column_name] is not None else default
    except (KeyError, IndexError):
        return default

def main():
    parser = argparse.ArgumentParser(description='View Pixil performance metrics')
    parser.add_argument('--recent', type=int, default=10, 
                       help='Show N most recent script runs (default: 10)')
    parser.add_argument('--script', type=str, 
                       help='Show history for specific script')
    parser.add_argument('--summary', action='store_true',
                       help='Show performance summary for last 7 days')
    parser.add_argument('--jit-summary', action='store_true',
                       help='Show JIT line caching performance summary')
    parser.add_argument('--list', action='store_true',
                       help='List all scripts in database')
    parser.add_argument('--trends', type=str,
                       help='Show performance trends for specific script')
    parser.add_argument('--trends-all', action='store_true',
                       help='Show system-wide performance trends')
    parser.add_argument('--count', type=int, default=20,
                       help='Number of executions to include in trends (default: 20)')
    parser.add_argument('--verbose', '-v', action='store_true',
                    help='Show verbose output with additional metrics')
    args = parser.parse_args()
    
    try:
        if args.jit_summary:
            show_jit_summary()
        elif args.trends:
            show_script_trends(args.trends, args.count, args.verbose)
        elif args.trends_all:
            show_system_trends(args.count, args.verbose)
        elif args.script:
            if args.summary:
                print("Note: Combining --script with --summary is not supported. Showing script history instead.")
            show_script_history(args.script)
        elif args.summary:
            show_summary()
        elif args.list:
            list_scripts()
        else:
            show_recent(args.recent)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def show_recent(limit):
    """Show recent script executions with JIT metrics."""
    db = PixilMetricsDB()
    recent = db.get_recent_metrics(limit)
    
    if not recent:
        print("No metrics data found in database.")
        return
    
    print(f"\n=== {len(recent)} Most Recent Script Executions ===")
    for row in recent:
        duration = row['total_execution_time']
        print(f"Script: {row['script_name']}")
        print(f"  Executed: {row['start_time']} ({row['execution_reason']})")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Performance: {row['commands_per_second']:.1f} cmds/sec, {row['lines_per_second']:.1f} lines/sec")
        
        # Include all optimization metrics with safe column access
        parse_val_rate = safe_get_column(row, 'parse_value_hit_rate', 0)
        parse_val_time_saved = safe_get_column(row, 'parse_value_time_saved', 0)
        
        # JIT line caching metrics
        jit_hit_rate = safe_get_column(row, 'jit_hit_rate', 0)
        jit_skip_efficiency = safe_get_column(row, 'jit_skip_efficiency', 0)
        jit_time_saved = safe_get_column(row, 'jit_time_saved', 0)
        jit_skip_time_saved = safe_get_column(row, 'jit_skip_time_saved', 0)

        print(f"  Optimizations: Fast Path {row['fast_path_hit_rate']:.1f}%, Fast Math {row['fast_math_hit_rate']:.1f}%, Cache {row['cache_hit_rate']:.1f}%, Parse Value {parse_val_rate:.1f}%")
        
        # Show JIT performance if data exists
        if jit_hit_rate > 0 or jit_skip_efficiency > 0:
            print(f"  JIT Performance: Hit Rate {jit_hit_rate:.1f}%, Skip Efficiency {jit_skip_efficiency:.1f}%")

        total_saved = (row['fast_path_time_saved'] + row['fast_math_time_saved'] + 
                    row['cache_time_saved'] + parse_val_time_saved + jit_time_saved + jit_skip_time_saved)

        print(f"  Time Saved: {total_saved:.3f}s")
        print()

def show_jit_summary():
    """Show JIT line caching performance summary."""
    db = PixilMetricsDB()
    
    with db.get_connection() as conn:
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total_runs,
                AVG(jit_hit_rate) as avg_jit_hit_rate,
                AVG(jit_skip_efficiency) as avg_skip_efficiency,
                AVG(jit_cache_utilization) as avg_cache_utilization,
                AVG(failed_lines_cached) as avg_failed_lines_cached,
                SUM(jit_time_saved) as total_jit_time_saved,
                SUM(jit_skip_time_saved) as total_skip_time_saved
            FROM script_metrics
            WHERE execution_reason IN ('complete', 'interrupted') 
            AND created_at >= datetime('now', '-7 days')
            AND jit_attempts > 0
        ''')
        
        row = cursor.fetchone()
        if row and row['total_runs'] > 0:
            print("\n=== JIT Line Caching Performance Summary (Last 7 Days) ===")
            print(f"Total script runs: {row['total_runs']}")
            print(f"Average JIT hit rate: {safe_get_column(row, 'avg_jit_hit_rate', 0):.1f}%")
            print(f"Average skip efficiency: {safe_get_column(row, 'avg_skip_efficiency', 0):.1f}%")
            print(f"Average cache utilization: {safe_get_column(row, 'avg_cache_utilization', 0):.1f}%")
            print(f"Average failed lines cached: {safe_get_column(row, 'avg_failed_lines_cached', 0):.0f}")
            print(f"Total JIT time saved: {safe_get_column(row, 'total_jit_time_saved', 0):.3f}s")
            print(f"Total skip time saved: {safe_get_column(row, 'total_skip_time_saved', 0):.3f}s")
            
            total_time_saved = safe_get_column(row, 'total_jit_time_saved', 0) + safe_get_column(row, 'total_skip_time_saved', 0)
            print(f"Combined time savings: {total_time_saved:.3f}s")
        else:
            print("No JIT metrics data found.")

def calculate_trends(history, script_name):
    """Calculate and display trend indicators including JIT metrics."""
    # Compare first vs last few executions
    recent = history[:3]  # Last 3 executions
    older = history[-3:] if len(history) >= 6 else history[3:6]  # 3 executions from earlier
    
    if not older:
        print("Not enough data for trend analysis (need at least 6 executions)")
        return
    
    # Calculate averages
    recent_avg_cmds = sum(r['commands_per_second'] for r in recent) / len(recent)
    older_avg_cmds = sum(r['commands_per_second'] for r in older) / len(older)
    
    recent_avg_time = sum(r['active_execution_time'] for r in recent) / len(recent)
    older_avg_time = sum(r['active_execution_time'] for r in older) / len(older)
    
    recent_avg_fp = sum(r['fast_path_hit_rate'] for r in recent) / len(recent)
    older_avg_fp = sum(r['fast_path_hit_rate'] for r in older) / len(older)
    
    # JIT trends
    recent_avg_jit = sum(safe_get_column(r, 'jit_hit_rate', 0) for r in recent) / len(recent)
    older_avg_jit = sum(safe_get_column(r, 'jit_hit_rate', 0) for r in older) / len(older)
    
    recent_avg_skip = sum(safe_get_column(r, 'jit_skip_efficiency', 0) for r in recent) / len(recent)
    older_avg_skip = sum(safe_get_column(r, 'jit_skip_efficiency', 0) for r in older) / len(older)
    
    # Trend indicators
    cmd_trend = "↗" if recent_avg_cmds > older_avg_cmds * 1.02 else "↘" if recent_avg_cmds < older_avg_cmds * 0.98 else "→"
    time_trend = "↗" if recent_avg_time < older_avg_time * 0.98 else "↘" if recent_avg_time > older_avg_time * 1.02 else "→"
    fp_trend = "↗" if recent_avg_fp > older_avg_fp * 1.01 else "↘" if recent_avg_fp < older_avg_fp * 0.99 else "→"
    jit_trend = "↗" if recent_avg_jit > older_avg_jit * 1.01 else "↘" if recent_avg_jit < older_avg_jit * 0.99 else "→"
    
    print(f"Trends: Commands/sec {cmd_trend}  Execution time {time_trend}  Fast path {fp_trend}  JIT hit rate {jit_trend}")
    print(f"Recent avg: {recent_avg_cmds:.0f} cmds/s, {recent_avg_time:.1f}s, {recent_avg_fp:.0f}% fast path")
    
    if recent_avg_jit > 0 or recent_avg_skip > 0:
        print(f"JIT recent avg: {recent_avg_jit:.0f}% hit rate, {recent_avg_skip:.0f}% skip efficiency")

def show_script_history(script_name):
    """Show performance history for specific script with JIT metrics."""
    db = PixilMetricsDB()
    history = db.get_metrics_by_script(script_name)
    
    if not history:
        print(f"No data found for script: {script_name}")
        return
    
    print(f"\n=== Performance History for {script_name} ===")
    print(f"Total executions: {len(history)}")
    
    # Calculate averages including JIT metrics
    completed = [row for row in history if row['execution_reason'] in ('complete', 'interrupted')]
    if completed:
        avg_duration = sum(row['total_execution_time'] for row in completed) / len(completed)
        avg_commands_per_sec = sum(row['commands_per_second'] for row in completed) / len(completed)
        avg_fast_path = sum(row['fast_path_hit_rate'] for row in completed) / len(completed)
        
        # JIT averages
        avg_jit_hit = sum(safe_get_column(row, 'jit_hit_rate', 0) for row in completed) / len(completed)
        avg_jit_skip = sum(safe_get_column(row, 'jit_skip_efficiency', 0) for row in completed) / len(completed)
        
        print(f"Completed executions: {len(completed)}")
        print(f"Average duration: {avg_duration:.3f}s")
        print(f"Average performance: {avg_commands_per_sec:.1f} commands/sec")
        print(f"Average fast path hit rate: {avg_fast_path:.1f}%")
        
        if avg_jit_hit > 0 or avg_jit_skip > 0:
            print(f"Average JIT hit rate: {avg_jit_hit:.1f}%")
            print(f"Average JIT skip efficiency: {avg_jit_skip:.1f}%")
    
    print("\nRecent executions:")
    for row in history[:5]:  # Show last 5
        status = row['execution_reason']
        jit_info = ""
        jit_rate = safe_get_column(row, 'jit_hit_rate', 0)
        if jit_rate > 0:
            jit_info = f", JIT {jit_rate:.0f}%"
            
        print(f"  {row['start_time']}: {row['total_execution_time']:.3f}s, {row['commands_per_second']:.1f} cmds/sec{jit_info} ({status})")

def show_summary():
    """Show overall performance summary including JIT metrics."""
    queries = PixilQueries()
    summary = queries.get_performance_summary()
    optimization = queries.get_optimization_effectiveness()
    
    if not summary or summary['total_runs'] == 0:
        print("No metrics data found for summary.")
        return
    
    print("\n=== Pixil Performance Summary (Last 7 Days) ===")
    print(f"Total script runs: {summary['total_runs']}")
    print(f"Unique scripts: {summary['unique_scripts']}")
    print(f"Completed runs: {summary['completed_count']}")
    print(f"Interrupted runs: {summary['interrupted_count']}")
    print(f"Average performance: {summary['avg_commands_per_sec']:.1f} commands/sec")
    print(f"Average line processing: {summary['avg_lines_per_sec']:.1f} lines/sec")
    print(f"Average execution time: {summary['avg_execution_time']:.3f} seconds")
    print(f"Total time saved by optimizations: {summary['total_time_saved']:.3f} seconds")
    
    print("\n=== Optimization Effectiveness ===")
    print(f"Fast Path hit rate: {optimization['avg_fast_path_rate']:.1f}%")
    print(f"Fast Math hit rate: {optimization['avg_fast_math_rate']:.1f}%")
    print(f"Expression Cache hit rate: {optimization['avg_cache_rate']:.1f}%")
    
    total_optimization_savings = (optimization['total_fast_path_saved'] + 
                                 optimization['total_fast_math_saved'] + 
                                 optimization['total_cache_saved'])
    print(f"Total optimization time savings: {total_optimization_savings:.3f} seconds")
    
    # JIT summary if available
    db = PixilMetricsDB()
    with db.get_connection() as conn:
        try:
            cursor = conn.execute('''
                SELECT 
                    AVG(jit_hit_rate) as avg_jit_hit_rate,
                    AVG(jit_skip_efficiency) as avg_skip_efficiency,
                    SUM(jit_time_saved + jit_skip_time_saved) as total_jit_time_saved
                FROM script_metrics
                WHERE execution_reason IN ('complete', 'interrupted')
                AND created_at >= datetime('now', '-7 days')
                AND jit_attempts > 0
            ''')
            
            jit_row = cursor.fetchone()
            if jit_row and safe_get_column(jit_row, 'avg_jit_hit_rate', 0) > 0:
                print(f"\n=== JIT Line Caching Effectiveness ===")
                print(f"JIT hit rate: {safe_get_column(jit_row, 'avg_jit_hit_rate', 0):.1f}%")
                print(f"JIT skip efficiency: {safe_get_column(jit_row, 'avg_skip_efficiency', 0):.1f}%")
                print(f"Total JIT time savings: {safe_get_column(jit_row, 'total_jit_time_saved', 0):.3f} seconds")
        except Exception:
            pass  # JIT columns might not exist in older databases

def show_script_trends(script_name, count, verbose=False):
    """Show performance trends for a specific script with JIT metrics."""
    db = PixilMetricsDB()
    history = db.get_metrics_by_script(script_name)
    
    if not history:
        print(f"No data found for script: {script_name}")
        return
    
    # Take only the requested number of most recent executions
    recent_history = history[:count]
    
    print(f"\n=== Performance Trends: {script_name} (Last {len(recent_history)} executions) ===")
    
    if verbose:
        print("Date/Time           Script              TotalTime ActTime  Cmds/s   Lines/s    FP%     FM%   C%   PV%   JIT%  Skip%  JIT-Time JIT-Skip Failed")
        print("-" * 135)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            total_time = f"{row['total_execution_time']:.1f}s"
            active_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            lines_per_sec = f"{row['lines_per_second']:.0f}"
            
            # Optimization rates
            fp_rate = f"{row['fast_path_hit_rate']:.0f}%"
            fm_rate = f"{row['fast_math_hit_rate']:.0f}%"
            cache_rate = f"{row['cache_hit_rate']:.0f}%"
            pv_rate = f"{safe_get_column(row, 'parse_value_hit_rate', 0):.0f}%"
            
            # JIT metrics
            jit_rate = f"{safe_get_column(row, 'jit_hit_rate', 0):.0f}%"
            skip_rate = f"{safe_get_column(row, 'jit_skip_efficiency', 0):.0f}%"
            jit_time = f"{safe_get_column(row, 'jit_time_saved', 0):.2f}s"
            skip_time = f"{safe_get_column(row, 'jit_skip_time_saved', 0):.2f}s"
            failed_lines = f"{safe_get_column(row, 'failed_lines_cached', 0)}"

            print(f"{date_str:19} {script:18} {total_time:>9} {active_time:>8} {cmds_per_sec:>8} {lines_per_sec:>8} {fp_rate:>7} {fm_rate:>7} {cache_rate:>4} {pv_rate:>5} {jit_rate:>5} {skip_rate:>6} {jit_time:>8} {skip_time:>9} {failed_lines:>6}")

    else:
        # Compact format with JIT columns
        print("Date/Time           ExecTime  Cmds/s  Lines/s  FastPath%  FastMath%  Cache%  ParseVal%  JIT%  Skip%")
        print("-" * 103)
        
        for row in reversed(recent_history):
            date_str = row['start_time'][:16].replace('T', ' ')
            exec_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            lines_per_sec = f"{row['lines_per_second']:.0f}"
            fast_path = f"{row['fast_path_hit_rate']:.0f}%"
            fast_math = f"{row['fast_math_hit_rate']:.0f}%"
            cache = f"{row['cache_hit_rate']:.0f}%"
            parse_val = f"{safe_get_column(row, 'parse_value_hit_rate', 0):.0f}%"
            jit_rate = f"{safe_get_column(row, 'jit_hit_rate', 0):.0f}%"
            skip_rate = f"{safe_get_column(row, 'jit_skip_efficiency', 0):.0f}%"

            print(f"{date_str:19} {exec_time:>8} {cmds_per_sec:>7} {lines_per_sec:>8} {fast_path:>9} {fast_math:>9} {cache:>6} {parse_val:>9} {jit_rate:>5} {skip_rate:>6}")
    
    # Calculate trends
    if len(recent_history) >= 2:
        print("\n" + "=" * (135 if verbose else 103))
        calculate_trends(recent_history, script_name)

def show_system_trends(count, verbose=False):
    """Show system-wide performance trends with JIT metrics."""
    db = PixilMetricsDB()
    
    with db.get_connection() as conn:
        if verbose:
            cursor = conn.execute('''
                SELECT script_name, start_time, total_execution_time, active_execution_time, 
                       commands_per_second, lines_per_second,
                       fast_path_hit_rate, fast_math_hit_rate, cache_hit_rate,
                       parse_value_hit_rate, jit_hit_rate, jit_skip_efficiency,
                       jit_time_saved, jit_skip_time_saved, failed_lines_cached
                FROM script_metrics 
                WHERE execution_reason IN ('complete', 'interrupted')
                ORDER BY start_time DESC
                LIMIT ?
            ''', (count,))
        else:
            cursor = conn.execute('''
                SELECT script_name, start_time, active_execution_time, commands_per_second, 
                       lines_per_second, fast_path_hit_rate, fast_math_hit_rate, cache_hit_rate,
                       parse_value_hit_rate, jit_hit_rate, jit_skip_efficiency
                FROM script_metrics 
                WHERE execution_reason IN ('complete', 'interrupted')
                ORDER BY start_time DESC
                LIMIT ?
            ''', (count,))
        
        history = cursor.fetchall()
    
    if not history:
        print("No completed executions found.")
        return
    
    print(f"\n=== System-Wide Performance Trends (Last {len(history)} executions) ===")
    
    if verbose:
        print("Date/Time           Script              ExecTime  Cmds/s  Lines/s  FP%   FM%   C%   PV%   JIT%  Skip%  JIT-Saved  Skip-Saved  Failed")
        print("-" * 125)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            exec_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            lines_per_sec = f"{row['lines_per_second']:.0f}"
            
            fp_rate = f"{row['fast_path_hit_rate']:.0f}%"
            fm_rate = f"{row['fast_math_hit_rate']:.0f}%"
            cache_rate = f"{row['cache_hit_rate']:.0f}%"
            parse_val = f"{safe_get_column(row, 'parse_value_hit_rate', 0):.0f}%"
            jit_rate = f"{safe_get_column(row, 'jit_hit_rate', 0):.0f}%"
            skip_rate = f"{safe_get_column(row, 'jit_skip_efficiency', 0):.0f}%"
            jit_saved = f"{safe_get_column(row, 'jit_time_saved', 0):.2f}s"
            skip_saved = f"{safe_get_column(row, 'jit_skip_time_saved', 0):.2f}s"
            failed = f"{safe_get_column(row, 'failed_lines_cached', 0)}"
            
            print(f"{date_str:19} {script:18} {exec_time:>8} {cmds_per_sec:>7} {lines_per_sec:>8} {fp_rate:>5} {fm_rate:>5} {cache_rate:>4} {parse_val:>5} {jit_rate:>5} {skip_rate:>6} {jit_saved:>10} {skip_saved:>11} {failed:>6}")
    
    else:
        print("Date/Time           Script              ExecTime  Cmds/s  FastPath%  FastMath%  Cache%  ParseVal%  JIT%  Skip%")
        print("-" * 108)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            exec_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            fast_path = f"{row['fast_path_hit_rate']:.0f}%"
            fast_math = f"{row['fast_math_hit_rate']:.0f}%"
            cache = f"{row['cache_hit_rate']:.0f}%"
            parse_val = f"{safe_get_column(row, 'parse_value_hit_rate', 0):.0f}%"
            jit_rate = f"{safe_get_column(row, 'jit_hit_rate', 0):.0f}%"
            skip_rate = f"{safe_get_column(row, 'jit_skip_efficiency', 0):.0f}%"
            
            print(f"{date_str:19} {script:18} {exec_time:>8} {cmds_per_sec:>7} {fast_path:>9} {fast_math:>9} {cache:>6} {parse_val:>9} {jit_rate:>5} {skip_rate:>6}")

def list_scripts():
    """List all scripts in database."""
    db = PixilMetricsDB()
    scripts = db.get_unique_scripts()
    
    if not scripts:
        print("No scripts found in database.")
        return
    
    print(f"\n=== Scripts in Database ({len(scripts)} total) ===")
    for script in scripts:
        print(f"  {script}")

if __name__ == '__main__':
    main()