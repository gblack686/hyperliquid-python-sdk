// Paper Trading Dashboard - Supabase Client
const SUPABASE_URL = 'https://lfxlrxwxnvtrzwsohojz.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxmeGxyeHd4bnZ0cnp3c29ob2p6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2NTk0MDIsImV4cCI6MjA2MDIzNTQwMn0.kBCpCkkfxcHWhycF6-ClE_o_AUmfBzJi6dnU5vDJUKI';

const REFRESH_INTERVAL = 60000; // 60 seconds

// Strategy display mapping
const STRATEGY_NAMES = {
    'funding_arbitrage': 'Funding Arbitrage',
    'grid_trading': 'Grid Trading',
    'directional_momentum': 'Directional Momentum'
};

const STRATEGY_CLASSES = {
    'funding_arbitrage': 'funding',
    'grid_trading': 'grid',
    'directional_momentum': 'momentum'
};

// Supabase REST API helper
async function supabaseQuery(table, params = {}) {
    const url = new URL(`${SUPABASE_URL}/rest/v1/${table}`);

    // Add query parameters
    Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
    });

    const response = await fetch(url, {
        headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        throw new Error(`Supabase error: ${response.status}`);
    }

    return response.json();
}

// Format time ago
function timeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

// Format duration
function formatDuration(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
}

// Format price
function formatPrice(price) {
    const num = parseFloat(price);
    if (num >= 1000) return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (num >= 1) return `$${num.toFixed(4)}`;
    return `$${num.toPrecision(4)}`;
}

// Format P&L with color class
function formatPnl(value, isPercent = false) {
    const num = parseFloat(value);
    const formatted = isPercent
        ? `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`
        : `${num >= 0 ? '+' : ''}$${Math.abs(num).toFixed(2)}`;
    const colorClass = num >= 0 ? 'positive' : 'negative';
    return { formatted, colorClass };
}

// Fetch active signals
async function fetchActiveSignals() {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    return supabaseQuery('paper_recommendations', {
        'select': '*',
        'status': 'eq.ACTIVE',
        'order': 'created_at.desc',
        'limit': '50'
    });
}

// Fetch recent recommendations (24h)
async function fetchRecentRecommendations() {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    return supabaseQuery('paper_recommendations', {
        'select': '*',
        'created_at': `gte.${twentyFourHoursAgo}`,
        'order': 'created_at.desc'
    });
}

// Fetch recent outcomes (24h)
async function fetchRecentOutcomes() {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    // First get outcomes
    const outcomes = await supabaseQuery('paper_recommendation_outcomes', {
        'select': '*,paper_recommendations(*)',
        'outcome_time': `gte.${twentyFourHoursAgo}`,
        'order': 'outcome_time.desc',
        'limit': '50'
    });

    return outcomes;
}

