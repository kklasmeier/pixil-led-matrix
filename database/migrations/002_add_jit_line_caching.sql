-- database/migrations/002_add_jit_line_caching.sql
-- Migration to add JIT line caching statistics
-- Created: 2025-05-26

-- Add JIT line caching columns to existing script_metrics table
ALTER TABLE script_metrics ADD COLUMN jit_attempts INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN jit_hits INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN jit_failures INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN jit_hit_rate REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN jit_time_saved REAL DEFAULT 0.0;

-- New JIT line caching specific metrics
ALTER TABLE script_metrics ADD COLUMN jit_line_cache_skips INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN failed_lines_cached INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN jit_skip_efficiency REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN jit_skip_time_saved REAL DEFAULT 0.0;

-- JIT cache utilization metrics
ALTER TABLE script_metrics ADD COLUMN jit_cache_size INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN jit_cache_utilization REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN jit_compilation_time REAL DEFAULT 0.0;

-- Create indexes for new JIT metrics
CREATE INDEX IF NOT EXISTS idx_jit_performance ON script_metrics(
    jit_hit_rate,
    jit_skip_efficiency,
    execution_reason
);

CREATE INDEX IF NOT EXISTS idx_jit_time_savings ON script_metrics(
    jit_time_saved,
    jit_skip_time_saved,
    execution_reason
);