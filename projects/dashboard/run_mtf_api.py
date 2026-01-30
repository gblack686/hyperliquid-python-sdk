#!/usr/bin/env python3

import sys
import os
import asyncio
import uvicorn
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(__file__))

from src.api.mtf_data_feed import app

def main():
    logger.info("Starting MTF Data Feed API Server...")
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()