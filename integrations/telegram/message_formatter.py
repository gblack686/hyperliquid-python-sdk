"""
Telegram Message Formatter

Windows-safe message templates with ASCII symbols for trade confirmations.
Handles multi-stage message flow with consistent formatting.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


# Windows-safe ASCII symbols (avoid emoji encoding issues)
SYMBOLS = {
    'bull': '[+]',      # Bullish indicator
    'bear': '[-]',      # Bearish indicator
    'neutral': '[=]',   # Neutral indicator
    'check': '[OK]',    # Success
    'cross': '[X]',     # Failed
    'signal': '>>',     # Signal marker
    'warning': '[!]',   # Warning
    'arrow': '->',      # Arrow
    'divider': '-' * 30,  # Section divider
}


def get_direction_symbol(direction: str) -> str:
    """Get symbol for trade direction"""
    direction = direction.upper()
    if direction in ['LONG', 'BUY']:
        return SYMBOLS['bull']
    elif direction in ['SHORT', 'SELL']:
        return SYMBOLS['bear']
    return SYMBOLS['neutral']


def get_bias_symbol(bias_score: int) -> str:
    """Get symbol for bias score (1-5)"""
    if bias_score >= 4:
        return SYMBOLS['bull']
    elif bias_score <= 2:
        return SYMBOLS['bear']
    return SYMBOLS['neutral']


def format_price(price: Optional[float], prefix: str = "$") -> str:
    """Format price with commas and 2 decimal places"""
    if price is None or price == 0:
        return "N/A"
    return f"{prefix}{price:,.2f}"


def format_time_ago(dt: Optional[datetime]) -> str:
    """Format datetime as relative time (e.g., '2h ago', '15m ago')"""
    if dt is None:
        return "N/A"

    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt

    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        return "just now"
    elif total_seconds < 60:
        return f"{total_seconds}s ago"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m ago"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h ago"
    else:
        days = total_seconds // 86400
        return f"{days}d ago"


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """Format as percentage"""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


class MessageFormatter:
    """
    Format Telegram messages for trade signal flow.

    Supports three message stages:
    1. Signal Received - Initial notification
    2. Analysis Complete - With Accept/Decline buttons
    3. Trade Executed - Final confirmation
    """

    @staticmethod
    def format_signal_received(
        ticker: str,
        direction: str,
        confidence: float,
        discord_content: str,
        discord_author: str,
        discord_channel: str,
        discord_timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Stage 1: Signal Received notification.

        Shows basic signal info while analysis is running.
        """
        dir_symbol = get_direction_symbol(direction)
        conf_pct = int(confidence * 100)

        # Truncate Discord content if too long
        if len(discord_content) > 200:
            discord_content = discord_content[:197] + "..."

        # Time ago
        time_ago = format_time_ago(discord_timestamp) if discord_timestamp else ""
        time_suffix = f" | {time_ago}" if time_ago and time_ago != "N/A" else ""

        msg = f"""<b>{SYMBOLS['signal']} DISCORD SIGNAL</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()} | {conf_pct}% Confidence

{SYMBOLS['divider']}
<b>DISCORD SOURCE</b>
{SYMBOLS['divider']}
<i>"{discord_content}"</i>
- @{discord_author} in #{discord_channel}{time_suffix}

<i>Analyzing...</i>"""

        return msg

    @staticmethod
    def format_analysis_complete(
        ticker: str,
        direction: str,
        confidence: float,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        take_profits: List[float],
        leverage: int,
        rsi: Optional[float],
        rsi_signal: str,
        trend_signal: str,
        ema20: float,
        ema50: float,
        nearest_support: Optional[float],
        nearest_resistance: Optional[float],
        bias_score: int,
        bias_label: str,
        discord_content: str,
        discord_author: str,
        discord_channel: str,
        discord_timestamp: Optional[datetime],
        report_path: str,
    ) -> str:
        """
        Stage 2: Analysis Complete with full trade setup.

        Includes quick analysis results and Accept/Decline prompt.
        """
        dir_symbol = get_direction_symbol(direction)
        conf_pct = int(confidence * 100)

        # Calculate R:R if possible
        rr_str = "N/A"
        if entry_price and stop_loss and take_profits:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profits[0] - entry_price)
            if risk > 0:
                rr_str = f"{reward/risk:.1f}:1"

        # Stop loss percentage
        sl_pct = ""
        if entry_price and stop_loss:
            pct = abs(entry_price - stop_loss) / entry_price * 100
            sl_pct = f" ({pct:.1f}%)"

        # Format entry
        entry_str = format_price(entry_price) if entry_price else "Market"

        # Format stop loss
        sl_str = format_price(stop_loss) if stop_loss else "Not set"

        # Format take profits
        if take_profits:
            tp_str = ", ".join([format_price(tp) for tp in take_profits[:3]])
        else:
            tp_str = "Not specified"

        # RSI formatting
        rsi_sym = get_direction_symbol('long' if rsi_signal == 'bull' else 'short' if rsi_signal == 'bear' else 'neutral')
        rsi_zone = "Oversold territory" if rsi and rsi < 30 else "Overbought territory" if rsi and rsi > 70 else "Neutral zone"

        # Trend formatting (escape < and > for HTML)
        trend_sym = get_direction_symbol('long' if trend_signal == 'bull' else 'short' if trend_signal == 'bear' else 'neutral')
        trend_desc = "Bullish (EMA20 &gt; EMA50)" if trend_signal == 'bull' else "Bearish (EMA20 &lt; EMA50)" if trend_signal == 'bear' else "Neutral"

        # Bias formatting
        bias_sym = get_bias_symbol(bias_score)

        # Truncate Discord content
        if len(discord_content) > 150:
            discord_content = discord_content[:147] + "..."

        # Discord timestamp - show both relative and absolute
        time_ago = format_time_ago(discord_timestamp)
        ts_str = discord_timestamp.strftime("%H:%M UTC") if discord_timestamp else "N/A"

        msg = f"""<b>{SYMBOLS['signal']} SIGNAL READY</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()} | {conf_pct}% Confidence

{SYMBOLS['divider']}
<b>TRADE SETUP</b>
{SYMBOLS['divider']}
Entry:      {entry_str}
Stop Loss:  {sl_str}{sl_pct}
Target:     {tp_str}
R:R:        {rr_str} | Leverage: {leverage}x

{SYMBOLS['divider']}
<b>QUICK ANALYSIS</b>
{SYMBOLS['divider']}
RSI (1h):   {f"{rsi:.1f}" if rsi else "N/A"} {rsi_sym} {rsi_zone}
Trend:      {trend_sym} {trend_desc}
Support:    {format_price(nearest_support)}
Resistance: {format_price(nearest_resistance)}
Bias:       {bias_score}/5 {bias_sym} {bias_label}

{SYMBOLS['divider']}
<b>DISCORD QUOTE</b>
{SYMBOLS['divider']}
<i>"{discord_content}"</i>
- @{discord_author} | #{discord_channel} | {time_ago}

Report: {report_path}

<i>Press Accept to execute or Decline to skip</i>"""

        return msg

    @staticmethod
    def format_trade_executed(
        ticker: str,
        direction: str,
        fill_price: float,
        size: float,
        notional: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        risk_amount: float,
        risk_pct: float,
        report_path: str,
    ) -> str:
        """
        Stage 3: Trade Executed confirmation.

        Shows execution details and position info.
        """
        dir_symbol = get_direction_symbol(direction)

        # Format SL/TP status
        sl_str = f"Set @ {format_price(stop_loss)}" if stop_loss else "Not set"
        tp_str = f"Set @ {format_price(take_profit)}" if take_profit else "Not set"

        msg = f"""<b>{SYMBOLS['check']} TRADE EXECUTED</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()}

{SYMBOLS['divider']}
<b>EXECUTION</b>
{SYMBOLS['divider']}
Fill:   {format_price(fill_price)}
Size:   {size:.4f} {ticker} ({format_price(notional)})
SL:     {sl_str}
TP:     {tp_str}

{SYMBOLS['divider']}
<b>POSITION</b>
{SYMBOLS['divider']}
Risk:   {format_price(risk_amount)} ({risk_pct:.1f}% equity)

Report: {report_path}"""

        return msg

    @staticmethod
    def format_trade_declined(
        ticker: str,
        direction: str,
        discord_content: str,
        discord_author: str,
    ) -> str:
        """Format message when trade is declined"""
        dir_symbol = get_direction_symbol(direction)

        # Truncate content
        if len(discord_content) > 100:
            discord_content = discord_content[:97] + "..."

        msg = f"""<b>{SYMBOLS['cross']} TRADE DECLINED</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()}

<i>"{discord_content}"</i>
- @{discord_author}

<i>Signal dismissed</i>"""

        return msg

    @staticmethod
    def format_trade_error(
        ticker: str,
        direction: str,
        error_message: str,
    ) -> str:
        """Format message when trade execution fails"""
        dir_symbol = get_direction_symbol(direction)

        msg = f"""<b>{SYMBOLS['warning']} TRADE FAILED</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()}

Error: {error_message[:200]}

<i>Check logs for details</i>"""

        return msg

    @staticmethod
    def format_dry_run_executed(
        ticker: str,
        direction: str,
        entry_price: float,
        size: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        report_path: str,
    ) -> str:
        """Format message for dry run execution"""
        dir_symbol = get_direction_symbol(direction)

        sl_str = format_price(stop_loss) if stop_loss else "Not set"
        tp_str = format_price(take_profit) if take_profit else "Not set"

        msg = f"""<b>{SYMBOLS['check']} DRY RUN EXECUTED</b>

<b>{ticker}</b> {dir_symbol} {direction.upper()}

{SYMBOLS['divider']}
<b>SIMULATED EXECUTION</b>
{SYMBOLS['divider']}
Entry:  {format_price(entry_price)}
Size:   {size:.4f} {ticker}
SL:     {sl_str}
TP:     {tp_str}

<i>No real trade placed (dry run mode)</i>

Report: {report_path}"""

        return msg


