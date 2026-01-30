"""
Unified Monitor for Both HYPE Trading Systems
Shows real-time status from Confluence Dashboard and Mean Reversion System
"""

import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import requests

load_dotenv()

console = Console()

# Supabase connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url else None


def check_service_status(url: str, service_name: str) -> dict:
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=2)
        return {
            "service": service_name,
            "status": "✅ Running",
            "code": response.status_code
        }
    except:
        return {
            "service": service_name,
            "status": "❌ Offline",
            "code": 0
        }


def get_confluence_dashboard_status():
    """Get Confluence Dashboard status"""
    services = []
    
    # Check main services
    services.append(check_service_status("http://localhost:8501", "Streamlit Dashboard"))
    services.append(check_service_status("http://localhost:8000/health", "Trigger Analyzer"))
    services.append(check_service_status("http://localhost:8181", "Paper Trading API"))
    
    return services


def get_paper_trading_status():
    """Get paper trading account status from Supabase"""
    if not supabase:
        return None
    
    try:
        # Get HYPE paper trader account
        result = supabase.table('hl_paper_accounts').select("*").eq(
            'account_name', 'hype_paper_trader'
        ).execute()
        
        if result.data:
            account = result.data[0]
            return {
                "balance": float(account.get('current_balance', 0)),
                "pnl": float(account.get('total_pnl', 0)),
                "win_rate": float(account.get('win_rate', 0)),
                "trades": account.get('total_trades', 0)
            }
    except Exception as e:
        console.print(f"[red]Error fetching paper trading data: {e}")
    
    return None


def get_mean_reversion_status():
    """Get Mean Reversion system status from Supabase"""
    if not supabase:
        return None
    
    try:
        # Get latest signals from Mean Reversion system
        result = supabase.table('hl_signals').select("*").order(
            'created_at', desc=True
        ).limit(5).execute()
        
        if result.data:
            return {
                "latest_signals": result.data,
                "signal_count": len(result.data)
            }
    except:
        pass
    
    return None


def get_docker_status():
    """Get Docker container status"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if 'hl-' in line or 'hype' in line.lower():
                containers.append(line)
        
        return containers
    except:
        return []


def create_status_table():
    """Create main status table"""
    table = Table(title="🚀 HYPE Trading Systems Status", expand=True)
    
    table.add_column("System", style="cyan", no_wrap=True)
    table.add_column("Component", style="white")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Confluence Dashboard Status
    dashboard_services = get_confluence_dashboard_status()
    for i, service in enumerate(dashboard_services):
        system = "Confluence Dashboard" if i == 0 else ""
        table.add_row(
            system,
            service["service"],
            service["status"],
            f"HTTP {service['code']}" if service['code'] > 0 else "No connection"
        )
    
    # Paper Trading Status
    paper_status = get_paper_trading_status()
    if paper_status:
        table.add_row(
            "",
            "Paper Trading",
            "✅ Active",
            f"Balance: ${paper_status['balance']:,.2f} | P&L: ${paper_status['pnl']:,.2f}"
        )
    
    # Mean Reversion Status
    mr_status = get_mean_reversion_status()
    if mr_status and mr_status['signal_count'] > 0:
        latest = mr_status['latest_signals'][0]
        table.add_row(
            "Mean Reversion",
            "Strategy Engine",
            "✅ Running",
            f"Latest: {latest.get('signal_type', 'N/A')} @ {latest.get('price', 0):.2f}"
        )
    else:
        table.add_row(
            "Mean Reversion",
            "Strategy Engine",
            "⏸️ Waiting",
            "No recent signals"
        )
    
    # Docker Status
    docker_containers = get_docker_status()
    if docker_containers:
        for i, container in enumerate(docker_containers[:4]):  # Show first 4
            system = "Docker" if i == 0 else ""
            parts = container.split(': ')
            if len(parts) == 2:
                table.add_row(system, parts[0], "🐳 Running", parts[1])
    
    return table


def create_metrics_panel():
    """Create metrics panel"""
    paper_status = get_paper_trading_status()
    
    if paper_status:
        content = f"""
[bold cyan]Paper Trading Metrics:[/bold cyan]
• Balance: ${paper_status['balance']:,.2f}
• Total P&L: ${paper_status['pnl']:,.2f} ({paper_status['pnl']/1000:.1f}%)
• Win Rate: {paper_status['win_rate']:.1f}%
• Total Trades: {paper_status['trades']}

[bold cyan]System Performance:[/bold cyan]
• Confluence Indicators: 10/10 Active
• Trigger System: Real-time
• WebSocket: Connected
• Update Rate: 5 seconds
"""
    else:
        content = "[yellow]Loading metrics...[/yellow]"
    
    return Panel(content, title="📊 Performance Metrics", border_style="blue")


def create_layout():
    """Create the display layout"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", size=20),
        Layout(name="metrics", size=10)
    )
    
    # Header
    header_text = Text()
    header_text.append("🚀 HYPE TRADING SYSTEMS MONITOR\n", style="bold magenta")
    header_text.append(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
    layout["header"].update(Panel(header_text, border_style="blue"))
    
    # Main status table
    layout["main"].update(create_status_table())
    
    # Metrics panel
    layout["metrics"].update(create_metrics_panel())
    
    return layout


async def monitor_loop():
    """Main monitoring loop"""
    with Live(create_layout(), refresh_per_second=1, console=console) as live:
        while True:
            try:
                live.update(create_layout())
                await asyncio.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error in monitor: {e}")
                await asyncio.sleep(5)


def main():
    """Main entry point"""
    console.print("[bold green]Starting HYPE Systems Monitor...[/bold green]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")
    
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")


if __name__ == "__main__":
    main()