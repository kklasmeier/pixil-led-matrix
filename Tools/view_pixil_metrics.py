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

def main():
    parser = argparse.ArgumentParser(description='View Pixil performance metrics')
    parser.add_argument('--recent', type=int, default=10, 
                       help='Show N most recent script runs (default: 10)')
    parser.add_argument('--script', type=str, 
                       help='Show history for specific script')
    parser.add_argument('--summary', action='store_true',
                       help='Show performance summary for last 7 days')
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
        if args.trends:
            show_script_trends(args.trends, args.count, args.verbose)
        elif args.trends_all:
            show_system_trends(args.count, args.verbose)
        elif args.script:
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
    """Show recent script executions."""
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
        
        # Include parse value optimization in the optimization summary
        try:
            parse_val_rate = row['parse_value_hit_rate'] or 0
            parse_val_time_saved = row['parse_value_time_saved'] or 0
        except (KeyError, TypeError):
            parse_val_rate = 0
            parse_val_time_saved = 0

        print(f"  Optimizations: Fast Path {row['fast_path_hit_rate']:.1f}%, Fast Math {row['fast_math_hit_rate']:.1f}%, Cache {row['cache_hit_rate']:.1f}%, Parse Value {parse_val_rate:.1f}%")

        total_saved = (row['fast_path_time_saved'] + row['fast_math_time_saved'] + 
                    row['cache_time_saved'] + parse_val_time_saved)

        print(f"  Time Saved: {total_saved:.3f}s")
        print()

def calculate_trends(history, script_name):
    """Calculate and display trend indicators."""
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
    
    # Trend indicators
    cmd_trend = "↗" if recent_avg_cmds > older_avg_cmds * 1.02 else "↘" if recent_avg_cmds < older_avg_cmds * 0.98 else "→"
    time_trend = "↗" if recent_avg_time < older_avg_time * 0.98 else "↘" if recent_avg_time > older_avg_time * 1.02 else "→"
    fp_trend = "↗" if recent_avg_fp > older_avg_fp * 1.01 else "↘" if recent_avg_fp < older_avg_fp * 0.99 else "→"
    
    print(f"Trends: Commands/sec {cmd_trend}  Execution time {time_trend}  Fast path optimization {fp_trend}")
    print(f"Recent avg: {recent_avg_cmds:.0f} cmds/s, {recent_avg_time:.1f}s, {recent_avg_fp:.0f}% fast path")

def show_script_history(script_name):
    """Show performance history for specific script."""
    db = PixilMetricsDB()
    history = db.get_metrics_by_script(script_name)
    
    if not history:
        print(f"No data found for script: {script_name}")
        return
    
    print(f"\n=== Performance History for {script_name} ===")
    print(f"Total executions: {len(history)}")
    
    # Calculate averages
    completed = [row for row in history if row['execution_reason'] == 'complete']
    if completed:
        avg_duration = sum(row['total_execution_time'] for row in completed) / len(completed)
        avg_commands_per_sec = sum(row['commands_per_second'] for row in completed) / len(completed)
        avg_fast_path = sum(row['fast_path_hit_rate'] for row in completed) / len(completed)
        
        print(f"Completed executions: {len(completed)}")
        print(f"Average duration: {avg_duration:.3f}s")
        print(f"Average performance: {avg_commands_per_sec:.1f} commands/sec")
        print(f"Average fast path hit rate: {avg_fast_path:.1f}%")
    
    print("\nRecent executions:")
    for row in history[:5]:  # Show last 5
        status = row['execution_reason']
        print(f"  {row['start_time']}: {row['total_execution_time']:.3f}s, {row['commands_per_second']:.1f} cmds/sec ({status})")

def show_summary():
    """Show overall performance summary."""
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

def show_script_trends(script_name, count, verbose=False):
    """Show performance trends for a specific script in compact or verbose format."""
    db = PixilMetricsDB()
    history = db.get_metrics_by_script(script_name)
    
    if not history:
        print(f"No data found for script: {script_name}")
        return
    
    # Take only the requested number of most recent executions
    recent_history = history[:count]
    
    print(f"\n=== Performance Trends: {script_name} (Last {len(recent_history)} executions) ===")
    
    if verbose:
        print("Date/Time           Script              TotalTime ActTime  Cmds/s   Lines/s    FP-Hits   FP-Tries  FP%     FM-Hits     FM-Tries   FM%   C-Hits   C-Tries  C%   PV-Hits   PV-Tries  PV%   C-Size")
        print("-" * 185)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            total_time = f"{row['total_execution_time']:.1f}s"
            active_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            lines_per_sec = f"{row['lines_per_second']:.0f}"
            
            # Optimization metrics with hit rates
            fp_hits = f"{row['fast_path_hits']:,}"
            fp_tries = f"{row['fast_path_attempts']:,}"
            fp_rate = f"{row['fast_path_hit_rate']:.0f}%"
            
            fm_hits = f"{row['fast_math_hits']:,}"
            fm_tries = f"{row['fast_math_attempts']:,}"
            fm_rate = f"{row['fast_math_hit_rate']:.0f}%"
            
            cache_hits = f"{row['cache_hits']:,}"
            cache_tries = f"{row['cache_attempts']:,}"
            cache_rate = f"{row['cache_hit_rate']:.0f}%"
            cache_size = f"{row['cache_size']}"
            
            # Parse value metrics (with safe defaults for old records)
            try:
                pv_hits_val = (row['parse_value_ultra_fast_hits'] or 0) + (row['parse_value_fast_hits'] or 0)
                pv_tries_val = row['parse_value_attempts'] or 0
                pv_rate_val = row['parse_value_hit_rate'] or 0
            except (KeyError, TypeError):
                pv_hits_val = 0
                pv_tries_val = 0
                pv_rate_val = 0

            pv_hits = f"{pv_hits_val:,}"
            pv_tries = f"{pv_tries_val:,}"
            pv_rate = f"{pv_rate_val:.0f}%"

            print(f"{date_str:19} {script:18} {total_time:>9} {active_time:>8} {cmds_per_sec:>8} {lines_per_sec:>8} {fp_hits:>10} {fp_tries:>10} {fp_rate:>7} {fm_hits:>11} {fm_tries:>10} {fm_rate:>5} {cache_hits:>8} {cache_tries:>9} {cache_rate:>4} {pv_hits:>9} {pv_tries:>10} {pv_rate:>5} {cache_size:>6}")

    else:
        # Compact format - add ParseVal% column
        print("Date/Time           ExecTime  Cmds/s  Lines/s  FastPath%  FastMath%  Cache%  ParseVal%")
        print("-" * 88)
        
        for row in reversed(recent_history):
            date_str = row['start_time'][:16].replace('T', ' ')
            exec_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            lines_per_sec = f"{row['lines_per_second']:.0f}"
            fast_path = f"{row['fast_path_hit_rate']:.0f}%"
            fast_math = f"{row['fast_math_hit_rate']:.0f}%"
            cache = f"{row['cache_hit_rate']:.0f}%"
            # Parse value hit rate (with safe default for old records)
            try:
                parse_val = f"{row['parse_value_hit_rate']:.0f}%"
            except (KeyError, TypeError):
                parse_val = "0%"

            print(f"{date_str:19} {exec_time:>8} {cmds_per_sec:>7} {lines_per_sec:>8} {fast_path:>9} {fast_math:>9} {cache:>6} {parse_val:>9}")
    
    # Calculate trends
    if len(recent_history) >= 2:
        print("\n" + "=" * (185 if verbose else 88))
        calculate_trends(recent_history, script_name)

