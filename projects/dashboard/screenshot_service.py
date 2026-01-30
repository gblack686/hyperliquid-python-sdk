"""
Kiyotaka Chart Screenshot Service
Captures screenshots of Kiyotaka charts using Playwright
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KiyotakaScreenshotService:
    def __init__(self):
        self.username = os.getenv('KIYOTAKA_USERNAME')
        self.password = os.getenv('KIYOTAKA_PASSWORD')
        self.screenshot_dir = Path('/app/screenshots')
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def initialize(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.page = await self.browser.new_page()
        logger.info("Browser initialized")
        
    async def login(self):
        """Login to Kiyotaka platform"""
        if not self.username or not self.password:
            raise ValueError("KIYOTAKA_USERNAME and KIYOTAKA_PASSWORD must be set in .env")
            
        logger.info("Logging in to Kiyotaka...")
        await self.page.goto('https://chart.kiyotaka.ai/auth/login')
        await self.page.wait_for_selector('input[type="email"]', timeout=10000)
        
        # Fill in credentials
        await self.page.fill('input[type="email"]', self.username)
        await self.page.fill('input[type="password"]', self.password)
        
        # Click sign in button
        await self.page.click('button:has-text("Sign In")')
        
        # Wait for navigation to complete
        await self.page.wait_for_url('https://chart.kiyotaka.ai/**', timeout=15000)
        logger.info("Successfully logged in")
        
    async def capture_chart(self, 
                          chart_id: Optional[str] = None, 
                          symbol: str = "HYPEUSDT",
                          exchange: str = "BINANCE.F",
                          timeframe: str = "1h") -> str:
        """
        Capture screenshot of a specific chart
        
        Args:
            chart_id: Specific chart ID to navigate to
            symbol: Trading symbol (default: HYPEUSDT)
            exchange: Exchange name (default: BINANCE.F)
            timeframe: Chart timeframe (default: 1h)
            
        Returns:
            Path to saved screenshot
        """
        try:
            # Navigate to chart
            if chart_id:
                url = f'https://chart.kiyotaka.ai/{chart_id}'
            else:
                url = f'https://chart.kiyotaka.ai/'
                
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for chart to load
            await self.page.wait_for_selector('.chart-container, canvas', timeout=15000)
            await asyncio.sleep(2)  # Give charts time to render
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'kiyotaka_{symbol}_{timeframe}_{timestamp}.png'
            filepath = self.screenshot_dir / filename
            
            # Take screenshot
            await self.page.screenshot(
                path=str(filepath),
                full_page=True
            )
            
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            raise
            
    async def capture_multiple_charts(self, charts: list) -> list:
        """
        Capture multiple chart screenshots
        
        Args:
            charts: List of chart configurations
                   [{"chart_id": "xxx", "symbol": "BTCUSDT", "timeframe": "1h"}, ...]
                   
        Returns:
            List of screenshot paths
        """
        screenshots = []
        for chart_config in charts:
            try:
                path = await self.capture_chart(**chart_config)
                screenshots.append(path)
            except Exception as e:
                logger.error(f"Failed to capture chart {chart_config}: {e}")
                
        return screenshots
        
    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser cleanup completed")
        
    async def run_screenshot_job(self, chart_configs: list = None):
        """
        Run a complete screenshot job
        
        Args:
            chart_configs: List of chart configurations to capture
        """
        try:
            await self.initialize()
            await self.login()
            
            if not chart_configs:
                # Default configuration
                chart_configs = [
                    {"symbol": "HYPEUSDT", "exchange": "BINANCE.F", "timeframe": "1h"},
                    {"symbol": "BTCUSDT", "exchange": "BINANCE.F", "timeframe": "4h"},
                ]
                
            screenshots = await self.capture_multiple_charts(chart_configs)
            logger.info(f"Captured {len(screenshots)} screenshots")
            return screenshots
            
        finally:
            await self.cleanup()


async def main():
    """Test the screenshot service"""
    service = KiyotakaScreenshotService()
    
    # Example: Capture specific chart
    charts = [
        {"chart_id": "YFvw7cHN"},  # Your specific chart
        {"symbol": "HYPEUSDT", "timeframe": "1m"},
        {"symbol": "HYPEUSDT", "timeframe": "1h"},
    ]
    
    screenshots = await service.run_screenshot_job(charts)
    print(f"Screenshots saved: {screenshots}")


if __name__ == "__main__":
    asyncio.run(main())