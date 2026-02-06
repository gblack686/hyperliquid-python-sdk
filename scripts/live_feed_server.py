"""
Live Feed SSE Server - FastAPI backend for the web-based live feed dashboard.

Reuses LogStore, WatcherManager, and parsers from live_feed.py.
Exposes:
  GET /api/feed/stream?source=ALL   - SSE stream of new log entries
  GET /api/feed/snapshot?source=ALL - JSON dump of last 500 entries
  GET /api/feed/health              - Health check

Run:
  uvicorn scripts.live_feed_server:app --host 127.0.0.1 --port 8099
"""

import asyncio
import json
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse

from scripts.live_feed import (
    LogEntry, LogStore, WatcherManager, SOURCES, SOURCE_LABELS,
)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
store = LogStore(maxlen=2000)
watcher = WatcherManager(store, poll_interval=1.0)
watcher.start()

app = FastAPI(title="Live Feed API", docs_url=None, redoc_url=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _entry_to_dict(entry: LogEntry) -> dict:
    return {
        "timestamp": entry.timestamp,
        "source": entry.source,
        "level": entry.level,
        "message": entry.message,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/feed/health")
async def health():
    return {
        "status": "ok",
        "entries": store.count,
        "sources": store.count_by_source(),
        "watching": watcher.active_sources,
    }


@app.get("/api/feed/snapshot")
async def snapshot(source: Optional[str] = Query("ALL")):
    entries = store.get_all(source_filter=source)
    return JSONResponse(content=[_entry_to_dict(e) for e in entries[-500:]])


@app.get("/api/feed/stream")
async def stream(source: Optional[str] = Query("ALL")):
    async def event_generator():
        last_version = store.version
        # Send initial keepalive
        yield ": keepalive\n\n"
        while True:
            if store.version != last_version:
                entries = store.get_all(source_filter=source)
                new_count = store.version - last_version
                last_version = store.version
                for entry in entries[-new_count:]:
                    data = json.dumps(_entry_to_dict(entry))
                    yield f"data: {data}\n\n"
            else:
                # Send keepalive comment every 15s to prevent timeout
                yield ": keepalive\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.on_event("shutdown")
def shutdown():
    watcher.stop()
