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

// Main refresh function
async function refreshDashboard() {
    try {
        console.log('Refreshing dashboard...');

        // Fetch all data in parallel
        const [activeSignals, recentRecs, recentOutcomes] = await Promise.all([
            fetchActiveSignals(),
            fetchRecentRecommendations(),
            fetchRecentOutcomes()
        ]);

        console.log('Data fetched:', {
            active: activeSignals.length,
            recent: recentRecs.length,
            outcomes: recentOutcomes.length
        });

        // Update all sections
        updateOverviewMetrics(recentRecs, recentOutcomes);
        updateStrategyCards(recentRecs, recentOutcomes);
        renderActiveSignals(activeSignals);
        renderOutcomes(recentOutcomes);
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
