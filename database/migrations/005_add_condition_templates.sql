-- Migration for condition template metrics
ALTER TABLE script_metrics ADD COLUMN condition_template_attempts INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN condition_template_hits INTEGER DEFAULT 0;
ALTER TABLE script_metrics ADD COLUMN condition_template_hit_rate REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN condition_template_time_saved REAL DEFAULT 0.0;
ALTER TABLE script_metrics ADD COLUMN condition_template_cache_size INTEGER DEFAULT 0;

-- Index for condition template analysis
CREATE INDEX IF NOT EXISTS idx_condition_template_metrics ON script_metrics(
    condition_template_hit_rate,
    condition_template_time_saved,
    execution_reason
);