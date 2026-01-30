-- Create a monitoring view that shows the most recent record from each hl_ table
-- This view provides a unified dashboard of all indicator statuses

CREATE OR REPLACE VIEW public.hl_monitoring_dashboard AS
WITH 
-- CVD Current Status
cvd_current_latest AS (
    SELECT 
        'CVD Current' as indicator_type,
        symbol,
        cvd as value,
        buy_volume,
        sell_volume,
        trend as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_cvd_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_cvd_current)
    LIMIT 1
),

-- CVD Snapshots
cvd_snapshots_latest AS (
    SELECT 
        'CVD Snapshots' as indicator_type,
        symbol,
        cvd as value,
        buy_volume,
        sell_volume,
        NULL as signal,
        timestamp as last_updated,
        EXTRACT(EPOCH FROM (NOW() - timestamp)) / 60 as minutes_ago
    FROM hl_cvd_snapshots
    WHERE timestamp = (SELECT MAX(timestamp) FROM hl_cvd_snapshots)
    LIMIT 1
),

-- Open Interest Current
oi_current_latest AS (
    SELECT 
        'OI Current' as indicator_type,
        symbol,
        open_interest as value,
        oi_24h_change as buy_volume,
        oi_percentage_change as sell_volume,
        trend as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_oi_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_oi_current)
    LIMIT 1
),

-- Open Interest Snapshots
oi_snapshots_latest AS (
    SELECT 
        'OI Snapshots' as indicator_type,
        symbol,
        open_interest as value,
        oi_24h_change as buy_volume,
        oi_percentage_change as sell_volume,
        NULL as signal,
        timestamp as last_updated,
        EXTRACT(EPOCH FROM (NOW() - timestamp)) / 60 as minutes_ago
    FROM hl_oi_snapshots
    WHERE timestamp = (SELECT MAX(timestamp) FROM hl_oi_snapshots)
    LIMIT 1
),

-- Funding Rate Current
funding_current_latest AS (
    SELECT 
        'Funding Current' as indicator_type,
        symbol,
        funding_rate as value,
        funding_rate_1h_avg as buy_volume,
        funding_rate_24h_avg as sell_volume,
        trend as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_funding_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_funding_current)
    LIMIT 1
),

-- Funding Rate Snapshots
funding_snapshots_latest AS (
    SELECT 
        'Funding Snapshots' as indicator_type,
        symbol,
        funding_rate as value,
        funding_rate_1h_avg as buy_volume,
        funding_rate_24h_avg as sell_volume,
        NULL as signal,
        timestamp as last_updated,
        EXTRACT(EPOCH FROM (NOW() - timestamp)) / 60 as minutes_ago
    FROM hl_funding_snapshots
    WHERE timestamp = (SELECT MAX(timestamp) FROM hl_funding_snapshots)
    LIMIT 1
),

-- Volume Profile Current
volume_profile_current_latest AS (
    SELECT 
        'Volume Profile Current' as indicator_type,
        symbol,
        poc_session as value,
        value_area_high as buy_volume,
        value_area_low as sell_volume,
        position_relative_to_va as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_volume_profile_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_volume_profile_current)
    LIMIT 1
),

-- Volume Profile Snapshots
volume_profile_snapshots_latest AS (
    SELECT 
        'Volume Profile Snapshots' as indicator_type,
        symbol,
        poc as value,
        value_area_high as buy_volume,
        value_area_low as sell_volume,
        NULL as signal,
        timestamp as last_updated,
        EXTRACT(EPOCH FROM (NOW() - timestamp)) / 60 as minutes_ago
    FROM hl_volume_profile_snapshots
    WHERE timestamp = (SELECT MAX(timestamp) FROM hl_volume_profile_snapshots)
    LIMIT 1
),

-- VWAP Current
vwap_current_latest AS (
    SELECT 
        'VWAP Current' as indicator_type,
        symbol,
        vwap as value,
        current_price as buy_volume,
        deviation_percentage as sell_volume,
        trend as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_vwap_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_vwap_current)
    LIMIT 1
),

-- ATR Current
atr_current_latest AS (
    SELECT 
        'ATR Current' as indicator_type,
        symbol,
        atr as value,
        atr_percentage as buy_volume,
        volatility_level as sell_volume,
        NULL as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_atr_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_atr_current)
    LIMIT 1
),

-- Bollinger Bands Current
bollinger_current_latest AS (
    SELECT 
        'Bollinger Current' as indicator_type,
        symbol,
        middle_band as value,
        upper_band as buy_volume,
        lower_band as sell_volume,
        signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_bollinger_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_bollinger_current)
    LIMIT 1
),

