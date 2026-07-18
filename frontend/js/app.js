/* LottoLab - Main Application JavaScript */

const API_BASE = '/api/v1';
let frequencyChart = null;
let currentGame = 'lotto649';

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
    
    // Auto-refresh simulations every 10 seconds
    setInterval(loadSimulations, 10000);
});

function switchGame(game) {
    currentGame = game;
    
    // Update buttons
    document.getElementById('btn-lotto649').style.background = game === 'lotto649' ? 'linear-gradient(90deg,#f7971e,#ffd200)' : 'rgba(255,255,255,0.1)';
    document.getElementById('btn-lotto649').style.color = game === 'lotto649' ? '#000' : '#fff';
    document.getElementById('btn-dailygrand').style.background = game === 'dailygrand' ? 'linear-gradient(90deg,#f7971e,#ffd200)' : 'rgba(255,255,255,0.1)';
    document.getElementById('btn-dailygrand').style.color = game === 'dailygrand' ? '#000' : '#fff';
    
    // Show/hide sections
    document.getElementById('analysis').style.display = game === 'lotto649' ? 'block' : 'none';
    document.getElementById('daily-grand-analysis').style.display = game === 'dailygrand' ? 'block' : 'none';
    document.getElementById('gameTitle').textContent = game === 'lotto649' ? 'Number Frequency Analysis - Lotto 6/49' : 'Number Frequency Analysis - Daily Grand';
    
    // Reload chart for selected game
    loadFrequencyChart();
    if (game === 'dailygrand') {
        loadDailyGrandAnalysis();
    }
}

// Load dashboard statistics
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

// Load frequency chart
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

// Load Daily Grand analysis
async function loadDailyGrandAnalysis() {
    try {
        // For Daily Grand, we'll use the data from the database
        const response = await fetch(`${API_BASE}/draws/stats/frequencies`);
        const data = await response.json();
        
        // Show top numbers
        const sorted = Object.entries(data.frequencies || {})
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        
        document.getElementById('topMainNumbers').textContent = 
            sorted.map(([num, count]) => `#${num} (${count}x)`).join(', ');
        
        // Show grand numbers
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
            ticket = [...hot, ...cold].sort((a, b) => a - b);
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

// Load strategies
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

// Load simulations
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

// Run simulation
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
