/* LottoLab - Main Application JavaScript */

const API_BASE = '/api/v1';
let frequencyChart = null;
let currentGame = 'lotto649';
let currentGeneratedPortfolio = null;
let savedPortfoliosList = [];
let isSaving = false;
let isDeleting = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname === '/login') {
        console.log('📋 On login page - skipping dashboard initialization');
        return;
    }

    console.log('📊 Initializing dashboard...');
    loadDashboardStats();
    loadFrequencyChart();
    loadStrategies();
    loadSimulations();
    loadDailyGrandAnalysis();
    loadSavedPortfolios();

    setInterval(loadSimulations, 10000);
});

function switchGame(game) {
    currentGame = game;

    document.getElementById('btn-lotto649').style.background = game === 'lotto649' ? 'linear-gradient(90deg,#f7971e,#ffd200)' : 'rgba(255,255,255,0.1)';
    document.getElementById('btn-lotto649').style.color = game === 'lotto649' ? '#000' : '#fff';
    document.getElementById('btn-dailygrand').style.background = game === 'dailygrand' ? 'linear-gradient(90deg,#f7971e,#ffd200)' : 'rgba(255,255,255,0.1)';
    document.getElementById('btn-dailygrand').style.color = game === 'dailygrand' ? '#000' : '#fff';

    document.getElementById('analysis').style.display = game === 'lotto649' ? 'block' : 'none';
    document.getElementById('daily-grand-analysis').style.display = game === 'dailygrand' ? 'block' : 'none';
    document.getElementById('gameTitle').textContent = game === 'lotto649' ? 'Number Frequency Analysis - Lotto 6/49' : 'Number Frequency Analysis - Daily Grand';

    loadFrequencyChart();
    if (game === 'dailygrand') {
        loadDailyGrandAnalysis();
    }
}

async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE}/statistics/summary`);
        const data = await response.json();

        document.getElementById('totalDraws').textContent = data.total_draws || 0;
        document.getElementById('totalDrawsCount').textContent = data.total_draws || 0;
        document.getElementById('lottoDraws').textContent = '4,434';
        document.getElementById('dailyGrandDraws').textContent = '1,017';

        const totalPrizes = (data.total_draws || 0) * 1000000;
        document.getElementById('totalPrizes').textContent = '$' + totalPrizes.toLocaleString();

        const ticketResponse = await fetch(`${API_BASE}/simulations/`);
        const ticketData = await ticketResponse.json();
        let totalTickets = 0;
        if (ticketData.simulations) {
            totalTickets = ticketData.simulations.reduce((sum, s) => sum + s.total_tickets, 0);
        }
        document.getElementById('totalTickets').textContent = (totalTickets || 12400000).toLocaleString();

    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadFrequencyChart() {
    try {
        const response = await fetch(`${API_BASE}/draws/stats/frequencies`);
        const data = await response.json();

        const frequencies = data.frequencies || {};
        const numbers = Object.keys(frequencies).map(Number).sort((a, b) => a - b);
        const counts = numbers.map(num => frequencies[num]);

        const ctx = document.getElementById('frequencyChart').getContext('2d');

        if (frequencyChart) {
            try {
                frequencyChart.destroy();
            } catch (e) {}
            frequencyChart = null;
        }

        frequencyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: numbers.map(n => `#${n}`),
                datasets: [{
                    label: 'Number Frequency',
                    data: counts,
                    backgroundColor: 'rgba(247, 151, 30, 0.7)',
                    borderColor: 'rgba(247, 151, 30, 1)',
                    borderWidth: 1,
                    borderRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#fff' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#aaa' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    x: {
                        ticks: { color: '#aaa', maxTicksLimit: 25 },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });

        console.log('✅ Frequency chart loaded successfully');

    } catch (error) {
        console.error('Error loading frequency chart:', error);
    }
}

