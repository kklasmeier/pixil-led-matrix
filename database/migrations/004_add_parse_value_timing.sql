-- database/migrations/004_add_parse_value_timing.sql
-- Migration to add parse_value timing statistics
-- Created: 2025-06-01

-- Add parse_value total time column to existing script_metrics table
ALTER TABLE script_metrics ADD COLUMN parse_value_total_time REAL DEFAULT 0.0;

-- Add parse_value average time per call (calculated column for convenience)
ALTER TABLE script_metrics ADD COLUMN parse_value_avg_time_per_call REAL DEFAULT 0.0;

-- Create index for parse_value timing analysis
CREATE INDEX IF NOT EXISTS idx_parse_value_timing ON script_metrics(
    parse_value_total_time,
    parse_value_attempts,
    execution_reason
);

-- Create index for parse_value performance analysis
CREATE INDEX IF NOT EXISTS idx_parse_value_performance ON script_metrics(
    parse_value_total_time,
    total_execution_time,
    execution_reason
);