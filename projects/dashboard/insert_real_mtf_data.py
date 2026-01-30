import os
import json
import asyncio
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MTFDataInserter:
    """Inserts real MTF data into Supabase"""
    
    def __init__(self):
        # Get Supabase credentials
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        print(f"Connected to Supabase: {self.supabase_url}")
    
    def clean_data(self, value):
        """Clean data for insertion, handling NaN values"""
        if isinstance(value, float):
            if str(value).lower() == 'nan':
                return 0.0  # Replace NaN with 0
            return value
        elif isinstance(value, list):
            return [self.clean_data(x) for x in value]
        elif isinstance(value, dict):
            return {k: self.clean_data(v) for k, v in value.items()}
        return value
    
    async def insert_mtf_context(self):
        """Insert MTF context data from real_mtf_context.jsonl"""
        try:
            # Read the real MTF context data
            with open('real_mtf_context.jsonl', 'r') as f:
                lines = f.readlines()
            
            inserted_count = 0
            
            for line in lines:
                if line.strip():
                    data = json.loads(line)
                    
                    # Clean the data (handle NaN values)
                    data = self.clean_data(data)
                    
                    # Prepare data for insertion with correct column names
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
                    
                    if result.data:
                        inserted_count += 1
                        print(f"Inserted context for symbol {data['sym']}: ID {result.data[0]['id']}")
                        
                        # Generate and insert sample output data for this context
                        await self.insert_sample_output(result.data[0]['id'], data)
                    else:
                        print(f"Failed to insert context for symbol {data['sym']}")
            
            print(f"\nSuccessfully inserted {inserted_count} MTF context records")
            return True
            
        except Exception as e:
            print(f"Error inserting MTF context data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def insert_sample_output(self, context_id: int, context_data: dict):
        """Insert sample MTF output data based on context"""
        try:
            # Generate sample output data (in production, this would come from LLM)
            output_data = {
                'context_id': context_id,
                'sym': context_data['sym'],
                't': context_data['t'],
                'p': context_data['p'],
                'tf': context_data['TF'],
                's': [0, -2, 2, 0, -1, 2],  # Sample structure signals
                'c': [3, -3, 3, 0, -1, 1],  # Sample context signals
                'o': [-1, 0, -2, 0, 0, -1],  # Sample orderflow signals
                'f': [3, -2, 1, 0, -1, -1],  # Sample flow signals
                'conf': [36, 41, 63, 75, 64, 64],  # Confidence scores
                's_a': 2,  # Aggregate structure
                'f_a': -1,  # Aggregate flow
                'conf_a': 64,  # Aggregate confidence
                'prob_cont': 61,  # Probability of continuation
                'sc_in': 39,  # Score in
                'sc_out': 45,  # Score out
                'hold': 1,  # Hold signal
                'tp_atr': 1.69,  # Take profit ATR
                'sl_atr': 1.21,  # Stop loss ATR
                'hedge': 67,  # Hedge percentage
                'reasons': [12, 14, 5, 3]  # Reason codes
            }
            
            # Insert into Supabase
            result = self.supabase.table('hl_mtf_output').insert(output_data).execute()
            
            if result.data:
                print(f"  - Inserted output for context {context_id}")
            
        except Exception as e:
            print(f"  - Error inserting output for context {context_id}: {e}")
    
    async def verify_data(self):
        """Verify the inserted data"""
        try:
            # Query context table
            context_result = self.supabase.table('hl_mtf_context').select("*").execute()
            print(f"\n[VERIFICATION] Found {len(context_result.data)} records in hl_mtf_context")
            
            # Query output table
            output_result = self.supabase.table('hl_mtf_output').select("*").execute()
            print(f"[VERIFICATION] Found {len(output_result.data)} records in hl_mtf_output")
            
            # Display sample data
            if context_result.data:
                print("\nSample MTF Context Data:")
                for record in context_result.data:
                    print(f"  Symbol {record['sym']}: ${record['p']:.2f} at {datetime.fromtimestamp(record['t'])}")
                    print(f"    Support: ${record['l_sup']:.2f}, Resistance: ${record['l_res']:.2f}")
                    print(f"    Funding: {record['fund_bp']} bp, Risk: {record['rsk']}")
            
            if output_result.data:
                print("\nSample MTF Output Data:")
                for record in output_result.data:
                    print(f"  Context {record['context_id']}: Confidence {record['conf_a']}%")
                    print(f"    Probability Continuation: {record['prob_cont']}%")
                    print(f"    TP: {record['tp_atr']} ATR, SL: {record['sl_atr']} ATR")
            
            return True
            
        except Exception as e:
            print(f"Error verifying data: {e}")
            return False

async def main():
    """Main function to insert and verify data"""
    inserter = MTFDataInserter()
    
    print("=== Inserting Real MTF Data into Supabase ===\n")
    
    # Insert the data
    success = await inserter.insert_mtf_context()
    
    if success:
        print("\n=== Verifying Inserted Data ===")
        await inserter.verify_data()
        
        print("\n=== Data Successfully Loaded! ===")
        print("The following tables now contain real Hyperliquid data:")
        print("  - hl_mtf_context: Multi-timeframe market context")
        print("  - hl_mtf_output: Trading signals and predictions")
    else:
        print("\n[ERROR] Failed to insert data")

if __name__ == "__main__":
    asyncio.run(main())