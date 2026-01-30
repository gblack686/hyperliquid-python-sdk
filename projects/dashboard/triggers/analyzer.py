"""
Analysis service for trigger decisions
FastAPI endpoint that receives trigger data and returns trading decisions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import aiohttp
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trigger Analysis Service")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4-turbo-preview"


class TriggerRequest(BaseModel):
    """Incoming trigger analysis request"""
    trigger: str
    timestamp: float
    symbol: str
    features: Dict[str, Any]


class AnalysisResponse(BaseModel):
    """Analysis decision response"""
    action: str  # "confirm", "cancel", "modify"
    confidence: float  # 0-1
    size_adjustment: float  # multiplier for position size
    tp_atr: float  # take profit in ATR multiples
    sl_atr: float  # stop loss in ATR multiples
    reasoning: str
    continuation_probability: float  # 0-1


class LLMAnalyzer:
    """LLM-based trigger analysis"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.system_prompt = self.build_system_prompt()
        
    def build_system_prompt(self) -> str:
        """Build the system prompt for analysis"""
        return """You are a quantitative trading analyst evaluating pre-emptive trading signals.
        
Your task is to analyze real-time market features and confirm/reject trading triggers.

Input features include:
- CVD slope (Cumulative Volume Delta momentum)
- OI delta (Open Interest changes)
- Funding rate (in basis points)
- L/S ratio (Long/Short positioning)
- VWAP z-score (standard deviations from VWAP)
- Basis (spot vs perp differential)

Respond with a JSON object containing:
- action: "confirm" to proceed, "cancel" to abort, "modify" to adjust
- confidence: 0-1 score
- size_adjustment: position size multiplier (0.5 = half size, 2.0 = double)
- tp_atr: take profit in ATR multiples (typically 1-3)
- sl_atr: stop loss in ATR multiples (typically 0.5-1.5)
- reasoning: brief explanation (max 50 words)
- continuation_probability: 0-1 chance the move continues

Focus on:
1. Confluence of signals (multiple indicators aligned)
2. Market structure (support/resistance context)
3. Risk/reward ratio
4. Momentum sustainability
"""
        
    def build_analysis_prompt(self, request: TriggerRequest) -> str:
        """Build the specific analysis prompt"""
        return f"""Analyze this {request.trigger} trigger for {request.symbol}:

Features:
- Price: ${request.features.get('last_px', 0):.2f}
- CVD slope (1m): {request.features.get('cvd_slope_1m', 0):.3f}
- CVD slope (5m): {request.features.get('cvd_slope_5m', 0):.3f}
- OI delta (5m): {request.features.get('oi_delta_5m_pct', 0):.2f}%
- OI delta (15m): {request.features.get('oi_delta_15m_pct', 0):.2f}%
- Funding: {request.features.get('funding_bp', 0):.2f} bp
- Basis: {request.features.get('basis_bps', 0):.2f} bps
- L/S ratio: {request.features.get('ls_ratio', 0):.2f}
- VWAP z-score: {request.features.get('vwap_z_1m', 0):.2f}
- Trade burst: {request.features.get('trade_burst', False)}

Trigger type: {request.trigger}
- squeeze_down: shorts trapped, potential violent up move
- squeeze_up: longs trapped, potential violent down move
- reversion_fade: extreme deviation, expect mean reversion
- breakout_continuation: momentum acceleration

Provide your analysis in JSON format."""
        
    async def analyze(self, request: TriggerRequest) -> AnalysisResponse:
        """Perform LLM analysis"""
        if not self.api_key:
            # Return default conservative response if no API key
            return AnalysisResponse(
                action="cancel",
                confidence=0.3,
                size_adjustment=0.5,
                tp_atr=1.0,
                sl_atr=0.7,
                reasoning="No LLM configured, defaulting to conservative",
                continuation_probability=0.5
            )
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.build_analysis_prompt(request)}
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "max_tokens": 300
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"]
                        result = json.loads(content)
                        
                        return AnalysisResponse(**result)
                    else:
                        logger.error(f"OpenAI API error: {resp.status}")
                        raise HTTPException(status_code=500, detail="LLM analysis failed")
                        
        except asyncio.TimeoutError:
            logger.warning("LLM analysis timeout, using fallback")
            return self.get_fallback_response(request)
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return self.get_fallback_response(request)
            
    def get_fallback_response(self, request: TriggerRequest) -> AnalysisResponse:
        """Fallback response based on simple rules"""
        # Conservative fallback logic
        features = request.features
        
        # Check signal confluence
        confluence_score = 0
        if abs(features.get("cvd_slope_1m", 0)) > 0.3:
            confluence_score += 1
        if abs(features.get("oi_delta_5m_pct", 0)) > 0.5:
            confluence_score += 1
        if abs(features.get("vwap_z_1m", 0)) > 1.5:
            confluence_score += 1
        if features.get("trade_burst", False):
            confluence_score += 1
            
        # Decision based on confluence
        if confluence_score >= 3:
            action = "confirm"
            confidence = 0.7
            size_adjustment = 1.0
        elif confluence_score >= 2:
            action = "modify"
            confidence = 0.5
            size_adjustment = 0.5
        else:
            action = "cancel"
            confidence = 0.3
            size_adjustment = 0
            
        return AnalysisResponse(
            action=action,
            confidence=confidence,
            size_adjustment=size_adjustment,
            tp_atr=1.5 if "squeeze" in request.trigger else 1.0,
            sl_atr=0.7,
            reasoning=f"Fallback decision with {confluence_score}/4 signals aligned",
            continuation_probability=confidence
        )


