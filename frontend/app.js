// Game State & Storage
let chartInstance = null;
const BACKEND_URL = "http://127.0.0.1:5000";

function getStoreSearchUrl(site, query) {
    const encodedQuery = encodeURIComponent(query);
    switch(site) {
        case "Amazon India":
            return `https://www.amazon.in/s?k=${encodedQuery}`;
        case "Flipkart":
            return `https://www.flipkart.com/search?q=${encodedQuery}`;
        case "Croma":
            return `https://www.croma.com/search/?text=${encodedQuery}`;
        case "Reliance Digital":
            return `https://www.reliancedigital.in/search?q=${encodedQuery}`;
        case "Tata CLiQ":
            return `https://www.tatacliq.com/search/?text=${encodedQuery}`;
        case "Vijay Sales":
            return `https://www.vijaysales.com/search/${encodedQuery}`;
        case "JioMart":
            return `https://www.jiomart.com/search/${encodedQuery}`;
        case "Snapdeal":
            return `https://www.snapdeal.com/search?keyword=${encodedQuery}`;
        case "ShopClues":
            return `https://www.shopclues.com/search?q=${encodedQuery}`;
        case "Meesho":
            return `https://www.meesho.com/search?q=${encodedQuery}`;
        default:
            return "https://www.google.com";
    }
}

// DOM Elements
const themeToggle = document.getElementById("theme-toggle");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");

const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const loadingTitle = document.getElementById("loading-title");
const loadingText = document.getElementById("loading-text");

const leftPanel = document.getElementById("left-panel");
const rightPanel = document.getElementById("right-panel");
const scanLogsWrapper = document.getElementById("scan-logs-wrapper");
const scanProgressLabel = document.getElementById("scan-progress-label");

const recoVal = document.getElementById("reco-val");
const recoReason = document.getElementById("reco-reason");
const probRing10 = document.getElementById("prob-ring-10");
const probVal10 = document.getElementById("prob-val-10");
const probVal20 = document.getElementById("prob-val-20");
const savingsPct = document.getElementById("savings-pct");
const currentPriceVal = document.getElementById("current-price-val");
const predictedLowVal = document.getElementById("predicted-low-val");
const chartProductName = document.getElementById("chart-product-name");

// Gamification elements removed

// --- Theme Management ---
function initTheme() {
    const savedTheme = localStorage.getItem("dealpulse_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    themeToggle.textContent = savedTheme === "dark" ? "🌙" : "☀️";
}

themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("dealpulse_theme", newTheme);
    themeToggle.textContent = newTheme === "dark" ? "🌙" : "☀️";
    
    // Update chart colors dynamically if chart exists
    if (chartInstance) {
        updateChartColors();
    }
});

// Prefill search query from clicks
function prefillSearch(term) {
    searchInput.value = term;
    initiateSearch(term);
}

// --- API Search & Animations ---
searchForm.addEventListener("submit", () => {
    const query = searchInput.value.trim();
    if (query) {
        initiateSearch(query);
    }
});

async function initiateSearch(query) {
    // 1. Loading UI state
    emptyState.style.display = "none";
    leftPanel.style.display = "none";
    rightPanel.style.display = "none";
    
    loadingTitle.textContent = "Initializing Scanner...";
    loadingText.textContent = `Pulsing search requests for '${query}' across 10 sites...`;
    loadingState.style.display = "flex";
    
    try {
        // Fetch matching and predictions from backend
        const response = await fetch(`${BACKEND_URL}/api/search`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ query: query })
        });
        
        if (!response.ok) {
            throw new Error("Backend server error.");
        }
        
        const data = await response.json();
        
        // Hide initial loading screen
        loadingState.style.display = "none";
        
        // Show panel wrappers so animations look sequential
        leftPanel.style.display = "flex";
        rightPanel.style.display = "none"; // hide right panel during scan
        
        // 2. Play Store Scanning Animation
        await playScannerAnimation(data.scan_logs, data);
        
    } catch (error) {
        console.error("Search error:", error);
        loadingTitle.textContent = "Connection Failed";
        loadingText.textContent = "Make sure the Python Flask backend is running (localhost:5000) and try again.";
        loadingState.className = "glass-card loading-indicator";
    }
}