# For testing
if __name__ == "__main__":
    from datetime import timedelta

    formatter = MessageFormatter()

    # Simulate a message from 25 minutes ago
    test_timestamp = datetime.now() - timedelta(minutes=25)

    # Test Stage 1
    print("=== Stage 1: Signal Received ===")
    msg1 = formatter.format_signal_received(
        ticker="BTC",
        direction="SHORT",
        confidence=0.55,
        discord_content="BTC short here, SL 82718",
        discord_author="sea-scalper-farouk",
        discord_channel="sea-scalper-farouk",
        discord_timestamp=test_timestamp,
    )
    print(msg1)

    print("\n\n=== Stage 2: Analysis Complete ===")
    msg2 = formatter.format_analysis_complete(
        ticker="BTC",
        direction="SHORT",
        confidence=0.55,
        entry_price=78100.0,
        stop_loss=82718.0,
        take_profits=[75000.0, 72000.0],
        leverage=5,
        rsi=42.5,
        rsi_signal='bear',
        trend_signal='bear',
        ema20=79000.0,
        ema50=80000.0,
        nearest_support=75200.0,
        nearest_resistance=80500.0,
        bias_score=2,
        bias_label='Bearish',
        discord_content="BTC short here, SL 82718",
        discord_author="sea-scalper-farouk",
        discord_channel="sea-scalper-farouk",
        discord_timestamp=test_timestamp,
        report_path="outputs/discord_signals/BTC_20260131_183045/",
    )
    print(msg2)

    print("\n\n=== Stage 3: Trade Executed ===")
    msg3 = formatter.format_trade_executed(
        ticker="BTC",
        direction="SHORT",
        fill_price=78067.0,
        size=0.001,
        notional=78.07,
        stop_loss=82718.0,
        take_profit=75000.0,
        risk_amount=4.65,
        risk_pct=1.5,
        report_path="outputs/discord_signals/BTC_20260131_183045/",
    )
    print(msg3)
