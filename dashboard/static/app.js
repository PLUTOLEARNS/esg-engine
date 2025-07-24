/**
 * ESG Portfolio Analytics Dashboard - Frontend JavaScript
 * Handles search, analysis, theme switching, and data visualization
 */

class ESGDashboard {
    constructor() {
        this.currentTheme = 'dark'; // Default to dark theme
        this.searchTimeout = null;
        this.currentAnalysis = null;
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupTheme();
        this.setupCharts();
    }
    
    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        
        searchInput.addEventListener('input', (e) => this.handleSearchInput(e));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        searchBtn.addEventListener('click', () => this.performSearch());
        
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        themeToggle.addEventListener('click', () => this.toggleTheme());
        
        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#search-input') && !e.target.closest('#search-suggestions')) {
                this.hideSuggestions();
            }
        });
    }
    
    setupTheme() {
        // Set initial theme (dark by default)
        document.body.classList.remove('light-theme');
        this.updateThemeText();
    }
    
    toggleTheme() {
        const body = document.body;
        const themeText = document.getElementById('theme-text');
        
        if (body.classList.contains('light-theme')) {
            body.classList.remove('light-theme');
            this.currentTheme = 'dark';
        } else {
            body.classList.add('light-theme');
            this.currentTheme = 'light';
        }
        
        this.updateThemeText();
        this.updateChartThemes();
    }
    
    updateThemeText() {
        const themeText = document.getElementById('theme-text');
        themeText.textContent = this.currentTheme === 'dark' ? 'Light Theme' : 'Dark Theme';
    }
    
    handleSearchInput(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        if (query.length < 2) {
            this.hideSuggestions();
            return;
        }
        
        // Debounce search suggestions
        this.searchTimeout = setTimeout(() => {
            this.fetchSuggestions(query);
        }, 300);
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`/api/search/${encodeURIComponent(query)}?limit=5`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                this.showSuggestions(data.results);
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            this.hideSuggestions();
        }
    }
    
    showSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('search-suggestions');
        
        const suggestionsHTML = suggestions.map(stock => `
            <div class="suggestion-item" onclick="dashboard.selectStock('${stock.ticker}')">
                <div class="flex justify-between items-center">
                    <div>
                        <div class="font-medium">${stock.name}</div>
                        <div class="text-sm opacity-70">${stock.ticker} • ${stock.sector}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-medium">${stock.market_cap_formatted}</div>
                        <div class="text-xs opacity-70">ESG: ${stock.esg_score.toFixed(1)}</div>
                    </div>
                </div>
            </div>
        `).join('');
        
        suggestionsContainer.innerHTML = suggestionsHTML;
        suggestionsContainer.classList.remove('hidden');
    }
    
    hideSuggestions() {
        const suggestionsContainer = document.getElementById('search-suggestions');
        suggestionsContainer.classList.add('hidden');
    }
    
    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        
        if (!query) return;
        
        this.showLoading();
        this.hideSuggestions();
        
        try {
            const response = await fetch(`/api/search/${encodeURIComponent(query)}?limit=12`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                this.showSearchResults(data.results);
            } else {
                this.showError('No stocks found matching your search criteria.');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Failed to search stocks. Please try again.');
        }
    }
    
    showSearchResults(results) {
        this.hideLoading();
        this.hideError();
        
        const resultsSection = document.getElementById('results-section');
        const resultsGrid = document.getElementById('results-grid');
        
        const resultsHTML = results.map(stock => `
            <div class="result-card rounded-xl border-2 p-6 shadow-lg cursor-pointer" onclick="dashboard.analyzeStock('${stock.ticker}')">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h4 class="font-secondary font-bold text-lg">${stock.name}</h4>
                        <p class="text-sm opacity-70">${stock.ticker}</p>
                    </div>
                    ${this.getESGBadge(stock.esg_score)}
                </div>
                
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span class="text-sm">Sector:</span>
                        <span class="text-sm font-medium">${stock.sector}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm">Market Cap:</span>
                        <span class="text-sm font-medium">${stock.market_cap_formatted}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm">ROIC:</span>
                        <span class="text-sm font-medium">${(stock.roic * 100).toFixed(1)}%</span>
                    </div>
                </div>
                
                ${stock.is_delisted ? '<div class="mt-3 text-xs bg-red-500 text-white px-2 py-1 rounded">Delisted/Problematic</div>' : ''}
                
                <div class="mt-4 pt-4 border-t border-gold border-opacity-30">
                    <button class="w-full bg-gold text-primary-black py-2 rounded-lg font-medium text-sm hover:scale-105 transition-transform duration-200">
                        <i class="fas fa-chart-line mr-2"></i>Analyze
                    </button>
                </div>
            </div>
        `).join('');
        
        resultsGrid.innerHTML = resultsHTML;
        resultsSection.classList.remove('hidden');
    }
    
    getESGBadge(score) {
        let badgeClass, badgeText;
        
        if (score >= 60) {
            badgeClass = 'status-excellent';
            badgeText = 'Excellent';
        } else if (score >= 45) {
            badgeClass = 'status-good';
            badgeText = 'Good';
        } else if (score >= 30) {
            badgeClass = 'status-fair';
            badgeText = 'Fair';
        } else {
            badgeClass = 'status-poor';
            badgeText = 'Poor';
        }
        
        return `<div class="status-badge ${badgeClass}">${badgeText} (${score.toFixed(1)})</div>`;
    }
    
    async selectStock(ticker) {
        document.getElementById('search-input').value = ticker;
        this.hideSuggestions();
        await this.analyzeStock(ticker);
    }
    
    async analyzeStock(ticker) {
        this.showLoading();
        
        try {
            const response = await fetch(`/api/analyze/${ticker}`);
            const analysis = await response.json();
            
            if (analysis.error) {
                this.showError(analysis.error);
                return;
            }
            
            this.currentAnalysis = analysis;
            this.showDetailedAnalysis(analysis);
            
        } catch (error) {
            console.error('Analysis error:', error);
            this.showError('Failed to analyze stock. Please try again.');
        }
    }
    
    showDetailedAnalysis(analysis) {
        this.hideLoading();
        this.hideError();
        
        const detailedSection = document.getElementById('detailed-analysis');
        
        // Update ESG content
        this.updateESGContent(analysis);
        
        // Update prediction content
        this.updatePredictionContent(analysis);
        
        // Update risk content
        this.updateRiskContent(analysis);
        
        // Update alternatives content
        this.updateAlternativesContent(analysis);
        
        // Update charts
        this.updateCharts(analysis);
        
        detailedSection.classList.remove('hidden');
        
        // Scroll to detailed analysis
        detailedSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    updateESGContent(analysis) {
        const esgContent = document.getElementById('esg-content');
        const data = analysis.basic_data;
        
        esgContent.innerHTML = `
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="metric-card bg-opacity-10">
                        <div class="metric-value text-2xl">${data.esg_score.toFixed(1)}</div>
                        <div class="metric-label">ESG Score</div>
                    </div>
                    <div class="metric-card bg-opacity-10">
                        <div class="metric-value text-2xl">${(data.roic * 100).toFixed(1)}%</div>
                        <div class="metric-label">ROIC</div>
                    </div>
                </div>
                
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span>Environmental:</span>
                        <div class="flex items-center space-x-2">
                            <div class="w-24 bg-gray-200 rounded-full h-2">
                                <div class="esg-environmental h-2 rounded-full" style="width: ${(data.environmental / 30) * 100}%"></div>
                            </div>
                            <span class="text-sm font-medium">${data.environmental.toFixed(1)}</span>
                        </div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Social:</span>
                        <div class="flex items-center space-x-2">
                            <div class="w-24 bg-gray-200 rounded-full h-2">
                                <div class="esg-social h-2 rounded-full" style="width: ${(data.social / 30) * 100}%"></div>
                            </div>
                            <span class="text-sm font-medium">${data.social.toFixed(1)}</span>
                        </div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Governance:</span>
                        <div class="flex items-center space-x-2">
                            <div class="w-24 bg-gray-200 rounded-full h-2">
                                <div class="esg-governance h-2 rounded-full" style="width: ${(data.governance / 30) * 100}%"></div>
                            </div>
                            <span class="text-sm font-medium">${data.governance.toFixed(1)}</span>
                        </div>
                    </div>
                </div>
                
                <div class="text-xs opacity-70 pt-2 border-t border-gold border-opacity-30">
                    Data Source: ${data.data_source.replace(/_/g, ' ').toUpperCase()}
                </div>
            </div>
        `;
    }
    
    updatePredictionContent(analysis) {
        const predictionContent = document.getElementById('prediction-content');
        const prediction = analysis.prediction;
        
        if (prediction.model === 'Failed') {
            predictionContent.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                    <p>Prediction analysis failed</p>
                    <p class="text-sm opacity-70">${prediction.prediction}</p>
                </div>
            `;
            return;
        }
        
        const trendIcon = prediction.change_percent > 0 ? 'fa-arrow-up prediction-up' : 
                         prediction.change_percent < 0 ? 'fa-arrow-down prediction-down' : 'fa-minus prediction-neutral';
        
        predictionContent.innerHTML = `
            <div class="space-y-4">
                <div class="text-center">
                    <div class="text-3xl mb-2">
                        <i class="fas ${trendIcon}"></i>
                    </div>
                    <div class="metric-value text-2xl ${prediction.change_percent > 0 ? 'prediction-up' : 'prediction-down'}">
                        ${prediction.change_percent > 0 ? '+' : ''}${prediction.change_percent.toFixed(1)}%
                    </div>
                    <div class="metric-label">30-Day Prediction</div>
                </div>
                
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span>Current Price:</span>
                        <span class="font-medium">₹${prediction.current_price}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Predicted Price:</span>
                        <span class="font-medium">₹${prediction.predicted_price}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Confidence:</span>
                        <span class="font-medium">${(prediction.confidence * 100).toFixed(0)}%</span>
                    </div>
                </div>
                
                <div class="confidence-meter">
                    <div class="confidence-indicator" style="width: ${prediction.confidence * 100}%"></div>
                </div>
                
                <div class="text-xs opacity-70 pt-2 border-t border-gold border-opacity-30">
                    Model: ${prediction.model} • Data Points: ${prediction.data_points}
                </div>
            </div>
        `;
    }
    
    updateRiskContent(analysis) {
        const riskContent = document.getElementById('risk-content');
        const risk = analysis.manipulation_risk;
        
        const riskColorClass = risk.risk_level.includes('High') ? 'status-high-risk' :
                              risk.risk_level.includes('Medium') ? 'status-medium-risk' : 'status-low-risk';
        
        riskContent.innerHTML = `
            <div class="space-y-4">
                <div class="text-center">
                    <div class="status-badge ${riskColorClass} text-lg px-4 py-2">
                        ${risk.risk_level}
                    </div>
                    <div class="metric-value text-2xl mt-2">${risk.risk_score}/100</div>
                    <div class="metric-label">Risk Score</div>
                </div>
                
                ${risk.alerts && risk.alerts.length > 0 ? `
                    <div class="space-y-2">
                        <h5 class="font-medium text-sm">Risk Alerts:</h5>
                        ${risk.alerts.map(alert => `
                            <div class="news-alert text-sm">
                                <i class="fas fa-exclamation-triangle mr-2"></i>
                                ${alert}
                            </div>
                        `).join('')}
                    </div>
                ` : '<div class="text-center text-sm opacity-70">No significant risks detected</div>'}
                
                ${risk.volume_ratio && risk.recent_volatility ? `
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <div class="font-medium">Volume Ratio:</div>
                            <div>${risk.volume_ratio}x avg</div>
                        </div>
                        <div>
                            <div class="font-medium">Volatility:</div>
                            <div>${risk.recent_volatility}%</div>
                        </div>
                    </div>
                ` : ''}
                
                <div class="text-xs opacity-70 pt-2 border-t border-gold border-opacity-30">
                    Analysis Date: ${new Date(risk.analysis_date).toLocaleDateString()}
                </div>
            </div>
        `;
    }
    
    updateAlternativesContent(analysis) {
        const alternativesContent = document.getElementById('alternatives-content');
        const alternatives = analysis.alternatives;
        
        if (!alternatives || alternatives.length === 0) {
            alternativesContent.innerHTML = `
                <div class="text-center text-sm opacity-70">
                    <i class="fas fa-check-circle text-2xl mb-2"></i>
                    <p>No alternatives needed</p>
                    <p>This stock appears to be actively traded</p>
                </div>
            `;
            return;
        }
        
        alternativesContent.innerHTML = `
            <div class="space-y-3">
                <div class="text-sm opacity-80 mb-3">
                    Suggested alternatives in the same sector:
                </div>
                ${alternatives.map(alt => `
                    <div class="alternative-stock">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <div class="font-medium">${alt.name}</div>
                                <div class="text-sm opacity-70">${alt.ticker}</div>
                                <div class="text-xs opacity-60 mt-1">${alt.reason}</div>
                            </div>
                            <div class="text-right">
                                <div class="text-sm font-medium">${alt.market_cap_formatted}</div>
                                <div class="text-xs opacity-70">ESG: ${alt.esg_score.toFixed(1)}</div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    setupCharts() {
        // Initialize chart contexts
        const esgCtx = document.getElementById('esg-chart');
        const riskCtx = document.getElementById('risk-chart');
        
        if (esgCtx) {
            this.charts.esg = new Chart(esgCtx.getContext('2d'), {
                type: 'radar',
                data: {
                    labels: ['Environmental', 'Social', 'Governance'],
                    datasets: [{
                        label: 'ESG Scores',
                        data: [0, 0, 0],
                        backgroundColor: 'rgba(255, 215, 0, 0.2)',
                        borderColor: '#FFD700',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: this.currentTheme === 'dark' ? '#FFFFFF' : '#333333'
                            }
                        }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 30,
                            ticks: {
                                color: this.currentTheme === 'dark' ? '#FFFFFF' : '#333333'
                            },
                            grid: {
                                color: this.currentTheme === 'dark' ? '#444444' : '#CCCCCC'
                            }
                        }
                    }
                }
            });
        }
        
        if (riskCtx) {
            this.charts.risk = new Chart(riskCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Risk Score', 'Safe Zone'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#EF4444', '#10B981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: this.currentTheme === 'dark' ? '#FFFFFF' : '#333333'
                            }
                        }
                    }
                }
            });
        }
    }
    
    updateCharts(analysis) {
        const data = analysis.basic_data;
        const risk = analysis.manipulation_risk;
        
        // Update ESG radar chart
        if (this.charts.esg) {
            this.charts.esg.data.datasets[0].data = [
                data.environmental,
                data.social,
                data.governance
            ];
            this.charts.esg.update();
        }
        
        // Update risk doughnut chart
        if (this.charts.risk) {
            const riskScore = risk.risk_score || 0;
            this.charts.risk.data.datasets[0].data = [riskScore, 100 - riskScore];
            this.charts.risk.update();
        }
    }
    
    updateChartThemes() {
        const textColor = this.currentTheme === 'dark' ? '#FFFFFF' : '#333333';
        const gridColor = this.currentTheme === 'dark' ? '#444444' : '#CCCCCC';
        
        Object.values(this.charts).forEach(chart => {
            if (chart.options.plugins?.legend?.labels) {
                chart.options.plugins.legend.labels.color = textColor;
            }
            if (chart.options.scales?.r) {
                chart.options.scales.r.ticks.color = textColor;
                chart.options.scales.r.grid.color = gridColor;
            }
            chart.update();
        });
    }
    
    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('error-message').classList.add('hidden');
    }
    
    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }
    
    showError(message) {
        document.getElementById('error-text').textContent = message;
        document.getElementById('error-message').classList.remove('hidden');
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('results-section').classList.add('hidden');
    }
    
    hideError() {
        document.getElementById('error-message').classList.add('hidden');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new ESGDashboard();
});