// Update overview metrics
function updateOverviewMetrics(recommendations, outcomes) {
    // Total signals (24h)
    const totalSignals = recommendations.length;
    document.getElementById('total-signals').textContent = totalSignals;

    // Count by strategy
    const byStrategy = {};
    recommendations.forEach(r => {
        byStrategy[r.strategy_name] = (byStrategy[r.strategy_name] || 0) + 1;
    });
    const breakdown = Object.entries(byStrategy)
        .map(([s, c]) => `${c} ${STRATEGY_NAMES[s]?.split(' ')[0] || s}`)
        .join(', ');
    document.getElementById('signals-breakdown').textContent = breakdown || 'No signals';

    // Win rate
    const wins = outcomes.filter(o => o.outcome_type === 'TARGET_HIT').length;
    const losses = outcomes.filter(o => o.outcome_type === 'STOPPED' || o.outcome_type === 'EXPIRED').length;
    const total = wins + losses;
    const winRate = total > 0 ? (wins / total * 100).toFixed(1) : 0;
    document.getElementById('win-rate').textContent = `${winRate}%`;
    document.getElementById('win-loss').textContent = `${wins} W / ${losses} L`;

    // Total P&L
    const totalPnlUsd = outcomes.reduce((sum, o) => sum + parseFloat(o.pnl_usd || 0), 0);
    const totalPnlPct = outcomes.reduce((sum, o) => sum + parseFloat(o.pnl_pct || 0), 0);
    const pnlFormatted = formatPnl(totalPnlUsd);
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.textContent = pnlFormatted.formatted;
    pnlEl.className = `metric-value ${pnlFormatted.colorClass}`;
    document.getElementById('pnl-pct').textContent = `${totalPnlPct >= 0 ? '+' : ''}${totalPnlPct.toFixed(2)}%`;

    // Active signals
    const activeSignals = recommendations.filter(r => r.status === 'ACTIVE').length;
    document.getElementById('active-signals').textContent = activeSignals;
    const activeByStrategy = {};
    recommendations.filter(r => r.status === 'ACTIVE').forEach(r => {
        activeByStrategy[r.strategy_name] = (activeByStrategy[r.strategy_name] || 0) + 1;
    });
    const activeBreakdown = Object.entries(activeByStrategy)
        .map(([s, c]) => `${c} ${STRATEGY_NAMES[s]?.split(' ')[0] || s}`)
        .join(', ');
    document.getElementById('active-breakdown').textContent = activeBreakdown || 'None active';
}

// Update strategy cards
function updateStrategyCards(recommendations, outcomes) {
    const strategies = ['funding_arbitrage', 'grid_trading', 'directional_momentum'];
    const prefixes = ['funding', 'grid', 'momentum'];

    strategies.forEach((strategy, i) => {
        const prefix = prefixes[i];
        const strategyRecs = recommendations.filter(r => r.strategy_name === strategy);
        const strategyOutcomes = outcomes.filter(o =>
            o.paper_recommendations?.strategy_name === strategy
        );

        // Signals count
        document.getElementById(`${prefix}-signals`).textContent = strategyRecs.length;

        // Win rate
        const wins = strategyOutcomes.filter(o => o.outcome_type === 'TARGET_HIT').length;
        const total = strategyOutcomes.length;
        const winRate = total > 0 ? (wins / total * 100).toFixed(0) : 0;
        document.getElementById(`${prefix}-winrate`).textContent = `${winRate}%`;

        // P&L
        const pnl = strategyOutcomes.reduce((sum, o) => sum + parseFloat(o.pnl_usd || 0), 0);
        const pnlFormatted = formatPnl(pnl);
        const pnlEl = document.getElementById(`${prefix}-pnl`);
        pnlEl.textContent = pnlFormatted.formatted;
        pnlEl.className = `stat-value ${pnlFormatted.colorClass}`;

        // Progress bar (win rate)
        document.getElementById(`${prefix}-bar`).style.width = `${winRate}%`;
    });
}

// Render active signals table
function renderActiveSignals(signals) {
    const tbody = document.getElementById('active-tbody');
    document.getElementById('active-count').textContent = signals.length;

    if (signals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading">No active signals</td></tr>';
        return;
    }

    tbody.innerHTML = signals.map(signal => {
        const createdAt = new Date(signal.created_at);
        const strategyClass = STRATEGY_CLASSES[signal.strategy_name] || '';
        const directionClass = signal.direction.toLowerCase();

        return `
            <tr>
                <td>${timeAgo(createdAt)}</td>
                <td><span class="strategy-tag ${strategyClass}">${STRATEGY_NAMES[signal.strategy_name] || signal.strategy_name}</span></td>
                <td><strong>${signal.symbol}</strong></td>
                <td><span class="direction ${directionClass}">${signal.direction}</span></td>
                <td class="price">${formatPrice(signal.entry_price)}</td>
                <td class="price">${formatPrice(signal.target_price_1)}</td>
                <td class="price">${formatPrice(signal.stop_loss_price)}</td>
                <td>
                    <div class="confidence-bar">
                        <div class="confidence-fill">
                            <div class="confidence-fill-inner" style="width: ${signal.confidence_score}%"></div>
                        </div>
                        <span class="confidence-text">${signal.confidence_score}</span>
                    </div>
                </td>
                <td><span class="status-active">Active</span></td>
            </tr>
        `;
    }).join('');
}

