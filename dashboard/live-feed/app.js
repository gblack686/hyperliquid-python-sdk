// Live Feed - SSE Client
// Connects to /api/feed/stream for real-time log entries

(function () {
    'use strict';

    // --- State ---
    var entries = [];
    var MAX_ENTRIES = 2000;
    var currentFilter = 'ALL';
    var searchText = '';
    var paused = false;
    var eventSource = null;
    var reconnectDelay = 1000;
    var maxReconnectDelay = 30000;

    // --- DOM refs ---
    var logContainer = document.getElementById('log-container');
    var logEmpty = document.getElementById('log-empty');
    var entryCountEl = document.getElementById('entry-count');
    var statusIndicator = document.getElementById('status-indicator');
    var statusText = document.getElementById('status-text');
    var pauseBtn = document.getElementById('pause-btn');
    var searchInput = document.getElementById('search-input');

    // --- Rendering ---
    function createEntryEl(entry) {
        var div = document.createElement('div');
        div.className = 'log-entry';
        div.dataset.source = entry.source;

        var ts = document.createElement('span');
        ts.className = 'log-ts';
        ts.textContent = entry.timestamp;

        var src = document.createElement('span');
        src.className = 'log-source ' + entry.source.toLowerCase();
        src.textContent = entry.source;

        var msg = document.createElement('span');
        msg.className = 'log-msg';
        if (entry.level === 'error') msg.className += ' level-error';
        else if (entry.level === 'warn') msg.className += ' level-warn';
        else if (entry.level === 'trade') msg.className += ' level-trade';
        msg.textContent = entry.message;

        div.appendChild(ts);
        div.appendChild(src);
        div.appendChild(msg);

        // Apply visibility based on current filters
        if (!matchesFilter(entry)) {
            div.classList.add('hidden');
        }

        return div;
    }

    function matchesFilter(entry) {
        if (currentFilter !== 'ALL' && entry.source !== currentFilter) {
            return false;
        }
        if (searchText && entry.message.toLowerCase().indexOf(searchText) === -1) {
            return false;
        }
        return true;
    }

    function addEntry(entry) {
        entries.push(entry);

        // Prune oldest if over limit
        if (entries.length > MAX_ENTRIES) {
            entries.shift();
            var firstChild = logContainer.querySelector('.log-entry');
            if (firstChild) {
                logContainer.removeChild(firstChild);
            }
        }

        // Hide empty message
        if (logEmpty) {
            logEmpty.style.display = 'none';
        }

        var el = createEntryEl(entry);
        logContainer.appendChild(el);

        // Auto-scroll if not paused
        if (!paused) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        updateCount();
    }

    function updateCount() {
        var visible = 0;
        for (var i = 0; i < entries.length; i++) {
            if (matchesFilter(entries[i])) visible++;
        }
        entryCountEl.textContent = visible + ' / ' + entries.length + ' entries';
    }

    // --- Filters ---
    window.setFilter = function (source) {
        currentFilter = source;

        // Update button states
        var btns = document.querySelectorAll('.filter-btn');
        btns.forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.source === source);
        });

        applyFiltersToDOM();
    };

    window.applyFilters = function () {
        searchText = searchInput.value.toLowerCase();
        applyFiltersToDOM();
    };

    function applyFiltersToDOM() {
        var els = logContainer.querySelectorAll('.log-entry');
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            var entry = entries[i];
            if (entry && matchesFilter(entry)) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
        updateCount();

        // Auto-scroll after filter change
        if (!paused) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }

    // --- Pause/Resume ---
    window.togglePause = function () {
        paused = !paused;
        pauseBtn.textContent = paused ? 'Resume' : 'Pause';
        pauseBtn.classList.toggle('paused', paused);
        if (!paused) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    };

    // --- Clear ---
    window.clearLogs = function () {
        entries = [];
        var entryEls = logContainer.querySelectorAll('.log-entry');
        entryEls.forEach(function (el) { el.remove(); });
        if (logEmpty) logEmpty.style.display = '';
        updateCount();
    };

    // --- Connection Status ---
    function setConnected() {
        statusIndicator.classList.remove('disconnected');
        statusText.textContent = 'Live';
        reconnectDelay = 1000;
    }

    function setDisconnected() {
        statusIndicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }

    // --- SSE ---
    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/feed/stream?source=ALL');

        eventSource.onopen = function () {
            setConnected();
        };

        eventSource.onmessage = function (event) {
            try {
                var entry = JSON.parse(event.data);
                addEntry(entry);
            } catch (e) {
                // Ignore parse errors (keepalives etc.)
            }
        };

        eventSource.onerror = function () {
            setDisconnected();
            eventSource.close();
            eventSource = null;

            // Reconnect with backoff
            setTimeout(function () {
                reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
                connectSSE();
            }, reconnectDelay);
        };
    }

    // --- Initial Load ---
    function loadSnapshot() {
        fetch('/api/feed/snapshot?source=ALL')
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                for (var i = 0; i < data.length; i++) {
                    addEntry(data[i]);
                }
                // Start SSE after snapshot
                connectSSE();
            })
            .catch(function () {
                // Snapshot failed, just connect SSE directly
                connectSSE();
            });
    }

    // --- Boot ---
    loadSnapshot();

})();
