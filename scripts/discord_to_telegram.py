#!/usr/bin/env python3
"""
Discord to Telegram Signal Bridge (Enhanced)

Monitors Discord signal channels and forwards high-confidence signals
to Telegram with Accept/Decline buttons for manual trade execution.

ENHANCED FEATURES:
- Quick technical analysis before trade confirmation
- Discord message citations with original quote
- Multi-stage message flow with visual indicators
- Report storage for each signal

USAGE:
  python scripts/discord_to_telegram.py                    # Default: 0.6 min confidence
  python scripts/discord_to_telegram.py --min-confidence 0.7
  python scripts/discord_to_telegram.py --poll 30          # Check every 30s
  python scripts/discord_to_telegram.py --dry-run          # Don't execute trades
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Set, Optional, Dict, Any

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from integrations.discord.signal_feed import DiscordSignalFeed, TokenExpiredError
from integrations.discord.signal_parser import TradeSignal, SignalDirection
from integrations.telegram.client import TelegramClient, InlineButton, CallbackHandler
from integrations.telegram.trade_bot import TradeOpportunity
from integrations.telegram.quick_analyzer import QuickAnalyzer, QuickAnalysisResult
from integrations.telegram.message_formatter import MessageFormatter
from scripts.safe_trade_executor import SafeTradeExecutor, KeyLevelCalculator


class DiscordTelegramBridge:
    """
    Enhanced Discord to Telegram Signal Bridge.

    Flow:
    1. Monitor Discord channels for trade signals
    2. Filter by confidence threshold
    3. Run quick technical analysis
    4. Send multi-stage message to Telegram
    5. Save signal report to disk
    6. On Accept: Execute trade on Hyperliquid
    7. On Decline: Log and dismiss
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        dry_run: bool = False,
        poll_interval: int = 60
    ):
        self.min_confidence = min_confidence
        self.dry_run = dry_run
        self.poll_interval = poll_interval

        # Track sent signals to avoid duplicates
        self._sent_signals: Set[str] = set()
        self._sent_file = "sent_signals.json"
        self._load_sent()

        # Discord feed
        self.discord = DiscordSignalFeed()

        # Telegram client
        self.telegram = TelegramClient(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID')
        )
        self.handler = CallbackHandler(self.telegram)

        # Quick analyzer for technical analysis
        self.analyzer = QuickAnalyzer()

        # Message formatter
        self.formatter = MessageFormatter()

        # Pending opportunities (message_id -> data)
        self._pending: dict = {}

        # Register callbacks
        self.handler.register("accept_", self._handle_accept)
        self.handler.register("decline_", self._handle_decline)

        # Output directory for reports
        self.output_dir = Path("outputs/discord_signals")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_sent(self):
        """Load previously sent signal IDs"""
        try:
            if os.path.exists(self._sent_file):
                with open(self._sent_file, 'r') as f:
                    self._sent_signals = set(json.load(f))
        except Exception:
            pass

    def _save_sent(self):
        """Save sent signal IDs"""
        try:
            with open(self._sent_file, 'w') as f:
                json.dump(list(self._sent_signals)[-1000:], f)  # Keep last 1000
        except Exception:
            pass

    def _signal_to_opportunity(self, signal: TradeSignal) -> TradeOpportunity:
        """Convert Discord TradeSignal to Telegram TradeOpportunity"""
        # Generate unique ID
        opp_id = f"discord_{signal.ticker}_{signal.message_id}"

        # Get direction string
        direction = "LONG" if signal.direction == SignalDirection.LONG else "SHORT"

        # Use signal's entry price or mark as "market"
        entry = signal.entry_price or 0

        # Use signal's stop loss or calculate a default
        stop_loss = signal.stop_loss or 0

        # Take profits
        take_profits = signal.take_profit if signal.take_profit else []

        return TradeOpportunity(
            id=opp_id,
            ticker=signal.ticker,
            direction=direction,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profits,
            leverage=int(signal.leverage or 5),
            confidence=signal.confidence,
            source=f"Discord: {signal.source_channel}",
            notes=f"Author: {signal.author}"
        )

    def _save_signal_report(
        self,
        signal: TradeSignal,
        analysis: Optional[QuickAnalysisResult],
        report_dir: Path
    ) -> None:
        """Save signal data and analysis to disk"""
        report_dir.mkdir(parents=True, exist_ok=True)

        # Save raw signal data
        signal_data = {
            "ticker": signal.ticker,
            "direction": signal.direction.value,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "leverage": signal.leverage,
            "confidence": signal.confidence,
            "source_channel": signal.source_channel,
            "author": signal.author,
            "timestamp": signal.timestamp.isoformat(),
            "message_id": signal.message_id,
            "raw_content": signal.raw_content,
        }
        with open(report_dir / "signal.json", 'w') as f:
            json.dump(signal_data, f, indent=2)

        # Save analysis report
        analysis_md = f"""# Signal Analysis: {signal.ticker}
## Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Discord Signal

**Channel**: #{signal.source_channel}
**Author**: @{signal.author}
**Timestamp**: {signal.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

> {signal.raw_content}

---

## Parsed Signal

- **Ticker**: {signal.ticker}
- **Direction**: {signal.direction.value}
- **Entry**: ${signal.entry_price:,.2f} if signal.entry_price else "Market"
- **Stop Loss**: ${signal.stop_loss:,.2f} if signal.stop_loss else "Not set"
- **Take Profit**: {", ".join([f"${tp:,.2f}" for tp in signal.take_profit]) if signal.take_profit else "Not set"}
- **Leverage**: {signal.leverage or 5}x
- **Confidence**: {signal.confidence * 100:.0f}%

---

## Quick Technical Analysis

"""
        if analysis:
            analysis_md += f"""
- **Current Price**: ${analysis.current_price:,.2f}
- **RSI (1h)**: {analysis.rsi:.1f if analysis.rsi else "N/A"} ({analysis.rsi_signal})
- **EMA 20**: ${analysis.ema20:,.2f}
- **EMA 50**: ${analysis.ema50:,.2f}
- **Trend**: {analysis.trend_signal}
- **Support**: ${analysis.nearest_support:,.2f if analysis.nearest_support else "N/A"}
- **Resistance**: ${analysis.nearest_resistance:,.2f if analysis.nearest_resistance else "N/A"}
- **Bias Score**: {analysis.bias_score}/5 - {analysis.bias_label}
"""
        else:
            analysis_md += "\n*Analysis not available*\n"

        with open(report_dir / "analysis.md", 'w', encoding='utf-8') as f:
            f.write(analysis_md)

    def _save_execution_report(
        self,
        report_dir: Path,
        success: bool,
        fill_price: Optional[float],
        size: Optional[float],
        error: Optional[str] = None
    ) -> None:
        """Save trade execution details"""
        execution_data = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "fill_price": fill_price,
            "size": size,
            "error": error,
            "dry_run": self.dry_run,
        }
        with open(report_dir / "execution.json", 'w') as f:
            json.dump(execution_data, f, indent=2)

    async def _send_to_telegram(self, signal: TradeSignal):
        """Send a signal to Telegram with multi-stage flow"""
        # Check if already sent
        signal_key = f"{signal.ticker}_{signal.message_id}"
        if signal_key in self._sent_signals:
            return

        # Create report directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"{signal.ticker}_{timestamp}"
        report_path = str(report_dir.relative_to(Path.cwd())) + "/"

        # Convert to opportunity
        opp = self._signal_to_opportunity(signal)
        direction = opp.direction

        # Stage 1: Send initial "analyzing" message
        stage1_msg = self.formatter.format_signal_received(
            ticker=opp.ticker,
            direction=direction,
            confidence=opp.confidence,
            discord_content=signal.raw_content,
            discord_author=signal.author,
            discord_channel=signal.source_channel,
            discord_timestamp=signal.timestamp,
        )

        result = await self.telegram.send(stage1_msg, parse_mode="HTML")

        if not result.get("ok"):
            print(f"[ERROR] Failed to send Stage 1: {result}")
            return

        msg_id = result["result"]["message_id"]
        print(f"[TELEGRAM] Stage 1 sent for {opp.ticker} {direction}")

        # Run quick analysis
        print(f"[ANALYSIS] Running quick analysis for {opp.ticker}...")
        analysis = self.analyzer.analyze(opp.ticker, timeframe='1h')

        # Get current price for entry if not specified
        if not opp.entry_price and analysis:
            opp.entry_price = analysis.current_price

        # Save signal report
        self._save_signal_report(signal, analysis, report_dir)

        # Stage 2: Update with analysis and buttons
        if analysis:
            stage2_msg = self.formatter.format_analysis_complete(
                ticker=opp.ticker,
                direction=direction,
                confidence=opp.confidence,
                entry_price=opp.entry_price,
                stop_loss=opp.stop_loss,
                take_profits=opp.take_profit,
                leverage=opp.leverage,
                rsi=analysis.rsi,
                rsi_signal=analysis.rsi_signal,
                trend_signal=analysis.trend_signal,
                ema20=analysis.ema20,
                ema50=analysis.ema50,
                nearest_support=analysis.nearest_support,
                nearest_resistance=analysis.nearest_resistance,
                bias_score=analysis.bias_score,
                bias_label=analysis.bias_label,
                discord_content=signal.raw_content,
                discord_author=signal.author,
                discord_channel=signal.source_channel,
                discord_timestamp=signal.timestamp,
                report_path=report_path,
            )
        else:
            # Fallback if analysis fails
            stage2_msg = self.formatter.format_analysis_complete(
                ticker=opp.ticker,
                direction=direction,
                confidence=opp.confidence,
                entry_price=opp.entry_price,
                stop_loss=opp.stop_loss,
                take_profits=opp.take_profit,
                leverage=opp.leverage,
                rsi=None,
                rsi_signal='neutral',
                trend_signal='neutral',
                ema20=opp.entry_price or 0,
                ema50=opp.entry_price or 0,
                nearest_support=None,
                nearest_resistance=None,
                bias_score=3,
                bias_label='Neutral',
                discord_content=signal.raw_content,
                discord_author=signal.author,
                discord_channel=signal.source_channel,
                discord_timestamp=signal.timestamp,
                report_path=report_path,
            )

        # Create buttons
        buttons = [[
            InlineButton("ACCEPT TRADE", f"accept_{opp.id}"),
            InlineButton("Decline", f"decline_{opp.id}")
        ]]

        await self.telegram.edit_message(
            msg_id,
            stage2_msg,
            parse_mode="HTML",
            buttons=buttons
        )

        # Store pending data
        self._pending[opp.id] = {
            "opportunity": opp,
            "signal": signal,
            "message_id": msg_id,
            "analysis": analysis,
            "report_dir": report_dir,
            "report_path": report_path,
        }
        self._sent_signals.add(signal_key)
        self._save_sent()

        print(f"[TELEGRAM] Stage 2 sent for {opp.ticker} {direction} (conf: {opp.confidence:.2f})")

    async def _handle_accept(self, callback_data: str, callback_query: dict) -> str:
        """Handle Accept button press"""
        opp_id = callback_data.replace("accept_", "")
        pending = self._pending.get(opp_id)

        if not pending:
            return "Signal expired"

        opp = pending["opportunity"]
        signal = pending["signal"]
        msg_id = pending["message_id"]
        analysis = pending["analysis"]
        report_dir = pending["report_dir"]
        report_path = pending["report_path"]

        print(f"[ACCEPTED] {opp.ticker} {opp.direction}")

        # Execute trade
        if self.dry_run:
            # Dry run - just show simulated execution
            entry_price = opp.entry_price or (analysis.current_price if analysis else 0)
            size = 0.001  # Simulated size

            stage3_msg = self.formatter.format_dry_run_executed(
                ticker=opp.ticker,
                direction=opp.direction,
                entry_price=entry_price,
                size=size,
                stop_loss=opp.stop_loss,
                take_profit=opp.take_profit[0] if opp.take_profit else None,
                report_path=report_path,
            )

            self._save_execution_report(report_dir, True, entry_price, size)

        else:
            # Real execution
            result = await self._execute_trade(opp, analysis)

            if result["success"]:
                stage3_msg = self.formatter.format_trade_executed(
                    ticker=opp.ticker,
                    direction=opp.direction,
                    fill_price=result["fill_price"],
                    size=result["size"],
                    notional=result["notional"],
                    stop_loss=opp.stop_loss,
                    take_profit=opp.take_profit[0] if opp.take_profit else None,
                    risk_amount=result.get("risk_amount", 0),
                    risk_pct=result.get("risk_pct", 0),
                    report_path=report_path,
                )
                self._save_execution_report(
                    report_dir, True, result["fill_price"], result["size"]
                )
            else:
                stage3_msg = self.formatter.format_trade_error(
                    ticker=opp.ticker,
                    direction=opp.direction,
                    error_message=result["error"],
                )
                self._save_execution_report(
                    report_dir, False, None, None, result["error"]
                )

        # Update message (remove buttons)
        await self.telegram.edit_message(msg_id, stage3_msg, parse_mode="HTML")

        # Clean up
        del self._pending[opp_id]

        return "Trade accepted!"

    async def _handle_decline(self, callback_data: str, callback_query: dict) -> str:
        """Handle Decline button press"""
        opp_id = callback_data.replace("decline_", "")
        pending = self._pending.get(opp_id)

        if not pending:
            return "Signal expired"

        opp = pending["opportunity"]
        signal = pending["signal"]
        msg_id = pending["message_id"]
        report_dir = pending["report_dir"]

        print(f"[DECLINED] {opp.ticker} {opp.direction}")

        # Update message
        declined_msg = self.formatter.format_trade_declined(
            ticker=opp.ticker,
            direction=opp.direction,
            discord_content=signal.raw_content,
            discord_author=signal.author,
        )

        await self.telegram.edit_message(msg_id, declined_msg, parse_mode="HTML")

        # Save decline to execution report
        self._save_execution_report(report_dir, False, None, None, "Declined by user")

        # Clean up
        del self._pending[opp_id]

        return "Trade declined"

    async def _execute_trade(
        self,
        opp: TradeOpportunity,
        analysis: Optional[QuickAnalysisResult]
    ) -> Dict[str, Any]:
        """
        Execute trade using SafeTradeExecutor.

        MANDATORY: All trades must have stop losses based on key technical levels.
        """
        try:
            # Use SafeTradeExecutor for mandatory stop loss handling
            executor = SafeTradeExecutor()

            # Get minimum size for the asset
            meta = executor.info.meta()
            sz_decimals = 0
            for asset in meta['universe']:
                if asset['name'] == opp.ticker:
                    sz_decimals = asset.get('szDecimals', 0)
                    break

            # Calculate position size based on risk
            current_price = executor.level_calc.get_current_price(opp.ticker)
            if current_price == 0:
                return {"success": False, "error": f"Could not get price for {opp.ticker}"}

            # Get key-level based stop
            stop_level = executor.level_calc.calculate_stop_loss(
                opp.ticker,
                opp.direction,
                current_price
            )

            # Use signal's stop if provided and valid, otherwise use key-level stop
            if opp.stop_loss and opp.stop_loss > 0:
                # Validate signal's stop is on correct side
                if opp.direction == "SHORT" and opp.stop_loss > current_price:
                    stop_price = opp.stop_loss
                    stop_method = "signal"
                elif opp.direction == "LONG" and opp.stop_loss < current_price:
                    stop_price = opp.stop_loss
                    stop_method = "signal"
                else:
                    # Signal's stop is invalid, use key-level stop
                    stop_price = stop_level.price
                    stop_method = stop_level.method
            else:
                # No signal stop, use key-level stop
                stop_price = stop_level.price
                stop_method = stop_level.method

            # Calculate size based on risk (1.5% of estimated $100 account for small accounts)
            risk_pct = 0.015
            account_estimate = 100  # Will be replaced with actual equity
            try:
                user_state = executor.info.user_state(executor.account)
                account_value = float(user_state.get('marginSummary', {}).get('accountValue', 100))
                account_estimate = account_value
            except:
                pass

            risk_amount = account_estimate * risk_pct
            stop_distance = abs(current_price - stop_price)

            if stop_distance > 0:
                size = risk_amount / stop_distance
            else:
                size = 0.01

            # Round to valid size
            if sz_decimals == 0:
                size = max(1, round(size))
                # Ensure minimum notional (~$10)
                min_size = max(1, int(10 / current_price) + 1)
                size = max(size, min_size)
            else:
                size = round(size, sz_decimals)

            # Execute with SafeTradeExecutor
            if opp.direction == "SHORT":
                result = executor.market_short(
                    opp.ticker,
                    size,
                    leverage=opp.leverage,
                    stop_price=stop_price,
                    take_profit=opp.take_profit[0] if opp.take_profit else None
                )
            else:
                result = executor.market_long(
                    opp.ticker,
                    size,
                    leverage=opp.leverage,
                    stop_price=stop_price,
                    take_profit=opp.take_profit[0] if opp.take_profit else None
                )

            if result.success:
                notional = result.size * result.entry_price
                actual_risk = abs(result.entry_price - result.stop_loss) * result.size
                risk_pct = (actual_risk / account_estimate) * 100

                return {
                    "success": True,
                    "fill_price": result.entry_price,
                    "size": result.size,
                    "notional": notional,
                    "risk_amount": actual_risk,
                    "risk_pct": risk_pct,
                    "stop_loss": result.stop_loss,
                    "stop_method": result.stop_method,
                }
            else:
                return {"success": False, "error": result.error or "Trade execution failed"}

        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    async def _process_new_signals(self):
        """Fetch and process new signals"""
        try:
            # Fetch recent signals
            signals = await self.discord.fetch_signals(hours=1)

            # Filter by confidence
            high_conf = [
                s for s in signals
                if s.confidence >= self.min_confidence
                and s.direction != SignalDirection.NEUTRAL
                and s.ticker  # Must have ticker
            ]

            # Send to Telegram
            for signal in high_conf:
                await self._send_to_telegram(signal)
                await asyncio.sleep(1)  # Rate limit between signals

        except TokenExpiredError:
            print("[ERROR] Discord token expired - run discord_auth.py")
        except Exception as e:
            print(f"[ERROR] Processing signals: {e}")

    async def _poll_callbacks(self):
        """Poll for Telegram button presses"""
        last_update_id = 0

        while True:
            try:
                updates = await self.telegram.get_updates(
                    offset=last_update_id + 1 if last_update_id else None,
                    timeout=5
                )

                if updates.get("ok"):
                    for update in updates.get("result", []):
                        last_update_id = update["update_id"]

                        if "callback_query" in update:
                            cq = update["callback_query"]
                            callback_data = cq["data"]

                            # Find handler
                            response = None
                            if callback_data.startswith("accept_"):
                                response = await self._handle_accept(callback_data, cq)
                            elif callback_data.startswith("decline_"):
                                response = await self._handle_decline(callback_data, cq)

                            # Answer callback
                            if response:
                                await self.telegram.answer_callback_query(
                                    cq["id"],
                                    response,
                                    show_alert=True
                                )

            except Exception as e:
                print(f"[ERROR] Polling callbacks: {e}")

            await asyncio.sleep(1)

    async def run(self):
        """Run the bridge"""
        print("=" * 60)
        print("DISCORD -> TELEGRAM SIGNAL BRIDGE (Enhanced)")
        print("=" * 60)
        print(f"Min Confidence: {self.min_confidence}")
        print(f"Poll Interval: {self.poll_interval}s")
        print(f"Dry Run: {self.dry_run}")
        print(f"Reports: {self.output_dir.absolute()}")
        print("=" * 60)
        print("\nStarting bridge... Press Ctrl+C to stop\n")

        # Start callback poller in background
        callback_task = asyncio.create_task(self._poll_callbacks())

        try:
            while True:
                await self._process_new_signals()
                await asyncio.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\nStopping bridge...")
            callback_task.cancel()
        finally:
            await self.telegram.close()


async def main():
    parser = argparse.ArgumentParser(description="Discord to Telegram Signal Bridge (Enhanced)")
    parser.add_argument('--min-confidence', type=float, default=0.6,
                       help='Minimum confidence threshold (0-1)')
    parser.add_argument('--poll', type=int, default=60,
                       help='Poll interval in seconds')
    parser.add_argument('--dry-run', action='store_true',
                       help='Do not execute real trades')

    args = parser.parse_args()

    # Check required env vars
    missing = []
    if not os.getenv('DISCORD_TOKEN'):
        missing.append('DISCORD_TOKEN')
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        missing.append('TELEGRAM_BOT_TOKEN')
    if not os.getenv('TELEGRAM_CHAT_ID'):
        missing.append('TELEGRAM_CHAT_ID')

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("\nSet them in your .env file")
        sys.exit(1)

    bridge = DiscordTelegramBridge(
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
        poll_interval=args.poll
    )

    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
