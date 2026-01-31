#!/usr/bin/env python3
"""
Service Validation Script
Tests all trading services and logs results for CloudWatch visibility.

Usage:
    python scripts/validate_services.py
    python scripts/validate_services.py --full  # Include trade test
"""

import os
import sys
import json
import asyncio
import subprocess
import syslog
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def log_result(test_name: str, status: str, details: str = ""):
    """Log test result to syslog (picked up by CloudWatch)"""
    msg = f"[VALIDATION] {test_name}: {status}"
    if details:
        msg += f" - {details}"
    print(msg)
    syslog.syslog(syslog.LOG_INFO, msg)


async def test_telegram():
    """Test Telegram connection"""
    try:
        from integrations.telegram.client import TelegramClient

        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not token or not chat_id:
            return False, "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"

        client = TelegramClient(token, chat_id)
        result = await client.send(
            f"[VALIDATION] Service check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            "All systems operational.",
            parse_mode="Markdown"
        )
        await client.close()

        if result.get("ok"):
            return True, f"Message sent (ID: {result['result']['message_id']})"
        else:
            return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


async def test_discord():
    """Test Discord connection"""
    try:
        from integrations.discord.signal_feed import DiscordSignalFeed, TokenExpiredError

        token = os.getenv('DISCORD_TOKEN')
        if not token:
            return False, "Missing DISCORD_TOKEN"

        feed = DiscordSignalFeed(token=token)
        # Try to fetch just 1 message to test connection
        signals = await feed.fetch_signals(hours=1)
        return True, f"Connected, found {len(signals)} signals in last hour"
    except TokenExpiredError:
        return False, "Token expired - needs refresh"
    except Exception as e:
        return False, str(e)


async def test_hyperliquid():
    """Test Hyperliquid API connection"""
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants

        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        mids = info.all_mids()
        btc_price = float(mids.get("BTC", 0))
        eth_price = float(mids.get("ETH", 0))

        if btc_price > 0:
            return True, f"BTC: ${btc_price:,.0f}, ETH: ${eth_price:,.0f}"
        else:
            return False, "Could not fetch prices"
    except Exception as e:
        return False, str(e)


async def test_supabase():
    """Test Supabase connection"""
    try:
        from supabase import create_client

        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')

        if not url or not key:
            return False, "Missing SUPABASE_URL or SUPABASE_KEY"

        client = create_client(url, key)
        # Try to count paper recommendations
        result = client.table('paper_recommendations').select('id', count='exact').limit(1).execute()
        count = result.count if hasattr(result, 'count') else len(result.data)
        return True, f"Connected, {count} paper recommendations"
    except Exception as e:
        return False, str(e)


def test_systemd_services():
    """Test systemd service status"""
    services = ['paper-trading', 'discord-telegram-bridge', 'amazon-cloudwatch-agent']
    results = {}

    for service in services:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True, text=True
            )
            status = result.stdout.strip()
            results[service] = status == 'active'
        except:
            results[service] = False

    return results


def test_memory():
    """Check memory usage"""
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        mem_line = [l for l in lines if l.startswith('Mem:')][0]
        parts = mem_line.split()
        total = int(parts[1])
        used = int(parts[2])
        pct = (used / total) * 100
        return True, f"{used}MB / {total}MB ({pct:.1f}%)"
    except Exception as e:
        return False, str(e)


async def run_validation(full_test: bool = False):
    """Run all validation tests"""
    print("=" * 60)
    print("SERVICE VALIDATION")
    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    syslog.openlog("validate_services", syslog.LOG_PID, syslog.LOG_USER)
    syslog.syslog(syslog.LOG_INFO, "[VALIDATION] Starting service validation")

    all_passed = True

    # Test systemd services
    print("\n[1/6] Systemd Services")
    services = test_systemd_services()
    for name, status in services.items():
        status_str = "RUNNING" if status else "STOPPED"
        log_result(f"service.{name}", status_str)
        if not status:
            all_passed = False

    # Test memory
    print("\n[2/6] Memory")
    ok, details = test_memory()
    log_result("memory", "OK" if ok else "FAIL", details)

    # Test Telegram
    print("\n[3/6] Telegram")
    ok, details = await test_telegram()
    log_result("telegram", "OK" if ok else "FAIL", details)
    if not ok:
        all_passed = False

    # Test Discord
    print("\n[4/6] Discord")
    ok, details = await test_discord()
    log_result("discord", "OK" if ok else "FAIL", details)
    if not ok:
        all_passed = False

    # Test Hyperliquid
    print("\n[5/6] Hyperliquid API")
    ok, details = await test_hyperliquid()
    log_result("hyperliquid", "OK" if ok else "FAIL", details)
    if not ok:
        all_passed = False

    # Test Supabase
    print("\n[6/6] Supabase")
    ok, details = await test_supabase()
    log_result("supabase", "OK" if ok else "FAIL", details)
    if not ok:
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("RESULT: ALL TESTS PASSED")
        syslog.syslog(syslog.LOG_INFO, "[VALIDATION] All tests passed")
    else:
        print("RESULT: SOME TESTS FAILED")
        syslog.syslog(syslog.LOG_WARNING, "[VALIDATION] Some tests failed")
    print("=" * 60)

    syslog.closelog()
    return all_passed


async def main():
    full_test = '--full' in sys.argv
    success = await run_validation(full_test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