-- Support Resistance Current
sr_current_latest AS (
    SELECT 
        'Support Resistance' as indicator_type,
        symbol,
        current_price as value,
        nearest_resistance as buy_volume,
        nearest_support as sell_volume,
        NULL as signal,
        updated_at as last_updated,
        EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_ago
    FROM hl_sr_current
    WHERE updated_at = (SELECT MAX(updated_at) FROM hl_sr_current)
    LIMIT 1
)

-- Combine all results
SELECT * FROM cvd_current_latest
UNION ALL
SELECT * FROM cvd_snapshots_latest
UNION ALL
SELECT * FROM oi_current_latest
UNION ALL
SELECT * FROM oi_snapshots_latest
UNION ALL
SELECT * FROM funding_current_latest
UNION ALL
SELECT * FROM funding_snapshots_latest
UNION ALL
SELECT * FROM volume_profile_current_latest
UNION ALL
SELECT * FROM volume_profile_snapshots_latest
UNION ALL
SELECT * FROM vwap_current_latest
UNION ALL
SELECT * FROM atr_current_latest
UNION ALL
SELECT * FROM bollinger_current_latest
UNION ALL
SELECT * FROM sr_current_latest
ORDER BY minutes_ago ASC;

-- Grant permissions
GRANT SELECT ON public.hl_monitoring_dashboard TO anon;
GRANT SELECT ON public.hl_monitoring_dashboard TO authenticated;

-- Create an additional summary view for quick status checks
CREATE OR REPLACE VIEW public.hl_table_summary AS
SELECT 
    table_name,
    record_count,
    latest_update,
    CASE 
        WHEN EXTRACT(EPOCH FROM (NOW() - latest_update)) / 60 < 5 THEN 'Active'
        WHEN EXTRACT(EPOCH FROM (NOW() - latest_update)) / 60 < 60 THEN 'Recent'
        WHEN EXTRACT(EPOCH FROM (NOW() - latest_update)) / 60 < 1440 THEN 'Stale'
        ELSE 'Inactive'
    END as status,
    ROUND(EXTRACT(EPOCH FROM (NOW() - latest_update)) / 60, 2) as minutes_since_update
FROM (
    SELECT 'hl_cvd_current' as table_name, COUNT(*) as record_count, MAX(updated_at) as latest_update FROM hl_cvd_current
    UNION ALL
    SELECT 'hl_cvd_snapshots', COUNT(*), MAX(timestamp) FROM hl_cvd_snapshots
    UNION ALL
    SELECT 'hl_oi_current', COUNT(*), MAX(updated_at) FROM hl_oi_current
    UNION ALL
    SELECT 'hl_oi_snapshots', COUNT(*), MAX(timestamp) FROM hl_oi_snapshots
    UNION ALL
    SELECT 'hl_funding_current', COUNT(*), MAX(updated_at) FROM hl_funding_current
    UNION ALL
    SELECT 'hl_funding_snapshots', COUNT(*), MAX(timestamp) FROM hl_funding_snapshots
    UNION ALL
    SELECT 'hl_volume_profile_current', COUNT(*), MAX(updated_at) FROM hl_volume_profile_current
    UNION ALL
    SELECT 'hl_volume_profile_snapshots', COUNT(*), MAX(timestamp) FROM hl_volume_profile_snapshots
    UNION ALL
    SELECT 'hl_vwap_current', COUNT(*), MAX(updated_at) FROM hl_vwap_current
    UNION ALL
    SELECT 'hl_vwap_snapshots', COUNT(*), MAX(timestamp) FROM hl_vwap_snapshots
    UNION ALL
    SELECT 'hl_atr_current', COUNT(*), MAX(updated_at) FROM hl_atr_current
    UNION ALL
    SELECT 'hl_atr_snapshots', COUNT(*), MAX(timestamp) FROM hl_atr_snapshots
    UNION ALL
    SELECT 'hl_bollinger_current', COUNT(*), MAX(updated_at) FROM hl_bollinger_current
    UNION ALL
    SELECT 'hl_bollinger_snapshots', COUNT(*), MAX(timestamp) FROM hl_bollinger_snapshots
    UNION ALL
    SELECT 'hl_sr_current', COUNT(*), MAX(updated_at) FROM hl_sr_current
    UNION ALL
    SELECT 'hl_sr_snapshots', COUNT(*), MAX(timestamp) FROM hl_sr_snapshots
) as table_stats
ORDER BY minutes_since_update ASC;

-- Grant permissions
GRANT SELECT ON public.hl_table_summary TO anon;
GRANT SELECT ON public.hl_table_summary TO authenticated;