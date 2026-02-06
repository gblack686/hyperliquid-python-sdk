"""
Live Feed Terminal - Aggregated Log Streaming UI

Streams real-time aggregated view of:
  - Hyperliquid fills/orders (HL)
  - Binance liquidations (BN)
  - Momentum monitor signals (MM)
  - Claude session activity (CL)
  - System monitor output (SYS)
  - New output files (OUT)

Usage:
  python scripts/live_feed.py              # Full interactive TUI
  python scripts/live_feed.py --no-tui     # Streaming fallback (rich only)
  python scripts/live_feed.py --sources HL,BN
  python scripts/live_feed.py --poll-interval 2
"""

import argparse
import json
import os
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Resolve project root (two levels up from this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# ---------------------------------------------------------------------------
# Source tags
# ---------------------------------------------------------------------------
SOURCES = ["HL", "BN", "MM", "CL", "SYS", "OUT"]

SOURCE_COLORS = {
    "HL": "cyan",
    "BN": "yellow",
    "MM": "magenta",
    "CL": "blue",
    "SYS": "white",
    "OUT": "green",
}

SOURCE_LABELS = {
    "HL": "Hyperliquid",
    "BN": "Binance Liq",
    "MM": "Momentum",
    "CL": "Claude",
    "SYS": "System",
    "OUT": "Outputs",
}


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------
@dataclass
class LogEntry:
    timestamp: str
    source: str
    level: str  # "info", "warn", "error", "trade"
    message: str
    raw: str = ""


# ---------------------------------------------------------------------------
# LogStore - thread-safe bounded deque
# ---------------------------------------------------------------------------
class LogStore:
    def __init__(self, maxlen: int = 2000):
        self._entries: Deque[LogEntry] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._version = 0  # bumped on every append for change detection
        self._callbacks: List[Callable] = []

    @property
    def version(self) -> int:
        return self._version

    def append(self, entry: LogEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            self._version += 1
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception:
                pass

    def get_all(self, source_filter: Optional[str] = None,
                search: Optional[str] = None) -> List[LogEntry]:
        with self._lock:
            entries = list(self._entries)
        if source_filter and source_filter != "ALL":
            entries = [e for e in entries if e.source == source_filter]
        if search:
            low = search.lower()
            entries = [e for e in entries if low in e.message.lower()]
        return entries

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._version += 1

    def on_entry(self, cb: Callable) -> None:
        self._callbacks.append(cb)

    @property
    def count(self) -> int:
        return len(self._entries)

    def count_by_source(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for e in self._entries:
                counts[e.source] = counts.get(e.source, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def _ts_now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def parse_fills_line(line: str) -> Optional[LogEntry]:
    """Parse fills.log line: 'ISO | {JSON}'"""
    line = line.strip()
    if not line:
        return None
    try:
        parts = line.split(" | ", 1)
        if len(parts) != 2:
            return None
        ts_raw, json_str = parts
        data = json.loads(json_str)
        coin = data.get("coin", "?")
        side = data.get("side", "?")
        sz = data.get("sz", "0")
        px = data.get("px", "0")
        direction = data.get("dir", "")
        closed_pnl = data.get("closedPnl", "0")

        # Map side codes
        side_label = "BUY" if side == "B" else "SELL" if side == "A" else side

        if closed_pnl and closed_pnl != "0":
            pnl_val = float(closed_pnl)
            sign = "+" if pnl_val >= 0 else ""
            msg = f"CLOSE: {coin} {direction} {sz} @ ${float(px):,.2f}  PnL: {sign}${pnl_val:,.2f}"
            level = "trade"
        else:
            msg = f"FILL: {coin} {side_label} {sz} @ ${float(px):,.2f}"
            level = "info"

        ts_short = ts_raw.split("T")[1][:8] if "T" in ts_raw else _ts_now()
        return LogEntry(timestamp=ts_short, source="HL", level=level, message=msg, raw=line)
    except Exception:
        return LogEntry(timestamp=_ts_now(), source="HL", level="info",
                        message=line[:120], raw=line)


def parse_closures_line(line: str) -> Optional[LogEntry]:
    """Parse closures.log line: JSON per line"""
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        coin = data.get("coin", "?")
        pnl = float(data.get("pnl", 0))
        total = float(data.get("total_pnl", 0))
        sign = "+" if pnl >= 0 else ""
        msg = f"CLOSED: {coin} PnL {sign}${pnl:,.2f}  (Total: ${total:,.2f})"
        ts_raw = data.get("timestamp", "")
        ts_short = ts_raw.split("T")[1][:8] if "T" in ts_raw else _ts_now()
        return LogEntry(timestamp=ts_short, source="HL", level="trade",
                        message=msg, raw=line)
    except Exception:
        return None


def parse_claude_hook(entry: dict, hook_type: str) -> Optional[LogEntry]:
    """Parse a Claude hook JSON entry."""
    try:
        event = entry.get("hook_event_name", hook_type)
        if event == "PreToolUse":
            tool = entry.get("tool_name", "?")
            msg = f"TOOL: {tool}"
        elif event == "PostToolUse":
            tool = entry.get("tool_name", "?")
            msg = f"DONE: {tool}"
        elif event == "SessionStart":
            source = entry.get("source", "startup")
            msg = f"SESSION: {source}"
        elif event == "Notification":
            msg = f"NOTE: {entry.get('message', '?')}"
        elif event == "Stop":
            msg = f"STOP: session ended"
        elif event == "SubagentStop":
            msg = "SUBAGENT: stopped"
        else:
            msg = f"{event}: {str(entry)[:80]}"
        return LogEntry(timestamp=_ts_now(), source="CL", level="info",
                        message=msg, raw=json.dumps(entry)[:200])
    except Exception:
        return None


def parse_monitor_line(line: str) -> Optional[LogEntry]:
    """Parse monitor_output.txt line."""
    line = line.strip()
    if not line:
        return None
    return LogEntry(timestamp=_ts_now(), source="SYS", level="info",
                    message=line[:200], raw=line)


# ---------------------------------------------------------------------------
# FileWatcher - polls append-only log files
# ---------------------------------------------------------------------------
class FileWatcher:
    """Watches an append-only text file for new lines."""

    def __init__(self, path: Path, parser: Callable[[str], Optional[LogEntry]],
                 store: LogStore, seek_to_end: bool = True):
        self.path = path
        self.parser = parser
        self.store = store
        self._offset = 0
        self._mtime = 0.0
        if seek_to_end and path.exists():
            self._offset = path.stat().st_size
            self._mtime = path.stat().st_mtime

    def poll(self) -> None:
        if not self.path.exists():
            return
        try:
            st = self.path.stat()
            if st.st_mtime == self._mtime and st.st_size == self._offset:
                return
            if st.st_size < self._offset:
                # File was truncated / rotated
                self._offset = 0
            self._mtime = st.st_mtime
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._offset)
                new_data = f.read()
                self._offset = f.tell()
            for line in new_data.splitlines():
                entry = self.parser(line)
                if entry:
                    self.store.append(entry)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# ClaudeHookWatcher - polls JSON array files, yields new entries only
# ---------------------------------------------------------------------------
class ClaudeHookWatcher:
    """Watches Claude hook JSON files (JSON arrays that grow)."""

    def __init__(self, path: Path, hook_type: str, store: LogStore,
                 skip_existing: bool = True):
        self.path = path
        self.hook_type = hook_type
        self.store = store
        self._mtime = 0.0
        self._count = 0
        if skip_existing and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                self._count = len(data) if isinstance(data, list) else 0
                self._mtime = path.stat().st_mtime
            except Exception:
                pass

    def poll(self) -> None:
        if not self.path.exists():
            return
        try:
            st = self.path.stat()
            if st.st_mtime == self._mtime:
                return
            self._mtime = st.st_mtime
            raw = self.path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
            if not isinstance(data, list):
                return
            new_entries = data[self._count:]
            self._count = len(data)
            for entry in new_entries:
                log_entry = parse_claude_hook(entry, self.hook_type)
                if log_entry:
                    self.store.append(log_entry)
        except (json.JSONDecodeError, ValueError):
            pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# OutputScanner - detects new files in outputs/
# ---------------------------------------------------------------------------
class OutputScanner:
    def __init__(self, directory: Path, store: LogStore,
                 skip_existing: bool = True):
        self.directory = directory
        self.store = store
        self._known: Set[str] = set()
        if skip_existing and directory.exists():
            for p in directory.rglob("*"):
                if p.is_file():
                    self._known.add(str(p))

    def poll(self) -> None:
        if not self.directory.exists():
            return
        try:
            current: Set[str] = set()
            for p in self.directory.rglob("*"):
                if p.is_file():
                    current.add(str(p))
            new_files = current - self._known
            for fp in sorted(new_files):
                rel = Path(fp).relative_to(self.directory)
                self.store.append(LogEntry(
                    timestamp=_ts_now(), source="OUT", level="info",
                    message=f"New file: {rel}",
                    raw=fp
                ))
            self._known = current
        except Exception:
            pass


# ---------------------------------------------------------------------------
# WatcherManager - orchestrates all watchers in a background thread
# ---------------------------------------------------------------------------
class WatcherManager:
    def __init__(self, store: LogStore, poll_interval: float = 1.0,
                 enabled_sources: Optional[Set[str]] = None):
        self.store = store
        self.poll_interval = poll_interval
        self.enabled = enabled_sources or set(SOURCES)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._file_watchers: List[FileWatcher] = []
        self._hook_watchers: List[ClaudeHookWatcher] = []
        self._output_scanner: Optional[OutputScanner] = None
        self._setup()

    def _setup(self) -> None:
        # HL watchers
        if "HL" in self.enabled:
            fills_path = LOGS_DIR / "fills.log"
            closures_path = LOGS_DIR / "closures.log"
            self._file_watchers.append(
                FileWatcher(fills_path, parse_fills_line, self.store))
            self._file_watchers.append(
                FileWatcher(closures_path, parse_closures_line, self.store))

        # SYS watcher
        if "SYS" in self.enabled:
            monitor_path = LOGS_DIR / "monitor_output.txt"
            self._file_watchers.append(
                FileWatcher(monitor_path, parse_monitor_line, self.store))

        # BN and MM - watch via generic log files if they exist
        if "BN" in self.enabled:
            bn_path = LOGS_DIR / "binance_liquidations.log"
            self._file_watchers.append(
                FileWatcher(bn_path, lambda line: LogEntry(
                    timestamp=_ts_now(), source="BN", level="info",
                    message=line.strip()[:200], raw=line.strip()
                ) if line.strip() else None, self.store))

        if "MM" in self.enabled:
            mm_path = LOGS_DIR / "momentum_monitor.log"
            self._file_watchers.append(
                FileWatcher(mm_path, lambda line: LogEntry(
                    timestamp=_ts_now(), source="MM", level="info",
                    message=line.strip()[:200], raw=line.strip()
                ) if line.strip() else None, self.store))

        # CL watchers (Claude hooks)
        if "CL" in self.enabled:
            hook_files = {
                "session_start.json": "SessionStart",
                "pre_tool_use.json": "PreToolUse",
                "post_tool_use.json": "PostToolUse",
                "notification.json": "Notification",
                "stop.json": "Stop",
                "subagent_stop.json": "SubagentStop",
            }
            for fname, htype in hook_files.items():
                path = LOGS_DIR / fname
                self._hook_watchers.append(
                    ClaudeHookWatcher(path, htype, self.store))

        # OUT scanner
        if "OUT" in self.enabled:
            self._output_scanner = OutputScanner(OUTPUTS_DIR, self.store)

    def _poll_loop(self) -> None:
        output_counter = 0
        hook_counter = 0
        while not self._stop_event.is_set():
            # File watchers every poll_interval
            for w in self._file_watchers:
                w.poll()

            # Hook watchers every 2 polls
            hook_counter += 1
            if hook_counter >= 2:
                hook_counter = 0
                for w in self._hook_watchers:
                    w.poll()

            # Output scanner every 5 polls
            output_counter += 1
            if output_counter >= 5:
                output_counter = 0
                if self._output_scanner:
                    self._output_scanner.poll()

            self._stop_event.wait(self.poll_interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    @property
    def active_sources(self) -> int:
        return len(self.enabled)


# ============================================================================
# TUI MODE (Textual)
# ============================================================================
def run_tui(store: LogStore, watcher: WatcherManager) -> None:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        Header, Footer, Static, ListView, ListItem, RichLog, Input, Label
    )
    from textual.reactive import reactive
    from textual.binding import Binding
    from textual import work
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.markdown import Markdown as RichMarkdown

    class LogPanel(RichLog):
        pass

    class FileItem(ListItem):
        def __init__(self, path: str, label: str) -> None:
            super().__init__()
            self.file_path = path
            self.file_label = label

        def compose(self) -> ComposeResult:
            yield Label(self.file_label)

    class LiveFeedApp(App):
        CSS = """
        Screen {
            layout: horizontal;
        }
        #left-panel {
            width: 3fr;
            height: 100%;
        }
        #right-panel {
            width: 1fr;
            height: 100%;
            display: none;
        }
        #right-panel.visible {
            display: block;
        }
        #log-panel {
            height: 1fr;
            border: solid $primary;
        }
        #search-bar {
            height: 3;
            display: none;
        }
        #search-bar.visible {
            display: block;
        }
        #status-bar {
            height: 1;
            background: $surface;
            color: $text;
            text-align: center;
        }
        #file-list {
            height: 2fr;
            border: solid $secondary;
        }
        #file-viewer {
            height: 1fr;
            border: solid $accent;
            display: none;
        }
        #file-viewer.visible {
            display: block;
        }
        #header-bar {
            height: 1;
            background: $primary;
            color: $text;
            text-align: center;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("f", "cycle_filter", "Filter"),
            Binding("slash", "toggle_search", "Search"),
            Binding("o", "toggle_outputs", "Outputs"),
            Binding("p", "toggle_pause", "Pause"),
            Binding("c", "clear_log", "Clear"),
            Binding("escape", "close_overlay", "Close"),
        ]

        source_filter: reactive[str] = reactive("ALL")
        paused: reactive[bool] = reactive(False)
        search_text: reactive[str] = reactive("")

        def __init__(self, store: LogStore, watcher: WatcherManager):
            super().__init__()
            self._store = store
            self._watcher = watcher
            self._last_version = 0
            self._filter_idx = 0
            self._filters = ["ALL"] + SOURCES

        def compose(self) -> ComposeResult:
            yield Static("[*] LIVE FEED TERMINAL", id="header-bar")
            with Horizontal():
                with Vertical(id="left-panel"):
                    yield Input(placeholder="Search...", id="search-bar")
                    yield LogPanel(id="log-panel", highlight=True, markup=True,
                                   max_lines=2000, auto_scroll=True)
                    yield Static("", id="status-bar")
                with Vertical(id="right-panel"):
                    yield Static("OUTPUTS", classes="title")
                    yield ListView(id="file-list")
                    yield RichLog(id="file-viewer", highlight=True, markup=True)
            yield Footer()

        def on_mount(self) -> None:
            self._refresh_timer = self.set_interval(0.5, self._poll_updates)
            self._update_status()
            # Initial welcome entry
            self._store.append(LogEntry(
                timestamp=_ts_now(), source="SYS", level="info",
                message="Live Feed Terminal started. Watching logs...",
                raw=""
            ))

        def _poll_updates(self) -> None:
            if self.paused:
                return
            if self._store.version == self._last_version:
                return
            self._last_version = self._store.version
            self._refresh_log()
            self._update_status()

        def _refresh_log(self) -> None:
            log_panel = self.query_one("#log-panel", LogPanel)
            log_panel.clear()
            entries = self._store.get_all(
                source_filter=self.source_filter,
                search=self.search_text if self.search_text else None
            )
            for entry in entries[-500:]:  # Show last 500 in view
                color = SOURCE_COLORS.get(entry.source, "white")
                line = Text()
                line.append(f"  {entry.timestamp} ", style="dim")
                line.append(f"[{entry.source}]", style=f"bold {color}")
                line.append(f" {entry.message}", style=color)
                log_panel.write(line)

        def _update_status(self) -> None:
            bar = self.query_one("#status-bar", Static)
            counts = self._store.count_by_source()
            parts = [f"{s}:{counts.get(s, 0)}" for s in SOURCES]
            filter_label = f"Filter: {self.source_filter}"
            pause_label = " [PAUSED]" if self.paused else ""
            total = self._store.count
            bar.update(
                f"  {filter_label}  |  Entries: {total}  |  "
                + "  ".join(parts) + pause_label
            )

        # --- Actions ---
        def action_cycle_filter(self) -> None:
            self._filter_idx = (self._filter_idx + 1) % len(self._filters)
            self.source_filter = self._filters[self._filter_idx]
            self._last_version = -1  # force refresh
            self._poll_updates()

        def action_toggle_search(self) -> None:
            search_bar = self.query_one("#search-bar", Input)
            if search_bar.has_class("visible"):
                search_bar.remove_class("visible")
                self.search_text = ""
                self._last_version = -1
                self._poll_updates()
            else:
                search_bar.add_class("visible")
                search_bar.focus()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            if event.input.id == "search-bar":
                self.search_text = event.value
                self._last_version = -1
                self._poll_updates()

        def action_toggle_outputs(self) -> None:
            panel = self.query_one("#right-panel")
            if panel.has_class("visible"):
                panel.remove_class("visible")
            else:
                panel.add_class("visible")
                self._populate_file_list()

        def _populate_file_list(self) -> None:
            lv = self.query_one("#file-list", ListView)
            lv.clear()
            if not OUTPUTS_DIR.exists():
                return
            for p in sorted(OUTPUTS_DIR.rglob("*")):
                if p.is_file():
                    rel = str(p.relative_to(OUTPUTS_DIR))
                    lv.append(FileItem(str(p), rel))

        def on_list_view_selected(self, event: ListView.Selected) -> None:
            item = event.item
            if isinstance(item, FileItem):
                self._show_file(item.file_path)

        def _show_file(self, path: str) -> None:
            viewer = self.query_one("#file-viewer", RichLog)
            viewer.add_class("visible")
            viewer.clear()
            try:
                p = Path(path)
                suffix = p.suffix.lower()
                content = p.read_text(encoding="utf-8", errors="replace")
                if suffix == ".json":
                    try:
                        parsed = json.loads(content)
                        formatted = json.dumps(parsed, indent=2)
                    except Exception:
                        formatted = content
                    syn = Syntax(formatted, "json", theme="monokai",
                                 line_numbers=True)
                    viewer.write(syn)
                elif suffix == ".md":
                    md = RichMarkdown(content)
                    viewer.write(md)
                else:
                    viewer.write(content[:5000])
            except Exception as exc:
                viewer.write(f"Error reading file: {exc}")

        def action_toggle_pause(self) -> None:
            self.paused = not self.paused
            self._update_status()

        def action_clear_log(self) -> None:
            self._store.clear()
            self._last_version = -1
            self._poll_updates()

        def action_close_overlay(self) -> None:
            # Close file viewer
            viewer = self.query_one("#file-viewer", RichLog)
            if viewer.has_class("visible"):
                viewer.remove_class("visible")
                return
            # Close search
            search_bar = self.query_one("#search-bar", Input)
            if search_bar.has_class("visible"):
                search_bar.remove_class("visible")
                self.search_text = ""
                self._last_version = -1
                self._poll_updates()

    app = LiveFeedApp(store, watcher)
    app.run()


# ============================================================================
# FALLBACK MODE (Rich streaming)
# ============================================================================
def run_rich_fallback(store: LogStore, watcher: WatcherManager) -> None:
    from rich.console import Console
    from rich.text import Text

    console = Console()
    console.print(
        "[yellow]TIP: Install textual for interactive TUI: "
        "pip install textual[/yellow]\n"
    )
    console.print("[bold]LIVE FEED TERMINAL[/bold] - streaming mode")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    last_version = store.version

    try:
        while True:
            if store.version != last_version:
                entries = store.get_all()
                # Only print entries we haven't seen
                new_count = store.version - last_version
                last_version = store.version
                for entry in entries[-new_count:]:
                    color = SOURCE_COLORS.get(entry.source, "white")
                    line = Text()
                    line.append(f"{entry.timestamp} ", style="dim")
                    line.append(f"[{entry.source}]", style=f"bold {color}")
                    line.append(f" {entry.message}", style=color)
                    console.print(line)
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Feed stopped.[/yellow]")


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live Feed Terminal - Aggregated Log Streaming UI")
    parser.add_argument("--no-tui", action="store_true",
                        help="Use plain Rich streaming instead of Textual TUI")
    parser.add_argument("--sources", type=str, default=None,
                        help="Comma-separated source filter (e.g. HL,BN,CL)")
    parser.add_argument("--poll-interval", type=float, default=1.0,
                        help="Poll interval in seconds (default: 1.0)")
    args = parser.parse_args()

    # Parse source filter
    enabled: Optional[Set[str]] = None
    if args.sources:
        enabled = set(s.strip().upper() for s in args.sources.split(","))
        invalid = enabled - set(SOURCES)
        if invalid:
            print(f"Warning: Unknown sources: {invalid}. "
                  f"Valid: {', '.join(SOURCES)}")
            enabled = enabled & set(SOURCES)

    store = LogStore(maxlen=2000)
    watcher = WatcherManager(store, poll_interval=args.poll_interval,
                             enabled_sources=enabled)
    watcher.start()

    use_tui = not args.no_tui
    if use_tui:
        try:
            import textual  # noqa: F401
        except ImportError:
            print("textual not installed - falling back to streaming mode.")
            print("Install with: pip install textual\n")
            use_tui = False

    try:
        if use_tui:
            run_tui(store, watcher)
        else:
            run_rich_fallback(store, watcher)
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