class LocalAnalyzer:
    """Local statistical analysis (no LLM)"""
    
    def analyze(self, request: TriggerRequest) -> Dict[str, Any]:
        """Perform local statistical analysis"""
        features = request.features
        
        # Calculate momentum score
        momentum = (
            features.get("cvd_slope_1m", 0) * 0.3 +
            features.get("cvd_slope_5m", 0) * 0.2 +
            features.get("oi_delta_5m_pct", 0) * 0.5
        )
        
        # Calculate positioning score
        positioning = 0
        ls_ratio = features.get("ls_ratio", 1.0)
        if ls_ratio > 2.0:  # Heavily long
            positioning = -1
        elif ls_ratio < 0.5:  # Heavily short
            positioning = 1
        else:
            positioning = (1 - ls_ratio) / 1.5
            
        # Calculate mean reversion score
        vwap_z = features.get("vwap_z_1m", 0)
        reversion = -vwap_z / 3 if abs(vwap_z) < 3 else -1 if vwap_z > 0 else 1
        
        return {
            "momentum_score": momentum,
            "positioning_score": positioning,
            "reversion_score": reversion,
            "composite_score": (momentum * 0.4 + positioning * 0.3 + reversion * 0.3)
        }


# Initialize analyzers
llm_analyzer = LLMAnalyzer()
local_analyzer = LocalAnalyzer()


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_trigger(request: TriggerRequest):
    """Analyze trigger and return trading decision"""
    logger.info(f"Analyzing {request.trigger} for {request.symbol}")
    
    # Perform parallel analysis
    llm_task = asyncio.create_task(llm_analyzer.analyze(request))
    local_stats = local_analyzer.analyze(request)
    
    # Wait for LLM with timeout
    try:
        llm_response = await asyncio.wait_for(llm_task, timeout=20)
    except asyncio.TimeoutError:
        logger.warning("LLM timeout, using local analysis")
        llm_response = llm_analyzer.get_fallback_response(request)
        
    # Log decision
    logger.info(f"Decision: {llm_response.action} (confidence: {llm_response.confidence:.2f})")
    logger.info(f"Local stats: momentum={local_stats['momentum_score']:.2f}, "
                f"positioning={local_stats['positioning_score']:.2f}")
    
    return llm_response


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "llm_configured": bool(OPENAI_API_KEY)
    }


@app.post("/webhook/n8n")
async def n8n_webhook(request: TriggerRequest):
    """Webhook endpoint for n8n integration"""
    # Process the trigger analysis
    response = await analyze_trigger(request)
    
    # Format for n8n workflow
    return {
        "trigger": request.trigger,
        "symbol": request.symbol,
        "decision": response.action,
        "confidence": response.confidence,
        "orders": {
            "size_multiplier": response.size_adjustment,
            "take_profit_atr": response.tp_atr,
            "stop_loss_atr": response.sl_atr
        },
        "analysis": {
            "reasoning": response.reasoning,
            "continuation_probability": response.continuation_probability,
            "features": request.features
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("Trigger Analysis Service")
    print(f"LLM: {'Configured' if OPENAI_API_KEY else 'Not configured (using fallback)'}")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)