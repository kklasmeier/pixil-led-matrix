-- Initial schema for Pixil performance metrics database
-- Migration: 001_pixil_initial
-- Created: 2025-01-XX
-- Updated: 2025-05-25 - Added parse value optimization metrics

-- Main table for storing Pixil script execution metrics
CREATE TABLE IF NOT EXISTS script_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Script identification and timing
    script_name TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    execution_reason TEXT DEFAULT 'complete',  -- 'complete', 'interrupted', 'error'
    
    -- Core performance metrics
    commands_executed INTEGER DEFAULT 0,
    script_lines_processed INTEGER DEFAULT 0,
    total_execution_time REAL DEFAULT 0.0,
    active_execution_time REAL DEFAULT 0.0,
    commands_per_second REAL DEFAULT 0.0,
    lines_per_second REAL DEFAULT 0.0,
    
    -- Phase 1 optimization metrics (Fast Path)
    fast_path_attempts INTEGER DEFAULT 0,
    fast_path_hits INTEGER DEFAULT 0,
    fast_path_hit_rate REAL DEFAULT 0.0,
    fast_path_time_saved REAL DEFAULT 0.0,
    
    -- Phase 2 optimization metrics (Fast Math)
    fast_math_attempts INTEGER DEFAULT 0,
    fast_math_hits INTEGER DEFAULT 0,
    fast_math_hit_rate REAL DEFAULT 0.0,
    fast_math_time_saved REAL DEFAULT 0.0,
    
    -- Expression cache metrics
    cache_attempts INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_hit_rate REAL DEFAULT 0.0,
    cache_size INTEGER DEFAULT 0,
    cache_time_saved REAL DEFAULT 0.0,
    
    -- Parse value optimization metrics (Phase 3)
    parse_value_attempts INTEGER DEFAULT 0,
    parse_value_ultra_fast_hits INTEGER DEFAULT 0,
    parse_value_fast_hits INTEGER DEFAULT 0,
    parse_value_hit_rate REAL DEFAULT 0.0,
    parse_value_time_saved REAL DEFAULT 0.0,
    
    -- Parse value detailed breakdown
    direct_integer_hits INTEGER DEFAULT 0,
    direct_color_hits INTEGER DEFAULT 0,
    direct_string_hits INTEGER DEFAULT 0,
    simple_array_hits INTEGER DEFAULT 0,
    simple_arithmetic_hits INTEGER DEFAULT 0,
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_script_name ON script_metrics(script_name);
CREATE INDEX IF NOT EXISTS idx_start_time ON script_metrics(start_time);
CREATE INDEX IF NOT EXISTS idx_created_at ON script_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_execution_reason ON script_metrics(execution_reason);
CREATE INDEX IF NOT EXISTS idx_script_date ON script_metrics(script_name, start_time);

-- Index for performance analysis queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics ON script_metrics(
    commands_per_second, 
    lines_per_second, 
    execution_reason
);

-- Composite index for optimization analysis
CREATE INDEX IF NOT EXISTS idx_optimization_rates ON script_metrics(
    fast_path_hit_rate,
    fast_math_hit_rate,
    cache_hit_rate,
    parse_value_hit_rate,
    execution_reason
);

-- Index for parse value optimization analysis
CREATE INDEX IF NOT EXISTS idx_parse_value_metrics ON script_metrics(
    parse_value_hit_rate,
    parse_value_time_saved,
    execution_reason
);