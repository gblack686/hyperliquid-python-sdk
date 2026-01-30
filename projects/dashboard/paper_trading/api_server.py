"""
API server for paper trading data
Provides RESTful endpoints for dashboard integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uvicorn

load_dotenv()

app = FastAPI(title="Paper Trading API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)


@app.get("/")
async def root():
    """API health check"""
    return {"status": "running", "service": "paper_trading_api"}


@app.get("/accounts")
async def get_accounts():
    """Get all paper trading accounts"""
    try:
        result = supabase.table('hl_paper_accounts').select("*").execute()
        return {"success": True, "accounts": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/accounts/{account_name}")
async def get_account(account_name: str):
    """Get specific paper trading account"""
    try:
        result = supabase.table('hl_paper_accounts').select("*").eq(
            'account_name', account_name
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return {"success": True, "account": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions/{account_name}")
async def get_positions(account_name: str, open_only: bool = True):
    """Get positions for an account"""
    try:
        # Get account ID
        account_result = supabase.table('hl_paper_accounts').select("id").eq(
            'account_name', account_name
        ).execute()
        
        if not account_result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_id = account_result.data[0]['id']
        
        # Get positions
        query = supabase.table('hl_paper_positions').select("*").eq(
            'account_id', account_id
        )
        
        if open_only:
            query = query.eq('is_open', True)
        
        result = query.execute()
        
        return {"success": True, "positions": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades/{account_name}")
async def get_trades(account_name: str, limit: int = 100):
    """Get recent trades for an account"""
    try:
        # Get account ID
        account_result = supabase.table('hl_paper_accounts').select("id").eq(
            'account_name', account_name
        ).execute()
        
        if not account_result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_id = account_result.data[0]['id']
        
        # Get trades
        result = supabase.table('hl_paper_trades').select("*").eq(
            'account_id', account_id
        ).order('created_at', desc=True).limit(limit).execute()
        
        return {"success": True, "trades": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{account_name}")
async def get_orders(account_name: str, status: Optional[str] = None, limit: int = 100):
    """Get orders for an account"""
    try:
        # Get account ID
        account_result = supabase.table('hl_paper_accounts').select("id").eq(
            'account_name', account_name
        ).execute()
        
        if not account_result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_id = account_result.data[0]['id']
        
        # Get orders
        query = supabase.table('hl_paper_orders').select("*").eq(
            'account_id', account_id
        )
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('created_at', desc=True).limit(limit).execute()
        
        return {"success": True, "orders": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/performance/{account_name}")
async def get_performance(account_name: str, days: int = 7):
    """Get performance metrics for an account"""
    try:
        # Get account ID
        account_result = supabase.table('hl_paper_accounts').select("*").eq(
            'account_name', account_name
        ).execute()
        
        if not account_result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account = account_result.data[0]
        account_id = account['id']
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily performance
        result = supabase.table('hl_paper_performance').select("*").eq(
            'account_id', account_id
        ).gte('date', start_date.isoformat()).lte('date', end_date.isoformat()).execute()
        
        # Calculate statistics
        if result.data:
            daily_pnls = [float(d['daily_pnl']) for d in result.data]
            win_days = len([p for p in daily_pnls if p > 0])
            lose_days = len([p for p in daily_pnls if p < 0])
            
            stats = {
                "total_pnl": sum(daily_pnls),
                "avg_daily_pnl": sum(daily_pnls) / len(daily_pnls) if daily_pnls else 0,
                "best_day": max(daily_pnls) if daily_pnls else 0,
                "worst_day": min(daily_pnls) if daily_pnls else 0,
                "win_days": win_days,
                "lose_days": lose_days,
                "win_rate_days": (win_days / (win_days + lose_days) * 100) if (win_days + lose_days) > 0 else 0
            }
        else:
            stats = {
                "total_pnl": 0,
                "avg_daily_pnl": 0,
                "best_day": 0,
                "worst_day": 0,
                "win_days": 0,
                "lose_days": 0,
                "win_rate_days": 0
            }
        
        return {
            "success": True,
            "account": {
                "name": account['account_name'],
                "current_balance": float(account['current_balance']),
                "initial_balance": float(account['initial_balance']),
                "total_pnl": float(account.get('total_pnl', 0)),
                "total_pnl_pct": float(account.get('total_pnl_pct', 0)),
                "win_rate": float(account.get('win_rate', 0)),
                "max_drawdown": float(account.get('max_drawdown', 0)),
                "total_trades": account.get('total_trades', 0)
            },
            "daily_performance": result.data,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/triggers/recent")
async def get_recent_triggers(limit: int = 50):
    """Get recent trigger signals"""
    try:
        result = supabase.table('hl_triggers').select("*").order(
            'created_at', desc=True
        ).limit(limit).execute()
        
        return {"success": True, "triggers": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary")
async def get_summary():
    """Get overall paper trading summary"""
    try:
        # Get all accounts
        accounts_result = supabase.table('hl_paper_accounts').select("*").execute()
        
        total_balance = sum([float(a['current_balance']) for a in accounts_result.data])
        total_initial = sum([float(a['initial_balance']) for a in accounts_result.data])
        total_pnl = total_balance - total_initial
        
        # Get today's trades
        today = datetime.now().date().isoformat()
        trades_result = supabase.table('hl_paper_trades').select("*").gte(
            'created_at', f"{today}T00:00:00"
        ).execute()
        
        # Get open positions
        positions_result = supabase.table('hl_paper_positions').select("*").eq(
            'is_open', True
        ).execute()
        
        return {
            "success": True,
            "summary": {
                "total_accounts": len(accounts_result.data),
                "total_balance": total_balance,
                "total_initial": total_initial,
                "total_pnl": total_pnl,
                "total_pnl_pct": (total_pnl / total_initial * 100) if total_initial > 0 else 0,
                "trades_today": len(trades_result.data),
                "open_positions": len(positions_result.data),
                "active_accounts": [a['account_name'] for a in accounts_result.data]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8181)