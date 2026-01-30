import os
import json
import asyncio
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseMTFTables:
    """Creates and manages Supabase tables for MTF data"""
    
    def __init__(self):
        # Get Supabase credentials
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        print(f"Connected to Supabase: {self.supabase_url}")
    
    def create_tables_sql(self) -> str:
        """Generate SQL to create MTF tables with hl_ prefix"""
        
        sql = """
-- Drop existing tables if they exist
DROP TABLE IF EXISTS hl_mtf_output CASCADE;
DROP TABLE IF EXISTS hl_mtf_context CASCADE;

-- Create MTF Context table (input data)
CREATE TABLE hl_mtf_context (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p NUMERIC(20, 2) NOT NULL,
    exec_tf INTEGER NOT NULL,
    tf INTEGER[] NOT NULL,
    px_z NUMERIC(10, 3)[] NOT NULL,
    v_z NUMERIC(10, 3)[] NOT NULL,
    vwap_z NUMERIC(10, 3)[] NOT NULL,
    bb_pos NUMERIC(10, 3)[] NOT NULL,
    atr_n NUMERIC(10, 3)[] NOT NULL,
    cvd_s NUMERIC(10, 3)[] NOT NULL,
    cvd_lvl NUMERIC(10, 3)[] NOT NULL,
    oi_d NUMERIC(10, 3)[] NOT NULL,
    liq_n NUMERIC(10, 3)[] NOT NULL,
    reg INTEGER[] NOT NULL,
    l_sup NUMERIC(20, 2) NOT NULL,
    l_res NUMERIC(20, 2) NOT NULL,
    l_q_bid NUMERIC(10, 2) NOT NULL,
    l_q_ask NUMERIC(10, 2) NOT NULL,
    l_dsup NUMERIC(10, 3) NOT NULL,
    l_dres NUMERIC(10, 3) NOT NULL,
    basis_bp NUMERIC(10, 1) NOT NULL,
    fund_bp NUMERIC(10, 1) NOT NULL,
    px_disp_bp NUMERIC(10, 2) NOT NULL,
    pos NUMERIC(10, 3) NOT NULL,
    avg NUMERIC(20, 2) NOT NULL,
    unrlz NUMERIC(10, 2) NOT NULL,
    rsk INTEGER NOT NULL,
    hr12 NUMERIC(5, 2) NOT NULL,
    slip_bp NUMERIC(10, 2) NOT NULL,
    dd_pct NUMERIC(10, 2) NOT NULL
);

-- Create MTF Output table (LLM predictions)
CREATE TABLE hl_mtf_output (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    context_id BIGINT REFERENCES hl_mtf_context(id) ON DELETE CASCADE,
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p NUMERIC(20, 2) NOT NULL,
    tf INTEGER[] NOT NULL,
    s INTEGER[] NOT NULL,
    c INTEGER[] NOT NULL,
    o INTEGER[] NOT NULL,
    f INTEGER[] NOT NULL,
    conf INTEGER[] NOT NULL,
    s_a INTEGER NOT NULL,
    f_a INTEGER NOT NULL,
    conf_a INTEGER NOT NULL,
    prob_cont INTEGER NOT NULL,
    sc_in INTEGER NOT NULL,
    sc_out INTEGER NOT NULL,
    hold INTEGER NOT NULL,
    tp_atr NUMERIC(10, 2) NOT NULL,
    sl_atr NUMERIC(10, 2) NOT NULL,
    hedge INTEGER NOT NULL,
    reasons INTEGER[] NOT NULL
);

-- Create indices for better query performance
CREATE INDEX idx_hl_mtf_context_sym ON hl_mtf_context(sym);
CREATE INDEX idx_hl_mtf_context_t ON hl_mtf_context(t);
CREATE INDEX idx_hl_mtf_context_created ON hl_mtf_context(created_at);

CREATE INDEX idx_hl_mtf_output_sym ON hl_mtf_output(sym);
CREATE INDEX idx_hl_mtf_output_t ON hl_mtf_output(t);
CREATE INDEX idx_hl_mtf_output_context ON hl_mtf_output(context_id);
CREATE INDEX idx_hl_mtf_output_created ON hl_mtf_output(created_at);

-- Create views for easier data access
CREATE VIEW hl_mtf_latest_context AS
SELECT DISTINCT ON (sym) *
FROM hl_mtf_context
ORDER BY sym, created_at DESC;

CREATE VIEW hl_mtf_latest_output AS
SELECT DISTINCT ON (sym) *
FROM hl_mtf_output
ORDER BY sym, created_at DESC;

-- Add comments for documentation
COMMENT ON TABLE hl_mtf_context IS 'Multi-timeframe context data from Hyperliquid';
COMMENT ON TABLE hl_mtf_output IS 'LLM predictions based on MTF context';

COMMENT ON COLUMN hl_mtf_context.sym IS 'Symbol ID (1=BTC, 2=ETH, 3=SOL, etc.)';
COMMENT ON COLUMN hl_mtf_context.t IS 'Unix timestamp';
COMMENT ON COLUMN hl_mtf_context.p IS 'Current price';
COMMENT ON COLUMN hl_mtf_context.exec_tf IS 'Execution timeframe in minutes';
COMMENT ON COLUMN hl_mtf_context.tf IS 'Timeframes array [10080, 1440, 240, 60, 15, 5] (1w, 1d, 4h, 1h, 15m, 5m)';
COMMENT ON COLUMN hl_mtf_context.px_z IS 'Price z-scores for each timeframe';
COMMENT ON COLUMN hl_mtf_context.v_z IS 'Volume z-scores for each timeframe';
COMMENT ON COLUMN hl_mtf_context.cvd_s IS 'CVD signal for each timeframe';
COMMENT ON COLUMN hl_mtf_context.cvd_lvl IS 'CVD level for each timeframe';
COMMENT ON COLUMN hl_mtf_context.oi_d IS 'Open interest delta for each timeframe';

COMMENT ON COLUMN hl_mtf_output.s IS 'Structure signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.c IS 'Context signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.o IS 'Orderflow signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.f IS 'Flow signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.conf IS 'Confidence scores per timeframe';
COMMENT ON COLUMN hl_mtf_output.s_a IS 'Aggregate structure signal';
COMMENT ON COLUMN hl_mtf_output.f_a IS 'Aggregate flow signal';
COMMENT ON COLUMN hl_mtf_output.prob_cont IS 'Probability of continuation (%)';
COMMENT ON COLUMN hl_mtf_output.tp_atr IS 'Take profit in ATR units';
COMMENT ON COLUMN hl_mtf_output.sl_atr IS 'Stop loss in ATR units';
"""
        return sql
    
    async def execute_sql(self, sql: str):
        """Execute SQL directly using Supabase RPC or admin API"""
        try:
            # Split SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement:
                    print(f"Executing: {statement[:100]}...")
                    # Note: Supabase Python client doesn't directly support raw SQL execution
                    # You would need to use the Supabase Database REST API or connect via psycopg2
                    # For now, we'll save the SQL to a file for manual execution
            
            return True
            
        except Exception as e:
            print(f"Error executing SQL: {e}")
            return False
    
    async def insert_sample_data(self):
        """Insert sample data from the real MTF context file"""
        try:
            # Read the real MTF context data
            with open('real_mtf_context.jsonl', 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.strip():
                    data = json.loads(line)
                    
                    # Prepare data for insertion
                    # Convert NaN to None for proper handling
                    for key in data:
                        if isinstance(data[key], float) and str(data[key]) == 'nan':
                            data[key] = None
                        elif isinstance(data[key], list):
                            data[key] = [None if (isinstance(x, float) and str(x) == 'nan') else x for x in data[key]]
                    
                    # Rename fields to match database schema
                    db_data = {
                        'sym': data['sym'],
                        't': data['t'],
                        'p': data['p'],
                        'exec_tf': data['exec_tf'],
                        'tf': data['TF'],
                        'px_z': data['px_z'],
                        'v_z': data['v_z'],
                        'vwap_z': data['vwap_z'],
                        'bb_pos': data['bb_pos'],
                        'atr_n': data['atr_n'],
                        'cvd_s': data['cvd_s'],
                        'cvd_lvl': data['cvd_lvl'],
                        'oi_d': data['oi_d'],
                        'liq_n': data['liq_n'],
                        'reg': data['reg'],
                        'l_sup': data['L_sup'],
                        'l_res': data['L_res'],
                        'l_q_bid': data['L_q_bid'],
                        'l_q_ask': data['L_q_ask'],
                        'l_dsup': data['L_dsup'],
                        'l_dres': data['L_dres'],
                        'basis_bp': data['basis_bp'],
                        'fund_bp': data['fund_bp'],
                        'px_disp_bp': data['px_disp_bp'],
                        'pos': data['pos'],
                        'avg': data['avg'],
                        'unrlz': data['unrlz'],
                        'rsk': data['rsk'],
                        'hr12': data['hr12'],
                        'slip_bp': data['slip_bp'],
                        'dd_pct': data['dd_pct']
                    }
                    
                    # Insert into Supabase
                    result = self.supabase.table('hl_mtf_context').insert(db_data).execute()
                    print(f"Inserted context for symbol {data['sym']}: {result.data[0]['id'] if result.data else 'Failed'}")
            
            print("Sample data insertion complete")
            return True
            
        except Exception as e:
            print(f"Error inserting sample data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_tables(self):
        """Test that the tables were created and can be queried"""
        try:
            # Test querying the context table
            result = self.supabase.table('hl_mtf_context').select("*").limit(5).execute()
            print(f"\nFound {len(result.data)} records in hl_mtf_context")
            
            if result.data:
                print(f"Sample record: Symbol {result.data[0]['sym']}, Price: ${result.data[0]['p']}")
            
            # Test the latest context view
            result = self.supabase.table('hl_mtf_latest_context').select("*").execute()
            print(f"\nFound {len(result.data)} latest contexts")
            
            for record in result.data:
                print(f"  Symbol {record['sym']}: ${record['p']:.2f}")
            
            return True
            
        except Exception as e:
            print(f"Error testing tables: {e}")
            return False

async def main():
    """Main function to create tables and insert data"""
    creator = SupabaseMTFTables()
    
    # Generate SQL
    sql = creator.create_tables_sql()
    
    # Save SQL to file
    sql_file = "create_hl_mtf_tables.sql"
    with open(sql_file, 'w') as f:
        f.write(sql)
    print(f"\nSQL saved to {sql_file}")
    print("\nTo execute in Supabase:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the SQL from the file")
    print("4. Click 'Run'")
    
    # Try to insert sample data
    print("\nAttempting to insert sample data...")
    success = await creator.insert_sample_data()
    
    if success:
        # Test the tables
        print("\nTesting tables...")
        await creator.test_tables()

if __name__ == "__main__":
    asyncio.run(main())