def show_system_trends(count, verbose=False):
    """Show system-wide performance trends in compact or verbose format."""
    db = PixilMetricsDB()
    
    with db.get_connection() as conn:
        if verbose:
            cursor = conn.execute('''
                SELECT script_name, start_time, total_execution_time, active_execution_time, 
                       commands_executed, commands_per_second, script_lines_processed, lines_per_second,
                       fast_path_hits, fast_path_attempts, fast_path_hit_rate,
                       fast_math_hits, fast_math_attempts, fast_math_hit_rate,
                       cache_hits, cache_attempts, cache_hit_rate, cache_size,
                       parse_value_ultra_fast_hits, parse_value_fast_hits, parse_value_attempts, parse_value_hit_rate
                FROM script_metrics 
                WHERE execution_reason = 'complete'
                ORDER BY start_time DESC
                LIMIT ?
            ''', (count,))
        else:
            cursor = conn.execute('''
                SELECT script_name, start_time, active_execution_time, commands_per_second, 
                       lines_per_second, fast_path_hit_rate, fast_math_hit_rate, cache_hit_rate,
                       parse_value_hit_rate
                FROM script_metrics 
                WHERE execution_reason = 'complete'
                ORDER BY start_time DESC
                LIMIT ?
            ''', (count,))
        
        history = cursor.fetchall()
    
    if not history:
        print("No completed executions found.")
        return
    
    print(f"\n=== System-Wide Performance Trends (Last {len(history)} executions) ===")
    
    if verbose:
        print("Date/Time           Script              TotalTime ActTime  Cmds     Lines    FP:Hits/Tries    FM:Hits/Tries    C:Hits/Tries/Size    PV:Hits/Tries")
        print("-" * 160)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            total_time = f"{row['total_execution_time']:.1f}s"
            active_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}/s"
            lines_per_sec = f"{row['lines_per_second']:.0f}/s"
            
            fp_detail = f"{row['fast_path_hits']:,}/{row['fast_path_attempts']:,}"
            fm_detail = f"{row['fast_math_hits']:,}/{row['fast_math_attempts']:,}"
            cache_detail = f"{row['cache_hits']:,}/{row['cache_attempts']:,}/{row['cache_size']}"
            
            # NEW: Parse value details (with safe defaults)
            pv_total_hits = (row.get('parse_value_ultra_fast_hits', 0) + row.get('parse_value_fast_hits', 0))
            pv_detail = f"{pv_total_hits:,}/{row.get('parse_value_attempts', 0):,}"
            
            print(f"{date_str:19} {script:18} {total_time:>8} {active_time:>7} {cmds_per_sec:>8} {lines_per_sec:>8} {fp_detail:>16} {fm_detail:>16} {cache_detail:>16} {pv_detail:>16}")
    
    else:
        print("Date/Time           Script              ExecTime  Cmds/s  FastPath%  FastMath%  Cache%  ParseVal%")
        print("-" * 98)
        
        for row in reversed(history):
            date_str = row['start_time'][:16].replace('T', ' ')
            script = row['script_name'][:18]
            exec_time = f"{row['active_execution_time']:.1f}s"
            cmds_per_sec = f"{row['commands_per_second']:.0f}"
            fast_path = f"{row['fast_path_hit_rate']:.0f}%"
            fast_math = f"{row['fast_math_hit_rate']:.0f}%"
            cache = f"{row['cache_hit_rate']:.0f}%"

            # Parse value hit rate
            try:
                parse_val = f"{row['parse_value_hit_rate']:.0f}%"
            except (KeyError, TypeError):
                parse_val = "0%"  # Default for old records without this column

            
            print(f"{date_str:19} {script:18} {exec_time:>8} {cmds_per_sec:>7} {fast_path:>9} {fast_math:>9} {cache:>6} {parse_val:>9}")

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