-- Create table for caching order flow data
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS orderflow_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    key_type VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    data_type VARCHAR(50) DEFAULT 'json',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    params JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_orderflow_cache_key_type ON orderflow_cache(key_type);
CREATE INDEX IF NOT EXISTS idx_orderflow_cache_expires_at ON orderflow_cache(expires_at);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_orderflow_cache_updated_at 
    BEFORE UPDATE ON orderflow_cache 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add RLS (Row Level Security) policies if needed
ALTER TABLE orderflow_cache ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read/write cache
CREATE POLICY "Enable read access for all users" ON orderflow_cache
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON orderflow_cache
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON orderflow_cache
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete for all users" ON orderflow_cache
    FOR DELETE USING (true);

-- Optional: Create a function to clean expired cache entries
CREATE OR REPLACE FUNCTION clean_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM orderflow_cache WHERE expires_at < NOW();
END;
$$ language 'plpgsql';

-- Optional: Schedule the cleanup function to run periodically
-- This requires pg_cron extension to be enabled in Supabase
-- SELECT cron.schedule('clean-expired-cache', '0 */6 * * *', 'SELECT clean_expired_cache();');