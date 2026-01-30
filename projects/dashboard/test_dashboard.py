"""
Test the Hyperliquid Trading Dashboard using Playwright
"""

import asyncio
from playwright.async_api import async_playwright
import time
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_dashboard():
    """Test the trading dashboard functionality"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Testing Hyperliquid Trading Dashboard...")
        print("=" * 60)
        
        # Test 1: Charts Dashboard
        print("\n[TEST 1] Testing Charts Dashboard...")
        try:
            await page.goto("http://localhost:8503", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check if page loaded
            title = await page.title()
            print(f"  [OK] Page loaded: {title}")
            
            # Check for main elements
            if await page.locator("text=HYPE Trading Dashboard").count() > 0:
                print("  [OK] Dashboard header found")
            
            # Check for tabs
            tabs = ["CVD Analysis", "Volume Profile", "Oscillators", "Market Metrics", "All Indicators"]
            for tab in tabs:
                if await page.locator(f"text={tab}").count() > 0:
                    print(f"  [OK] Tab found: {tab}")
            
            # Click on CVD Analysis tab
            await page.click("text=CVD Analysis")
            await page.wait_for_timeout(2000)
            print("  [OK] CVD Analysis tab clicked")
            
            # Take screenshot
            await page.screenshot(path="charts_dashboard_test.png")
            print("  [OK] Screenshot saved: charts_dashboard_test.png")
            
        except Exception as e:
            print(f"  [ERROR] Charts Dashboard Error: {e}")
        
        # Test 2: Simplified Dashboard
        print("\n[TEST 2] Testing Simplified Dashboard...")
        try:
            await page.goto("http://localhost:8502", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check if page loaded
            title = await page.title()
            print(f"  [OK] Page loaded: {title}")
            
            # Check for main elements
            if await page.locator("text=Simplified View").count() > 0:
                print("  [OK] Simplified view header found")
            
            # Check for indicator cards
            indicators = ["CVD", "Volume Spike", "MA Crossover", "RSI", "Bollinger", "MACD"]
            for indicator in indicators:
                if await page.locator(f"text={indicator}").count() > 0:
                    print(f"  [OK] Indicator card found: {indicator}")
            
            # Check for confluence score
            if await page.locator("text=Confluence Score").count() > 0:
                print("  [OK] Confluence score found")
            
            # Take screenshot
            await page.screenshot(path="simplified_dashboard_test.png")
            print("  [OK] Screenshot saved: simplified_dashboard_test.png")
            
        except Exception as e:
            print(f"  [ERROR] Simplified Dashboard Error: {e}")
        
        # Test 3: Check data feed status
        print("\n[TEST 3] Testing Data Feed Status...")
        try:
            # Look for data feed status section
            if await page.locator("text=Data Feed Status").count() > 0:
                print("  [OK] Data feed status section found")
                
                # Check individual feeds
                feeds = ["Indicators", "Market Data", "Account", "Confluence"]
                for feed in feeds:
                    if await page.locator(f"text={feed}").count() > 0:
                        print(f"  [OK] Feed status found: {feed}")
            
        except Exception as e:
            print(f"  [ERROR] Data Feed Status Error: {e}")
        
        print("\n" + "=" * 60)
        print("Dashboard Testing Complete!")
        print("=" * 60)
        
        # Close browser
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_dashboard())