// Render outcomes table
function renderOutcomes(outcomes) {
    const tbody = document.getElementById('outcomes-tbody');
    document.getElementById('outcomes-count').textContent = outcomes.length;

    if (outcomes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No recent outcomes</td></tr>';
        return;
    }

    tbody.innerHTML = outcomes.map(outcome => {
        const rec = outcome.paper_recommendations || {};
        const outcomeTime = new Date(outcome.outcome_time);
        const strategyClass = STRATEGY_CLASSES[rec.strategy_name] || '';
        const directionClass = (rec.direction || '').toLowerCase();

        // Outcome type styling
        let outcomeClass = '';
        let outcomeText = outcome.outcome_type;
        if (outcome.outcome_type === 'TARGET_HIT') {
            outcomeClass = 'target-hit';
            outcomeText = 'Target Hit';
        } else if (outcome.outcome_type === 'STOPPED') {
            outcomeClass = 'stopped';
            outcomeText = 'Stopped';
        } else if (outcome.outcome_type === 'EXPIRED') {
            outcomeClass = 'expired';
            outcomeText = 'Expired';
        }

        const pnlPct = formatPnl(outcome.pnl_pct, true);
        const pnlUsd = formatPnl(outcome.pnl_usd);

        return `
            <tr>
                <td>${timeAgo(outcomeTime)}</td>
                <td><span class="strategy-tag ${strategyClass}">${STRATEGY_NAMES[rec.strategy_name] || rec.strategy_name}</span></td>
                <td><strong>${rec.symbol || '--'}</strong></td>
                <td><span class="direction ${directionClass}">${rec.direction || '--'}</span></td>
                <td><span class="outcome ${outcomeClass}">${outcomeText}</span></td>
                <td><span class="pnl ${pnlPct.colorClass}">${pnlPct.formatted}</span></td>
                <td><span class="pnl ${pnlUsd.colorClass}">${pnlUsd.formatted}</span></td>
                <td>${formatDuration(outcome.hold_duration_minutes)}</td>
            </tr>
        `;
    }).join('');
}

// Update last updated timestamp
function updateTimestamp() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    document.getElementById('last-updated').textContent = `Updated: ${timeStr} UTC`;
}

// Fetch recent backtest results
async function fetchBacktestResults() {
    try {
        return await supabaseQuery('paper_backtest_results', {
            'select': 'id,created_at,engine,formula,strategy_name,tickers,total_return_pct,sharpe_ratio,max_drawdown,win_rate,sortino_ratio,cagr,profit_factor,equity_curve,starting_capital,terminal_value',
            'order': 'created_at.desc',
            'limit': '10'
        });
    } catch (e) {
        console.warn('Backtest results not available:', e);
        return [];
    }
}