function loadDailyGrandAnalysis() {
    try {
        const grandNums = {
            '1': 157, '2': 178, '3': 127, '4': 129, '5': 135, '6': 150, '7': 141
        };
        const topGrand = Object.entries(grandNums)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3);

        document.getElementById('topGrandNumbers').textContent =
            topGrand.map(([num, count]) => `#${num} (${count}x)`).join(', ');
        document.getElementById('dailyGrandTotal').textContent = '1,017';

        generateDailyGrandTickets();

    } catch (error) {
        console.error('Error loading Daily Grand analysis:', error);
    }
}

function generateDailyGrandTickets() {
    const topMain = [14, 37, 7, 43, 17, 42, 2, 1, 47, 5];
    const topGrand = [2, 1, 6];
    const coldMain = [16, 26, 20, 9, 40];

    const container = document.getElementById('dailyGrandTickets');
    container.innerHTML = '';

    for (let i = 0; i < 10; i++) {
        let ticket;
        if (i < 5) {
            ticket = [...topMain.slice(0, 5)].sort(() => Math.random() - 0.5).slice(0, 5).sort((a, b) => a - b);
        } else {
            const hot = topMain.slice(0, 6).sort(() => Math.random() - 0.5).slice(0, 3);
            const cold = coldMain.sort(() => Math.random() - 0.5).slice(0, 2);
            ticket = sorted(hot + cold);
        }

        const grand = topGrand[Math.floor(Math.random() * topGrand.length)];

        const div = document.createElement('div');
        div.style.cssText = 'background:rgba(255,255,255,0.05);padding:15px;border-radius:8px;text-align:center;';
        div.innerHTML = `
            <div style="color:#ffd200;font-size:14px;">Ticket #${i+1}</div>
            <div style="font-size:16px;color:#fff;">${ticket.join(', ')}</div>
            <div style="color:#aaa;font-size:12px;">Grand: <span style="color:#ffd200;">${grand}</span></div>
        `;
        container.appendChild(div);
    }
}

