-- database/migrations/003_add_detailed_parse_value_metrics.sql
-- Migration to add detailed parse value optimization statistics
-- Created: 2025-05-30
-- Adds separate tracking for Ultra Fast Path, Fast Path, and Parse Value Cache

-- Add Ultra Fast Path optimization metrics
ALTER TABLE script_metrics ADD COLUMN ultra_fast_attempts INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN ultra_fast_hits INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN ultra_fast_hit_rate REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN ultra_fast_time_saved REAL DEFAULT 0.0;

-- Add Fast Path (parse value) optimization metrics  
ALTER TABLE script_metrics ADD COLUMN fast_path_parse_attempts INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN fast_path_parse_hits INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN fast_path_parse_hit_rate REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN fast_path_parse_time_saved REAL DEFAULT 0.0;

-- Add Variable Cache specific metrics (rename existing for clarity)
ALTER TABLE script_metrics ADD COLUMN var_cache_attempts INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN var_cache_hits INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN var_cache_hit_rate REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN var_cache_time_saved REAL DEFAULT 0.0;

-- Create composite index for detailed parse value optimization analysis
CREATE INDEX IF NOT EXISTS idx_detailed_parse_value_metrics ON script_metrics(
    ultra_fast_hit_rate,
    fast_path_parse_hit_rate,
    var_cache_hit_rate,
    execution_reason
);

-- Create index for parse value time savings analysis
CREATE INDEX IF NOT EXISTS idx_parse_value_time_savings ON script_metrics(
    ultra_fast_time_saved,
    fast_path_parse_time_saved,
    var_cache_time_saved,
    execution_reason
);

-- Create index for parse value attempts tracking
CREATE INDEX IF NOT EXISTS idx_parse_value_attempts ON script_metrics(
    parse_value_attempts,
    ultra_fast_attempts,
    fast_path_parse_attempts,
    var_cache_attempts,
    execution_reason
);