// Render backtest results table with expandable equity curve
function renderBacktestResults(backtests) {
    const tbody = document.getElementById('backtests-tbody');
    const countEl = document.getElementById('backtests-count');
    if (!tbody || !countEl) return;

    countEl.textContent = backtests.length;

    if (backtests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No backtests yet</td></tr>';
        return;
    }

    // Store backtests globally for chart rendering
    window._backtestData = backtests;

    tbody.innerHTML = backtests.map((bt, idx) => {
        const createdAt = new Date(bt.created_at);
        const label = bt.formula
            ? bt.formula.substring(0, 40) + (bt.formula.length > 40 ? '...' : '')
            : bt.strategy_name || '--';
        const tickers = Array.isArray(bt.tickers) ? bt.tickers.join(', ') : '--';
        const retPct = bt.total_return_pct != null ? parseFloat(bt.total_return_pct) : null;
        const sharpe = bt.sharpe_ratio != null ? parseFloat(bt.sharpe_ratio).toFixed(2) : '--';
        const maxDD = bt.max_drawdown != null ? (parseFloat(bt.max_drawdown) * 100).toFixed(1) + '%' : '--';
        const winRate = bt.win_rate != null ? (parseFloat(bt.win_rate) * 100).toFixed(0) + '%' : '--';
        const retFormatted = retPct != null ? formatPnl(retPct, true) : { formatted: '--', colorClass: '' };
        const hasChart = bt.equity_curve && bt.equity_curve.length > 1;
        const cursor = hasChart ? 'cursor: pointer;' : '';

        // Main row
        let html = `
            <tr onclick="${hasChart ? `toggleEquityCurve(${idx})` : ''}" style="${cursor}" title="${hasChart ? 'Click to view equity curve' : ''}">
                <td>${timeAgo(createdAt)}</td>
                <td><span class="strategy-tag">${bt.engine || '--'}</span></td>
                <td><code>${label}</code></td>
                <td>${tickers}</td>
                <td><span class="pnl ${retFormatted.colorClass}">${retFormatted.formatted}</span></td>
                <td>${sharpe}</td>
                <td>${maxDD}</td>
                <td>${winRate}</td>
            </tr>`;

        // Expandable detail row (hidden by default)
        if (hasChart) {
            const sortino = bt.sortino_ratio != null ? parseFloat(bt.sortino_ratio).toFixed(2) : '--';
            const cagr = bt.cagr != null ? (parseFloat(bt.cagr) * 100).toFixed(1) + '%' : '--';
            const pf = bt.profit_factor != null ? parseFloat(bt.profit_factor).toFixed(2) : '--';
            const start = bt.starting_capital != null ? '$' + parseFloat(bt.starting_capital).toLocaleString() : '--';
            const end = bt.terminal_value != null ? '$' + parseFloat(bt.terminal_value).toLocaleString(undefined, {maximumFractionDigits: 2}) : '--';

            html += `
            <tr id="bt-detail-${idx}" class="bt-detail-row" style="display: none;">
                <td colspan="8">
                    <div class="bt-detail-panel">
                        <div class="bt-detail-metrics">
                            <div class="bt-metric"><span class="bt-metric-label">Sortino</span><span class="bt-metric-val">${sortino}</span></div>
                            <div class="bt-metric"><span class="bt-metric-label">CAGR</span><span class="bt-metric-val">${cagr}</span></div>
                            <div class="bt-metric"><span class="bt-metric-label">Profit Factor</span><span class="bt-metric-val">${pf}</span></div>
                            <div class="bt-metric"><span class="bt-metric-label">Start</span><span class="bt-metric-val">${start}</span></div>
                            <div class="bt-metric"><span class="bt-metric-label">End</span><span class="bt-metric-val">${end}</span></div>
                        </div>
                        <div class="bt-chart-container">
                            <canvas id="bt-chart-${idx}" width="800" height="200"></canvas>
                        </div>
                    </div>
                </td>
            </tr>`;
        }

        return html;
    }).join('');
}

// Toggle equity curve detail row
function toggleEquityCurve(idx) {
    const row = document.getElementById(`bt-detail-${idx}`);
    if (!row) return;

    if (row.style.display === 'none') {
        row.style.display = '';
        const canvas = document.getElementById(`bt-chart-${idx}`);
        if (canvas && window._backtestData && window._backtestData[idx]) {
            drawEquityCurve(canvas, window._backtestData[idx]);
        }
    } else {
        row.style.display = 'none';
    }
}