// Renders the simulated scanner with visual timing delays
async function playScannerAnimation(logs, allData) {
    scanLogsWrapper.innerHTML = "";
    scanProgressLabel.textContent = "Initializing Radar...";
    
    // Build blank items in container
    logs.forEach((log, index) => {
        const row = document.createElement("div");
        row.className = "scan-row";
        row.id = `scan-row-${index}`;
        const searchUrl = getStoreSearchUrl(log.site, allData.query);
        row.innerHTML = `
            <div class="store-meta">
                <span class="store-name">${log.site}</span>
                <span class="store-product" id="scan-prod-${index}">Scanning...</span>
            </div>
            <div class="store-match-data">
                <span class="store-price" id="scan-price-${index}">₹---.--</span>
                <span class="match-score-badge" id="scan-score-${index}">--%</span>
            </div>
        `;
        scanLogsWrapper.appendChild(row);
    });
    
    // Sequentially step through each retailer
    for (let i = 0; i < logs.length; i++) {
        const row = document.getElementById(`scan-row-${i}`);
        const prodSpan = document.getElementById(`scan-prod-${i}`);
        const priceSpan = document.getElementById(`scan-price-${i}`);
        const scoreSpan = document.getElementById(`scan-score-${i}`);
        
        // Mark row active
        row.className = "scan-row active";
        scanProgressLabel.textContent = `Scanning sites: ${i + 1}/10`;
        
        // Visual delay to simulate server communication & scraping
        await new Promise(resolve => setTimeout(resolve, 250));
        
        // Fill data and complete
        const log = logs[i];
        prodSpan.innerHTML = `<a href="${log.url || '#'}" target="_blank" rel="noopener noreferrer">${log.original_title}</a>`;
        priceSpan.textContent = `₹${log.base_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
        
        scoreSpan.textContent = `${log.match_score.toFixed(0)}%`;
        
        // Set match badge style
        let badgeClass = "low";
        if (log.confidence === "High") badgeClass = "high";
        else if (log.confidence === "Medium") badgeClass = "medium";
        scoreSpan.className = `match-score-badge ${badgeClass}`;
        
        row.className = `scan-row completed ${log.is_matched ? 'matched' : 'mismatched'}`;
    }
    
    scanProgressLabel.textContent = "Scan complete! Analyzing data...";
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Reveal predictions panel
    rightPanel.style.display = "flex";
    
    // Populate predictions UI
    populatePredictionResults(allData);
}

// Updates metrics, dials, recommendations, and gamified bets
function populatePredictionResults(data) {
    chartProductName.textContent = data.resolved_title;
    
    // Reco value styles
    recoVal.textContent = data.recommendation;
    recoVal.className = "recommendation-value";
    recoVal.classList.add(data.recommendation.toLowerCase());
    recoReason.textContent = data.reason;
    
    // 10-day deal probability circle animation
    const prob10 = data.prob_drop_10;
    probVal10.textContent = `${prob10}%`;
    animateProbabilityRing(prob10);
    
    // Detailed stats
    probVal20.textContent = `${data.prob_drop_20}%`;
    savingsPct.textContent = `${data.potential_savings_pct}%`;
    currentPriceVal.textContent = `₹${data.current_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
    predictedLowVal.textContent = `₹${data.predicted_low.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
    
    // Render Chart
    renderForecastChart(data.history, data.forecast);
}

// Computes circular progress ring offsets (circumference: 283)
function animateProbabilityRing(probability) {
    const circumference = 283;
    const offset = circumference - (probability / 100) * circumference;
    probRing10.style.strokeDashoffset = offset;
}

// --- Chart rendering ---
function renderForecastChart(history, forecast) {
    const ctx = document.getElementById("price-forecast-chart").getContext("2d");
    
    // Process dataset labels & data values
    const labels = [];
    const histData = [];
    const foreData = [];
    
    // Insert history
    history.forEach(pt => {
        labels.push(pt.date);
        histData.push(pt.price);
        foreData.push(null); // padding for forecast
    });
    
    // Insert forecast bridge (connect last history node to first forecast node)
    if (history.length > 0 && forecast.length > 0) {
        foreData[history.length - 1] = history[history.length - 1].price;
    }
    
    // Insert forecast
    forecast.forEach(pt => {
        labels.push(pt.date);
        histData.push(null); // padding for history
        foreData.push(pt.price);
    });
    
    // Clear old chart
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    const theme = document.documentElement.getAttribute("data-theme");
    const textColor = theme === "dark" ? "#94a3b8" : "#64748b";
    const gridColor = theme === "dark" ? "rgba(255, 255, 255, 0.05)" : "rgba(15, 23, 42, 0.05)";
    
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Historical Price',
                    data: histData,
                    borderColor: '#00f2fe',
                    backgroundColor: 'rgba(0, 242, 254, 0.05)',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    spanGaps: false,
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'ML Forecasted Price',
                    data: foreData,
                    borderColor: '#ff007f',
                    backgroundColor: 'rgba(255, 0, 127, 0.05)',
                    borderWidth: 2.5,
                    borderDash: [6, 4],
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    spanGaps: false,
                    fill: false,
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: textColor,
                        font: { family: 'Inter', weight: 500 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: theme === "dark" ? "#161c2d" : "#ffffff",
                    titleColor: theme === "dark" ? "#f8fafc" : "#0f172a",
                    bodyColor: theme === "dark" ? "#f8fafc" : "#0f172a",
                    borderColor: 'rgba(0, 242, 254, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textColor,
                        maxTicksLimit: 8,
                        font: { family: 'Inter' }
                    }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textColor,
                        font: { family: 'Inter' },
                        callback: function(value) {
                            return '₹' + value;
                        }
                    }
                }
            }
        }
    });
}

function updateChartColors() {
    if (!chartInstance) return;
    const theme = document.documentElement.getAttribute("data-theme");
    const textColor = theme === "dark" ? "#94a3b8" : "#64748b";
    const gridColor = theme === "dark" ? "rgba(255, 255, 255, 0.05)" : "rgba(15, 23, 42, 0.05)";
    
    chartInstance.options.plugins.legend.labels.color = textColor;
    chartInstance.options.scales.x.grid.color = gridColor;
    chartInstance.options.scales.x.ticks.color = textColor;
    chartInstance.options.scales.y.grid.color = gridColor;
    chartInstance.options.scales.y.ticks.color = textColor;
    
    chartInstance.update();
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
    initTheme();
});