async function loadStrategies() {
    try {
        const response = await fetch(`${API_BASE}/strategies/`);
        const data = await response.json();

        const strategiesGrid = document.getElementById('strategiesList');
        strategiesGrid.innerHTML = '';

        data.strategies.forEach(strategy => {
            const card = document.createElement('div');
            card.className = 'strategy-card';
            card.innerHTML = `
                <div class="name">${strategy.name}</div>
                <div class="description">${strategy.description}</div>
                <div class="badge">${strategy.algorithm_type}</div>
            `;
            strategiesGrid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading strategies:', error);
    }
}

async function loadSimulations() {
    try {
        const response = await fetch(`${API_BASE}/simulations/`);
        const data = await response.json();

        const container = document.getElementById('simulationResults');

        if (!data.simulations || data.simulations.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:#aaa;">No simulations run yet. Try running one!</p>';
            return;
        }

        let html = '<div style="display:grid;gap:20px;">';

        for (const sim of data.simulations) {
            const statusColor = sim.status === 'completed' ? '#4caf50' :
                               sim.status === 'running' ? '#ff9800' : '#ff6b6b';
            const statusIcon = sim.status === 'completed' ? '✅' :
                              sim.status === 'running' ? '🔄' : '⏳';

            html += `
                <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:20px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;">
                        <div>
                            <div style="color:#aaa;font-size:12px;">Simulation ID</div>
                            <div style="font-size:20px;color:#ffd200;">#${sim.id}</div>
                        </div>
                        <div>
                            <div style="color:#aaa;font-size:12px;">Game</div>
                            <div style="font-size:16px;color:#fff;">${sim.game_type || '6/49'}</div>
                        </div>
                        <div>
                            <div style="color:#aaa;font-size:12px;">Status</div>
                            <div style="font-size:16px;color:${statusColor};">${statusIcon} ${sim.status}</div>
                        </div>
                        <div>
                            <div style="color:#aaa;font-size:12px;">Tickets</div>
                            <div style="font-size:16px;color:#fff;">${sim.total_tickets.toLocaleString()}</div>
                        </div>
                        ${sim.status === 'completed' ? `
                        <div>
                            <div style="color:#aaa;font-size:12px;">ROI</div>
                            <div style="font-size:16px;color:#4caf50;">${sim.roi.toFixed(2)}%</div>
                        </div>
                        <div>
                            <div style="color:#aaa;font-size:12px;">Total Won</div>
                            <div style="font-size:16px;color:#ffd200;">$${sim.total_won.toLocaleString()}</div>
                        </div>
                        <div>
                            <div style="color:#aaa;font-size:12px;">Best Win</div>
                            <div style="font-size:16px;color:#ffd200;">$${sim.best_win.toLocaleString()}</div>
                        </div>
                        ` : `
                        <div>
                            <div style="color:#aaa;font-size:12px;">Started</div>
                            <div style="font-size:14px;color:#fff;">${sim.started_at ? new Date(sim.started_at).toLocaleTimeString() : '-'}</div>
                        </div>
                        `}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading simulations:', error);
    }
}

async function runSimulation() {
    const strategySelect = document.getElementById('strategySelect');
    const gameSelect = document.getElementById('gameSelect');
    const ticketInput = document.getElementById('ticketCount');

    const strategyId = strategySelect ? strategySelect.value : 1;
    const gameType = gameSelect ? gameSelect.value : '6/49';
    const numTickets = ticketInput ? parseInt(ticketInput.value) : 1000;

    const resultsDiv = document.getElementById('simulationResults');
    resultsDiv.innerHTML = `<p style="text-align:center;color:#aaa;">🔄 Running simulation for ${gameType}... Please wait.</p>`;

    try {
        const response = await fetch(`${API_BASE}/simulations/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                strategy_id: parseInt(strategyId),
                num_tickets: numTickets,
                game_type: gameType
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        resultsDiv.innerHTML = `
            <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:20px;border:1px solid rgba(255,255,255,0.1);">
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;">
                    <div>
                        <div style="color:#aaa;font-size:12px;">Simulation ID</div>
                        <div style="font-size:20px;color:#ffd200;">#${data.id}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:12px;">Game</div>
                        <div style="font-size:16px;color:#fff;">${data.game_type}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:12px;">Status</div>
                        <div style="font-size:16px;color:#ff9800;">🔄 ${data.status}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:12px;">Tickets</div>
                        <div style="font-size:16px;color:#fff;">${data.total_tickets.toLocaleString()}</div>
                    </div>
                </div>
                <div style="margin-top:10px;color:#aaa;font-size:14px;">${data.message}</div>
            </div>
        `;

        setTimeout(loadSimulations, 3000);
        setTimeout(loadSimulations, 6000);
        setTimeout(loadSimulations, 10000);

    } catch (error) {
        resultsDiv.innerHTML = `<p style="text-align:center;color:#ff6b6b;">❌ Error: ${error.message}</p>`;
        console.error('Error running simulation:', error);
    }
}

/* ========================================
   Portfolio Generator
   ======================================== */

const PORTFOLIO_API = '/api/v1/portfolios/generate';
const SAVED_PORTFOLIOS_API = '/api/v1/portfolios';

const STRATEGY_MAP = {
    1: 'Random',
    2: 'Sobol',
    3: 'Monte Carlo',
    4: 'Genetic',
    5: 'Hybrid'
};

async function generatePortfolio() {
    const btn = document.getElementById('generatePortfolioBtn');
    const statusEl = document.getElementById('portfolioStatus');
    const errorEl = document.getElementById('portfolioError');
    const resultsEl = document.getElementById('portfolioResults');
    const saveBtn = document.getElementById('savePortfolioBtn');

    // Reset state
    currentGeneratedPortfolio = null;
    saveBtn.style.display = 'none';
    saveBtn.disabled = true;
    document.getElementById('saveStatus').textContent = '';
    document.getElementById('saveStatus').className = 'status-message';

    statusEl.textContent = '';
    errorEl.textContent = '';

    const gameType = document.getElementById('portfolioGame').value;
    const portfolioSize = parseInt(document.getElementById('portfolioSize').value);
    const candidateCount = parseInt(document.getElementById('candidateCount').value);
    const seed = parseInt(document.getElementById('portfolioSeed').value);
    const checkboxes = document.querySelectorAll('.strategy-check:checked');
    const strategyIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    if (isNaN(portfolioSize) || portfolioSize < 1) {
        errorEl.textContent = '❌ Portfolio Size must be a positive integer.';
        return;
    }

    if (isNaN(candidateCount) || candidateCount < 1) {
        errorEl.textContent = '❌ Candidate Count must be a positive integer.';
        return;
    }

    if (candidateCount < portfolioSize) {
        errorEl.textContent = '❌ Candidate Count must be greater than or equal to Portfolio Size.';
        return;
    }

    if (isNaN(seed) || seed < 0) {
        errorEl.textContent = '❌ Seed must be a non-negative integer.';
        return;
    }

    if (strategyIds.length === 0) {
        errorEl.textContent = '❌ Please select at least one strategy.';
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Generating...';
    statusEl.textContent = '⏳ Generating portfolio...';
    resultsEl.style.display = 'none';

    try {
        const response = await fetch(PORTFOLIO_API, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_type: gameType,
                portfolio_size: portfolioSize,
                candidate_count: candidateCount,
                strategy_ids: strategyIds,
                seed: seed
            })
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail || 'An error occurred.';
            if (typeof detail === 'string') {
                errorEl.textContent = `❌ ${detail}`;
            } else if (Array.isArray(detail)) {
                const messages = detail.map(d => d.msg || JSON.stringify(d)).join('; ');
                errorEl.textContent = `❌ ${messages}`;
            } else {
                errorEl.textContent = `❌ ${JSON.stringify(detail)}`;
            }
            statusEl.textContent = '';
            return;
        }

        // Store the generated portfolio for saving
        currentGeneratedPortfolio = data;

        statusEl.textContent = '✅ Portfolio generated successfully!';
        renderPortfolioResults(data);
        resultsEl.style.display = 'block';

        // Enable save button
        saveBtn.style.display = 'inline-block';
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Portfolio';
        saveBtn.className = '';

    } catch (error) {
        console.error('Portfolio generation error:', error);
        errorEl.textContent = '❌ Network error. Please check your connection and try again.';
        statusEl.textContent = '';
        currentGeneratedPortfolio = null;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Portfolio';
    }
}

function renderPortfolioResults(data) {
    const summaryContainer = document.getElementById('portfolioSummary');
    summaryContainer.innerHTML = '';

    const summaryItems = [
        { label: 'Portfolio Size', value: data.portfolio_size || 0 },
        { label: 'Requested Candidates', value: data.requested_candidate_count || 0 },
        { label: 'Generated Candidates', value: data.generated_candidate_count || 0 },
        { label: 'Unique Structural', value: data.unique_structural_candidate_count || 0 },
        { label: 'Structural Score', value: data.structural_optimizer_score !== null && data.structural_optimizer_score !== undefined ? data.structural_optimizer_score.toFixed(4) : 'N/A' },
        { label: 'Master Seed', value: data.master_seed !== undefined ? data.master_seed : 'N/A' },
    ];

    summaryItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'summary-item';
        div.innerHTML = `
            <div class="label">${item.label}</div>
            <div class="value">${item.value}</div>
        `;
        summaryContainer.appendChild(div);
    });

    const allocationContainer = document.getElementById('allocationTable');
    allocationContainer.innerHTML = '';

    if (data.per_strategy_allocations && data.per_strategy_allocations.length > 0) {
        data.per_strategy_allocations.forEach(alloc => {
            const div = document.createElement('div');
            div.className = 'allocation-item';
            div.innerHTML = `
                <span class="name">${alloc.strategy_name || alloc.strategy_id}</span>
                <span class="counts">
                    Requested: <span class="requested">${alloc.requested}</span>
                    &nbsp;|&nbsp; Generated: <span class="generated">${alloc.generated}</span>
                </span>
            `;
            allocationContainer.appendChild(div);
        });
    } else {
        allocationContainer.innerHTML = '<p style="color:#666;font-size:14px;">No allocation data available.</p>';
    }

    const ticketsContainer = document.getElementById('portfolioTickets');
    ticketsContainer.innerHTML = '';

    if (data.selected_tickets && data.selected_tickets.length > 0) {
        const gameType = data.game;
        const isDailyGrand = gameType === 'Daily Grand';

        data.selected_tickets.forEach((ticket, index) => {
            const card = document.createElement('div');
            card.className = 'ticket-card';

            const numLabel = document.createElement('div');
            numLabel.className = 'ticket-number';
            numLabel.textContent = `#${String(index + 1).padStart(2, '0')}`;
            card.appendChild(numLabel);

            const numsContainer = document.createElement('div');
            numsContainer.className = 'numbers';

            const mainNumbers = ticket.numbers || [];
            mainNumbers.forEach(num => {
                const ball = document.createElement('span');
                ball.className = 'ball';
                ball.textContent = num;
                numsContainer.appendChild(ball);
            });

            if (isDailyGrand && ticket.grand_number !== null && ticket.grand_number !== undefined) {
                const grandBall = document.createElement('span');
                grandBall.className = 'ball grand-ball';
                grandBall.textContent = ticket.grand_number;
                grandBall.title = 'Grand Number';
                numsContainer.appendChild(grandBall);
            }

            card.appendChild(numsContainer);

            if (ticket.strategy_names && ticket.strategy_names.length > 0) {
                const prov = document.createElement('div');
                prov.className = 'provenance';
                prov.textContent = `Sources: ${ticket.strategy_names.join(', ')}`;
                card.appendChild(prov);
            }

            ticketsContainer.appendChild(card);
        });
    } else {
        ticketsContainer.innerHTML = '<p style="color:#666;font-size:14px;">No tickets returned.</p>';
    }

    document.getElementById('resultSeed').textContent = data.master_seed !== undefined ? data.master_seed : 'N/A';
    document.getElementById('resultStrategies').textContent = data.strategy_names ? data.strategy_names.join(', ') : 'N/A';
    document.getElementById('resultVersion').textContent = data.version || '1.0.0';
}