// Draw equity curve on a canvas
function drawEquityCurve(canvas, backtest) {
    const curve = backtest.equity_curve;
    if (!curve || curve.length < 2) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();

    // Size canvas to container
    canvas.width = rect.width * dpr;
    canvas.height = 200 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '200px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 200;
    const pad = { top: 20, right: 60, bottom: 30, left: 70 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    // Extract values
    const values = curve.map(p => p.v);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 1;
    const startVal = values[0];

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = '#12121a';
    ctx.fillRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#2a2a3a';
    ctx.lineWidth = 0.5;
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
        const y = pad.top + (plotH / gridLines) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();

        // Y-axis labels
        const val = maxVal - (range / gridLines) * i;
        ctx.fillStyle = '#606070';
        ctx.font = '11px JetBrains Mono, monospace';
        ctx.textAlign = 'right';
        ctx.fillText('$' + val.toLocaleString(undefined, {maximumFractionDigits: 0}), pad.left - 8, y + 4);
    }

    // Starting capital reference line
    if (startVal >= minVal && startVal <= maxVal) {
        const startY = pad.top + plotH - ((startVal - minVal) / range) * plotH;
        ctx.strokeStyle = '#606070';
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(pad.left, startY);
        ctx.lineTo(w - pad.right, startY);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // Determine color based on final return
    const finalVal = values[values.length - 1];
    const isProfit = finalVal >= startVal;
    const lineColor = isProfit ? '#00d26a' : '#ff4757';
    const fillColor = isProfit ? 'rgba(0, 210, 106, 0.08)' : 'rgba(255, 71, 87, 0.08)';

    // Draw area fill
    ctx.beginPath();
    ctx.moveTo(pad.left, pad.top + plotH);
    for (let i = 0; i < values.length; i++) {
        const x = pad.left + (i / (values.length - 1)) * plotW;
        const y = pad.top + plotH - ((values[i] - minVal) / range) * plotH;
        ctx.lineTo(x, y);
    }
    ctx.lineTo(pad.left + plotW, pad.top + plotH);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    for (let i = 0; i < values.length; i++) {
        const x = pad.left + (i / (values.length - 1)) * plotW;
        const y = pad.top + plotH - ((values[i] - minVal) / range) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // End value label
    const endX = pad.left + plotW;
    const endY = pad.top + plotH - ((finalVal - minVal) / range) * plotH;
    ctx.fillStyle = lineColor;
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText('$' + finalVal.toLocaleString(undefined, {maximumFractionDigits: 0}), endX + 6, endY + 4);

    // Title
    const retPct = ((finalVal - startVal) / startVal * 100).toFixed(1);
    const sign = retPct >= 0 ? '+' : '';
    ctx.fillStyle = '#a0a0b0';
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('Equity Curve', pad.left, pad.top - 6);

    ctx.fillStyle = lineColor;
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`${sign}${retPct}%`, w - pad.right, pad.top - 6);
}

// Fetch strategy adjustments from paper_strategy_adjustments table
async function fetchAdjustments() {
    try {
        return await supabaseQuery('paper_strategy_adjustments', {
            'select': '*',
            'order': 'created_at.desc',
            'limit': '20'
        });
    } catch (e) {
        console.warn('Adjustments not available:', e);
        return [];
    }
}

// Render adjustment history table
function renderAdjustments(adjustments) {
    const tbody = document.getElementById('adjustments-tbody');
    const countEl = document.getElementById('adjustments-count');
    if (!tbody || !countEl) return;

    const pending = adjustments.filter(a => a.status === 'pending').length;
    countEl.textContent = pending > 0 ? `${pending} pending` : adjustments.length;

    if (adjustments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No adjustments yet - tuner evaluates strategies daily</td></tr>';
        return;
    }

    tbody.innerHTML = adjustments.map(adj => {
        const createdAt = new Date(adj.created_at);

        // Format parameter change
        let oldFmt, newFmt;
        if (adj.parameter_name === 'min_volume') {
            oldFmt = '$' + (adj.old_value || 0).toLocaleString();
            newFmt = '$' + (adj.new_value || 0).toLocaleString();
        } else if (['expiry_hours', 'lookback_hours', 'min_score', 'entry_threshold_pct'].includes(adj.parameter_name)) {
            oldFmt = (adj.old_value || 0).toFixed(0);
            newFmt = (adj.new_value || 0).toFixed(0);
        } else {
            oldFmt = (adj.old_value || 0).toFixed(4);
            newFmt = (adj.new_value || 0).toFixed(4);
        }

        const isIncrease = adj.new_value > adj.old_value;
        const arrow = isIncrease ? '&uarr;' : '&darr;';
        const changeClass = isIncrease ? 'positive' : 'negative';

        // Status styling
        const statusMap = {
            'pending': '<span class="adj-status adj-pending">PENDING</span>',
            'approved': '<span class="adj-status adj-approved">APPROVED</span>',
            'applied': '<span class="adj-status adj-applied">APPLIED</span>',
            'reverted': '<span class="adj-status adj-reverted">REVERTED</span>',
        };
        const statusHtml = statusMap[adj.status] || adj.status;

        // 7d context
        const wr = adj.win_rate_7d != null ? (adj.win_rate_7d * 100).toFixed(0) + '%' : '--';
        const pnl = adj.avg_pnl_pct_7d != null ? (adj.avg_pnl_pct_7d >= 0 ? '+' : '') + adj.avg_pnl_pct_7d.toFixed(2) + '%' : '--';
        const sigs = adj.total_signals_7d != null ? adj.total_signals_7d : '--';

        return `
            <tr class="adj-row adj-row-${adj.status}">
                <td>${timeAgo(createdAt)}</td>
                <td><span class="strategy-tag">${adj.strategy_name}</span></td>
                <td><code>${adj.parameter_name}</code></td>
                <td>
                    <span class="adj-change">
                        ${oldFmt} <span class="pnl ${changeClass}">${arrow} ${newFmt}</span>
                    </span>
                </td>
                <td class="adj-reason">${adj.reason || '--'}</td>
                <td><span class="adj-context">WR ${wr} | P&L ${pnl} | ${sigs} sigs</span></td>
                <td>${statusHtml}</td>
            </tr>
        `;
    }).join('');
}

// Fetch enhanced metrics from paper_strategy_metrics table
async function fetchEnhancedMetrics() {
    try {
        return await supabaseQuery('paper_strategy_metrics', {
            'select': '*',
            'order': 'period_end.desc',
            'limit': '20'
        });
    } catch (e) {
        console.warn('Enhanced metrics not available:', e);
        return [];
    }
}

// Update enhanced analytics panel
function updateEnhancedAnalytics(metrics) {
    if (!metrics || metrics.length === 0) {
        return;
    }

    // Aggregate across strategies for the most recent period
    let totalWins = 0, totalLosses = 0, totalPnl = 0;
    const allReturns = [];

    metrics.forEach(m => {
        totalWins += (m.winning_trades || 0);
        totalLosses += (m.losing_trades || 0);
        totalPnl += (m.total_pnl_pct || 0);
        if (m.avg_pnl_pct) allReturns.push(m.avg_pnl_pct);
    });

    // Compute Sharpe approximation from available data
    if (allReturns.length > 0) {
        const mean = allReturns.reduce((a, b) => a + b, 0) / allReturns.length;
        const variance = allReturns.reduce((a, b) => a + (b - mean) ** 2, 0) / allReturns.length;
        const std = Math.sqrt(variance);
        const sharpe = std > 0 ? (mean / std * Math.sqrt(365)).toFixed(2) : 'N/A';

        const sharpeEl = document.getElementById('sharpe-ratio');
        if (sharpeEl) {
            sharpeEl.textContent = sharpe;
            const qualityEl = document.getElementById('sharpe-quality');
            if (qualityEl) {
                const s = parseFloat(sharpe);
                if (s > 2) qualityEl.textContent = 'Excellent';
                else if (s > 1) qualityEl.textContent = 'Good';
                else if (s > 0) qualityEl.textContent = 'Positive';
                else qualityEl.textContent = 'Negative';
            }
        }

        // Sortino (approximate using only negative returns as denominator)
        const negReturns = allReturns.filter(r => r < 0);
        const downVar = negReturns.length > 0
            ? negReturns.reduce((a, b) => a + b ** 2, 0) / negReturns.length
            : 0;
        const downStd = Math.sqrt(downVar);
        const sortino = downStd > 0 ? (mean / downStd * Math.sqrt(365)).toFixed(2) : 'N/A';
        const sortinoEl = document.getElementById('sortino-ratio');
        if (sortinoEl) {
            sortinoEl.textContent = sortino;
            const qualityEl = document.getElementById('sortino-quality');
            if (qualityEl) {
                const s = parseFloat(sortino);
                if (s > 3) qualityEl.textContent = 'Excellent';
                else if (s > 1.5) qualityEl.textContent = 'Good';
                else if (s > 0) qualityEl.textContent = 'Positive';
                else qualityEl.textContent = 'Negative';
            }
        }
    }

    // Max drawdown from metrics
    const maxLosses = metrics.map(m => m.max_loss_pct || 0);
    const maxDD = Math.min(...maxLosses);
    const ddEl = document.getElementById('max-drawdown');
    if (ddEl) {
        ddEl.textContent = `${maxDD.toFixed(2)}%`;
        ddEl.className = `metric-value ${maxDD < -5 ? 'negative' : maxDD < 0 ? '' : 'positive'}`;
        const qualityEl = document.getElementById('drawdown-quality');
        if (qualityEl) {
            if (maxDD > -2) qualityEl.textContent = 'Low risk';
            else if (maxDD > -5) qualityEl.textContent = 'Moderate';
            else qualityEl.textContent = 'High risk';
        }
    }

    // Profit factor
    const profitFactors = metrics.map(m => m.profit_factor || 0).filter(p => p > 0);
    const avgPF = profitFactors.length > 0
        ? (profitFactors.reduce((a, b) => a + b, 0) / profitFactors.length).toFixed(2)
        : 'N/A';
    const pfEl = document.getElementById('profit-factor');
    if (pfEl) {
        pfEl.textContent = avgPF;
        const qualityEl = document.getElementById('factor-quality');
        if (qualityEl) {
            const pf = parseFloat(avgPF);
            if (pf > 2) qualityEl.textContent = 'Strong edge';
            else if (pf > 1.5) qualityEl.textContent = 'Good edge';
            else if (pf > 1) qualityEl.textContent = 'Marginal';
            else qualityEl.textContent = 'No edge';
        }
    }
}

// Main refresh function
async function refreshDashboard() {
    try {
        console.log('Refreshing dashboard...');

        // Fetch all data in parallel
        const [activeSignals, recentRecs, recentOutcomes, enhancedMetrics, backtestResults, adjustments] = await Promise.all([
            fetchActiveSignals(),
            fetchRecentRecommendations(),
            fetchRecentOutcomes(),
            fetchEnhancedMetrics(),
            fetchBacktestResults(),
            fetchAdjustments()
        ]);

        console.log('Data fetched:', {
            active: activeSignals.length,
            recent: recentRecs.length,
            outcomes: recentOutcomes.length,
            enhanced: enhancedMetrics.length,
            backtests: backtestResults.length,
            adjustments: adjustments.length
        });

        // Update all sections
        updateOverviewMetrics(recentRecs, recentOutcomes);
        updateStrategyCards(recentRecs, recentOutcomes);
        renderActiveSignals(activeSignals);
        renderOutcomes(recentOutcomes);
        updateEnhancedAnalytics(enhancedMetrics);
        renderBacktestResults(backtestResults);
        renderAdjustments(adjustments);
        updateTimestamp();

        // Update status indicator
        document.querySelector('.status-dot').style.background = 'var(--accent-green)';
        document.querySelector('.status-text').textContent = 'Live';

    } catch (error) {
        console.error('Error refreshing dashboard:', error);

        // Update status indicator to show error
        document.querySelector('.status-dot').style.background = 'var(--accent-red)';
        document.querySelector('.status-text').textContent = 'Error';
    }
}

// Initialize dashboard
async function init() {
    console.log('Initializing Paper Trading Dashboard...');

    // Initial load
    await refreshDashboard();

    // Set up auto-refresh
    setInterval(refreshDashboard, REFRESH_INTERVAL);

    console.log(`Dashboard initialized. Refreshing every ${REFRESH_INTERVAL / 1000}s`);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
