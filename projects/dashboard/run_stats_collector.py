"""
HyperLiquid Stats Collector
Continuously fetches and stores stats data from stats.hyperliquid.xyz
"""

import asyncio
import sys
import os
from datetime import datetime
import signal

sys.path.append(os.path.dirname(__file__))

from hyperliquid_stats_api import HyperLiquidStatsAPI


class StatsCollector:
    """Stats collection service"""
    
    def __init__(self):
        self.stats_api = HyperLiquidStatsAPI()
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[INFO] Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def run(self):
        """Main collection loop"""
        print("="*70)
        print("HYPERLIQUID STATS COLLECTOR")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Collecting stats every 5 minutes...")
        print("Press Ctrl+C to stop")
        print("="*70)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        async with self.stats_api as api:
            while self.running:
                try:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching stats...")
                    
                    # Fetch all data types in parallel
                    tasks = [
                        api.get_funding_rates(),
                        api.get_volume_comparison(),
                        api.get_tvl_metrics(),
                        api.get_leaderboard('24h'),
                        api.get_liquidations(1)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    funding, volume, tvl, leaderboard, liquidations = results
                    
                    # Log results
                    stats_summary = []
                    
                    if funding and not isinstance(funding, Exception):
                        await api.save_to_supabase('funding', funding)
                        stats_summary.append(f"Funding: {len(funding)} symbols")
                    
                    if volume and not isinstance(volume, Exception):
                        await api.save_to_supabase('volume', volume)
                        stats_summary.append(f"Volume: {len(volume)} pairs")
                    
                    if tvl and not isinstance(tvl, Exception):
                        await api.save_to_supabase('tvl', tvl)
                        stats_summary.append(f"TVL: ${tvl.total_tvl:,.0f}")
                    
                    if leaderboard and not isinstance(leaderboard, Exception):
                        await api.save_to_supabase('leaderboard', leaderboard)
                        stats_summary.append(f"Traders: {len(leaderboard)}")
                    
                    if liquidations and not isinstance(liquidations, Exception):
                        await api.save_to_supabase('liquidations', liquidations)
                        stats_summary.append(f"Liquidations: {len(liquidations)}")
                    
                    print(f"[SUCCESS] {' | '.join(stats_summary)}")
                    
                    # Wait for next cycle
                    for i in range(300):  # 5 minutes = 300 seconds
                        if not self.running:
                            break
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"[ERROR] Collection cycle failed: {e}")
                    await asyncio.sleep(60)  # Retry after 1 minute on error
        
        print("\n[INFO] Stats collector stopped")


async def main():
    """Main entry point"""
    collector = StatsCollector()
    await collector.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Stats collector interrupted by user")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        sys.exit(1)