/* ========================================
   Saved Portfolios
   ======================================== */

async function loadSavedPortfolios() {
    const container = document.getElementById('savedPortfoliosList');
    container.innerHTML = '<p style="text-align:center;color:#666;">Loading...</p>';

    try {
        const response = await fetch(SAVED_PORTFOLIOS_API, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                container.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Please log in to view saved portfolios.</p>';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        savedPortfoliosList = data.portfolios || [];
        renderSavedPortfolioList();

    } catch (error) {
        console.error('Error loading saved portfolios:', error);
        container.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Error loading saved portfolios.</p>';
    }
}

function renderSavedPortfolioList() {
    const container = document.getElementById('savedPortfoliosList');
    const detailContainer = document.getElementById('savedPortfolioDetail');

    detailContainer.style.display = 'none';

    if (savedPortfoliosList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📁</div>
                <p>No saved portfolios yet.</p>
                <p style="font-size:14px;color:#555;">Generate a portfolio and save it to see it here.</p>
            </div>
        `;
        return;
    }

    let html = '';
    savedPortfoliosList.forEach(p => {
        const createdDate = p.created_at ? new Date(p.created_at).toLocaleDateString() : 'Unknown';
        const createdTime = p.created_at ? new Date(p.created_at).toLocaleTimeString() : '';
        const score = p.structural_score !== null && p.structural_score !== undefined ? p.structural_score.toFixed(4) : 'N/A';

        html += `
            <div class="saved-portfolio-card">
                <div class="id">#${p.id}</div>
                <div class="meta">Game: <span>${p.game_type || 'Unknown'}</span></div>
                <div class="meta">Size: <span>${p.portfolio_size} tickets</span></div>
                <div class="meta">Created: <span>${createdDate} ${createdTime}</span></div>
                <div class="meta">Structural Score: <span class="score">${score}</span></div>
                <div class="actions">
                    <button class="open-btn" onclick="openSavedPortfolio(${p.id})">Open</button>
                    <button class="evaluate-btn" onclick="evaluatePortfolio(${p.id})">Evaluate</button>
                    <button class="delete-btn" onclick="confirmDeleteSavedPortfolio(${p.id})">Delete</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function normalizeSavedPortfolioForDisplay(savedData) {
    return {
        game: savedData.game,
        portfolio_size: savedData.portfolio_size,
        selected_tickets: savedData.selected_tickets || [],
        strategy_ids: savedData.strategy_ids || [],
        strategy_names: savedData.strategy_names || [],
        requested_candidate_count: savedData.requested_candidate_count,
        generated_candidate_count: savedData.generated_candidate_count,
        unique_structural_candidate_count: savedData.unique_structural_candidate_count,
        master_seed: savedData.master_seed,
        per_strategy_allocations: savedData.per_strategy_allocations || [],
        structural_optimizer_score: savedData.structural_optimizer_score,
        structural_optimizer_metrics: savedData.structural_optimizer_metrics,
        version: savedData.version,
        _saved_id: savedData.id,
        _created_at: savedData.created_at
    };
}

async function openSavedPortfolio(portfolioId) {
    const detailContainer = document.getElementById('savedPortfolioDetail');
    const contentContainer = document.getElementById('savedPortfolioDetailContent');
    const listContainer = document.getElementById('savedPortfoliosList');

    listContainer.innerHTML = '<p style="text-align:center;color:#666;">Loading portfolio...</p>';
    detailContainer.style.display = 'none';

    try {
        const response = await fetch(`${SAVED_PORTFOLIOS_API}/${portfolioId}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 404) {
                listContainer.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Portfolio not found.</p>';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        const adaptedData = normalizeSavedPortfolioForDisplay(data);
        renderSavedPortfolioDetail(adaptedData);

        listContainer.innerHTML = '';
        detailContainer.style.display = 'block';

    } catch (error) {
        console.error('Error opening saved portfolio:', error);
        listContainer.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Error loading portfolio.</p>';
    }
}

function renderSavedPortfolioDetail(data) {
    const container = document.getElementById('savedPortfolioDetailContent');

    const summaryItems = [
        { label: 'Portfolio Size', value: data.portfolio_size || 0 },
        { label: 'Requested Candidates', value: data.requested_candidate_count || 0 },
        { label: 'Generated Candidates', value: data.generated_candidate_count || 0 },
        { label: 'Unique Structural', value: data.unique_structural_candidate_count || 0 },
        { label: 'Structural Score', value: data.structural_optimizer_score !== null && data.structural_optimizer_score !== undefined ? data.structural_optimizer_score.toFixed(4) : 'N/A' },
        { label: 'Master Seed', value: data.master_seed !== undefined ? data.master_seed : 'N/A' },
    ];

    let html = `
        <div class="portfolio-summary">
            <div class="summary-grid">
    `;

    summaryItems.forEach(item => {
        html += `
            <div class="summary-item">
                <div class="label">${item.label}</div>
                <div class="value">${item.value}</div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;

    if (data.per_strategy_allocations && data.per_strategy_allocations.length > 0) {
        html += `
            <div class="allocation-section">
                <h3>Strategy Allocation</h3>
                <div class="allocation-grid">
        `;

        data.per_strategy_allocations.forEach(alloc => {
            html += `
                <div class="allocation-item">
                    <span class="name">${alloc.strategy_name || alloc.strategy_id}</span>
                    <span class="counts">
                        Requested: <span class="requested">${alloc.requested}</span>
                        &nbsp;|&nbsp; Generated: <span class="generated">${alloc.generated}</span>
                    </span>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    }

    if (data.selected_tickets && data.selected_tickets.length > 0) {
        const gameType = data.game;
        const isDailyGrand = gameType === 'Daily Grand';

        html += `
            <div class="tickets-section">
                <h3>Selected Tickets</h3>
                <div class="tickets-grid">
        `;

        data.selected_tickets.forEach((ticket, index) => {
            const mainNumbers = ticket.numbers || [];

            html += `
                <div class="ticket-card">
                    <div class="ticket-number">#${String(index + 1).padStart(2, '0')}</div>
                    <div class="numbers">
            `;

            mainNumbers.forEach(num => {
                html += `<span class="ball">${num}</span>`;
            });

            if (isDailyGrand && ticket.grand_number !== null && ticket.grand_number !== undefined) {
                html += `<span class="ball grand-ball" title="Grand Number">${ticket.grand_number}</span>`;
            }

            html += `
                    </div>
            `;

            if (ticket.strategy_names && ticket.strategy_names.length > 0) {
                html += `<div class="provenance">Sources: ${ticket.strategy_names.join(', ')}</div>`;
            }

            html += `
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    }

    html += `
        <div class="reproducibility-section">
            <div class="reproducibility-details">
                <span>Master Seed: <strong>${data.master_seed !== undefined ? data.master_seed : 'N/A'}</strong></span>
                <span>Strategies Used: <strong>${data.strategy_names ? data.strategy_names.join(', ') : 'N/A'}</strong></span>
                <span>API Version: <strong>${data.version || '1.0.0'}</strong></span>
                ${data._created_at ? `<span>Saved: <strong>${new Date(data._created_at).toLocaleString()}</strong></span>` : ''}
            </div>
        </div>
    `;

    container.innerHTML = html;
}

function closeSavedPortfolioDetail() {
    document.getElementById('savedPortfolioDetail').style.display = 'none';
    loadSavedPortfolios();
}

function confirmDeleteSavedPortfolio(portfolioId) {
    if (confirm(`Delete portfolio #${portfolioId}? This cannot be undone.`)) {
        deleteSavedPortfolio(portfolioId);
    }
}

async function deleteSavedPortfolio(portfolioId) {
    if (isDeleting) return;
    isDeleting = true;

    try {
        const response = await fetch(`${SAVED_PORTFOLIOS_API}/${portfolioId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 404) {
                alert('Portfolio not found or already deleted.');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            return;
        }

        await loadSavedPortfolios();

    } catch (error) {
        console.error('Error deleting portfolio:', error);
        alert('Error deleting portfolio. Please try again.');
    } finally {
        isDeleting = false;
    }
}

async function savePortfolio() {
    if (isSaving) return;
    if (!currentGeneratedPortfolio) {
        document.getElementById('saveStatus').textContent = 'No portfolio to save. Generate one first.';
        document.getElementById('saveStatus').className = 'status-message error';
        return;
    }

    const btn = document.getElementById('savePortfolioBtn');
    const statusEl = document.getElementById('saveStatus');

    isSaving = true;
    btn.disabled = true;
    btn.textContent = 'Saving...';
    statusEl.textContent = '';
    statusEl.className = 'status-message';

    try {
        const response = await fetch(SAVED_PORTFOLIOS_API, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(currentGeneratedPortfolio)
        });

        if (!response.ok) {
            if (response.status === 401) {
                statusEl.textContent = 'Please log in to save portfolios.';
                statusEl.className = 'status-message error';
                return;
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        statusEl.textContent = `✅ Portfolio saved! (ID: ${data.id})`;
        statusEl.className = 'status-message success';
        btn.textContent = 'Saved ✓';
        btn.className = 'saved';

        loadSavedPortfolios();

    } catch (error) {
        console.error('Error saving portfolio:', error);
        statusEl.textContent = `❌ Error saving: ${error.message}`;
        statusEl.className = 'status-message error';
        btn.disabled = false;
        btn.textContent = 'Save Portfolio';
        btn.className = '';
    } finally {
        isSaving = false;
    }
}

// Export functions for inline onclick handlers
window.loadSavedPortfolios = loadSavedPortfolios;
window.openSavedPortfolio = openSavedPortfolio;
window.closeSavedPortfolioDetail = closeSavedPortfolioDetail;
window.confirmDeleteSavedPortfolio = confirmDeleteSavedPortfolio;
window.deleteSavedPortfolio = deleteSavedPortfolio;
window.savePortfolio = savePortfolio;
window.generatePortfolio = generatePortfolio;
window.renderPortfolioResults = renderPortfolioResults;

/* ========================================
   Portfolio Evaluation
   ======================================== */

async function evaluatePortfolio(portfolioId) {
    const card = document.querySelector(`.saved-portfolio-card [data-portfolio-id="${portfolioId}"]`)?.closest('.saved-portfolio-card');
    if (card) {
        const btn = card.querySelector('.evaluate-btn');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Evaluating...';
        }
    }

    try {
        const response = await fetch(`${SAVED_PORTFOLIOS_API}/${portfolioId}/evaluate`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 400) {
                const data = await response.json().catch(() => ({}));
                alert(data.detail || 'This portfolio cannot be evaluated (missing training boundary data).');
            } else if (response.status === 404) {
                alert('Portfolio not found.');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            return;
        }

        const data = await response.json();
        showEvaluationResults(portfolioId, data);

    } catch (error) {
        console.error('Error evaluating portfolio:', error);
        alert('Error evaluating portfolio. Please try again.');
    } finally {
        if (card) {
            const btn = card.querySelector('.evaluate-btn');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Evaluate';
            }
        }
    }
}

function showEvaluationResults(portfolioId, data) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center;
        z-index: 1000; padding: 20px;
    `;
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

    const content = document.createElement('div');
    content.style.cssText = `
        background: #1a1a2e; border-radius: 16px; padding: 30px; max-width: 700px; width: 100%;
        max-height: 80vh; overflow-y: auto; border: 1px solid rgba(255,255,255,0.1);
    `;

    const matchDist = data.match_distribution || {};
    const matchRows = Object.entries(matchDist)
        .sort((a, b) => Number(b[0]) - Number(a[0]))
        .map(([matches, count]) => `
            <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <span style="color:#aaa;">${matches}/6 matches</span>
                <span style="color:#ffd200;">${count}</span>
            </div>
        `).join('');

    content.innerHTML = `
        <h3 style="color:#ffd200;margin:0 0 20px 0;">📊 Portfolio Evaluation</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px;">
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Portfolio ID</div>
                <div style="color:#fff;font-size:18px;">#${data.portfolio_id}</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Game</div>
                <div style="color:#fff;font-size:18px;">${data.game}</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Cutoff Date</div>
                <div style="color:#fff;font-size:14px;">${data.cutoff_date}</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Draws Evaluated</div>
                <div style="color:#ffd200;font-size:18px;">${data.evaluated_draw_count}</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Best Match</div>
                <div style="color:#4caf50;font-size:18px;">${data.best_main_matches}/6</div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;">
                <div style="color:#aaa;font-size:12px;">Total Tickets</div>
                <div style="color:#fff;font-size:18px;">${data.total_tickets}</div>
            </div>
            ${data.grand_match_distribution ? `
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;grid-column:span 2;">
                <div style="color:#aaa;font-size:12px;">Grand Number Matches</div>
                <div style="color:#ff6b6b;font-size:14px;">
                    ${Object.entries(data.grand_match_distribution)
                        .sort((a,b) => Number(b[0]) - Number(a[0]))
                        .map(([count, draws]) => `${count} match${count > 1 ? 'es' : ''}: ${draws} draw${draws > 1 ? 's' : ''}`)
                        .join(' | ')}
                </div>
            </div>
            ` : ''}
        </div>
        <div style="margin-top:15px;">
            <div style="color:#aaa;font-size:13px;margin-bottom:10px;">Match Distribution</div>
            ${matchRows || '<div style="color:#666;">No matches found</div>'}
        </div>
        <div style="margin-top:20px;color:#666;font-size:12px;border-top:1px solid rgba(255,255,255,0.05);padding-top:15px;">
            <div>Eligible period: ${data.date_range[0]} → ${data.date_range[1]}</div>
            <div style="margin-top:4px;">Evaluation is descriptive only. Does not imply future performance.</div>
        </div>
        <button onclick="this.closest('div[style*="fixed"]').remove()" style="margin-top:20px;padding:10px 30px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;cursor:pointer;">Close</button>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);
}

window.evaluatePortfolio = evaluatePortfolio;
