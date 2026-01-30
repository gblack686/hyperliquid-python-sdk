"""
FastAPI endpoint for Kiyotaka chart screenshot service
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from pathlib import Path
import os
from datetime import datetime
import logging

from screenshot_service import KiyotakaScreenshotService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kiyotaka Screenshot Service", version="1.0.0")

# Global service instance
screenshot_service = None

class ChartRequest(BaseModel):
    chart_id: Optional[str] = None
    symbol: str = "HYPEUSDT"
    exchange: str = "BINANCE.F"
    timeframe: str = "1h"

class BatchChartRequest(BaseModel):
    charts: List[ChartRequest]

class ScreenshotResponse(BaseModel):
    status: str
    message: str
    screenshots: Optional[List[str]] = None
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Initialize the screenshot service on startup"""
    global screenshot_service
    screenshot_service = KiyotakaScreenshotService()
    logger.info("Screenshot service initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global screenshot_service
    if screenshot_service:
        await screenshot_service.cleanup()
    logger.info("Screenshot service shutdown")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "kiyotaka-screenshot"}

@app.post("/screenshot", response_model=ScreenshotResponse)
async def capture_screenshot(request: ChartRequest, background_tasks: BackgroundTasks):
    """
    Capture a single chart screenshot
    
    Args:
        request: Chart configuration
        
    Returns:
        Screenshot response with file path
    """
    try:
        service = KiyotakaScreenshotService()
        await service.initialize()
        await service.login()
        
        screenshot_path = await service.capture_chart(
            chart_id=request.chart_id,
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe
        )
        
        await service.cleanup()
        
        return ScreenshotResponse(
            status="success",
            message="Screenshot captured successfully",
            screenshots=[screenshot_path],
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/screenshot/batch", response_model=ScreenshotResponse)
async def capture_batch_screenshots(request: BatchChartRequest):
    """
    Capture multiple chart screenshots
    
    Args:
        request: List of chart configurations
        
    Returns:
        Screenshot response with file paths
    """
    try:
        service = KiyotakaScreenshotService()
        
        chart_configs = [chart.dict() for chart in request.charts]
        screenshots = await service.run_screenshot_job(chart_configs)
        
        return ScreenshotResponse(
            status="success",
            message=f"Captured {len(screenshots)} screenshots",
            screenshots=screenshots,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error capturing batch screenshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshot/{filename}")
async def get_screenshot(filename: str):
    """
    Retrieve a screenshot by filename
    
    Args:
        filename: Name of the screenshot file
        
    Returns:
        Screenshot image file
    """
    screenshot_path = Path('/app/screenshots') / filename
    
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
        
    return FileResponse(
        path=str(screenshot_path),
        media_type="image/png",
        filename=filename
    )

@app.get("/screenshots/list")
async def list_screenshots():
    """
    List all available screenshots
    
    Returns:
        List of screenshot filenames with metadata
    """
    screenshot_dir = Path('/app/screenshots')
    
    if not screenshot_dir.exists():
        return {"screenshots": []}
        
    screenshots = []
    for file in screenshot_dir.glob("*.png"):
        stat = file.stat()
        screenshots.append({
            "filename": file.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
        
    # Sort by creation time, newest first
    screenshots.sort(key=lambda x: x["created"], reverse=True)
    
    return {"screenshots": screenshots, "total": len(screenshots)}

@app.delete("/screenshot/{filename}")
async def delete_screenshot(filename: str):
    """
    Delete a screenshot
    
    Args:
        filename: Name of the screenshot file to delete
        
    Returns:
        Deletion confirmation
    """
    screenshot_path = Path('/app/screenshots') / filename
    
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
        
    try:
        screenshot_path.unlink()
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        logger.error(f"Error deleting screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/screenshot/scheduled")
async def schedule_screenshot_job(interval_minutes: int = 60):
    """
    Schedule periodic screenshot captures
    
    Args:
        interval_minutes: Interval between captures in minutes
        
    Returns:
        Schedule confirmation
    """
    # This would integrate with a task scheduler like Celery or APScheduler
    # For now, just return a placeholder response
    return {
        "status": "scheduled",
        "interval_minutes": interval_minutes,
        "message": "Screenshot job scheduled (requires task scheduler implementation)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)