// Greenify Chart.js wrapper for visual analysis
let footprintPieChart = null;
let trendLineChart = null;

const chartColors = {
    energy: '#10b981',      // Emerald Green
    transport: '#06b6d4',   // Teal / Cyan
    diet: '#f59e0b',        // Amber Gold
    waste: '#a78bfa',       // Purple Accent
    gridColor: 'rgba(255, 255, 255, 0.06)',
    textColor: '#9ca3af',
    tooltipBg: 'rgba(9, 15, 11, 0.95)',
    tooltipBorder: 'rgba(16, 185, 129, 0.3)'
};

function renderPieChart(canvasId, breakdown) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Destroy existing chart to prevent canvas overlay bugs
    if (footprintPieChart) {
        footprintPieChart.destroy();
    }

    const data = {
        labels: ['Energy (Home)', 'Commute / Transport', 'Diet Type', 'Waste & Landfill'],
        datasets: [{
            data: [
                breakdown.energy || 0,
                breakdown.transport || 0,
                breakdown.diet || 0,
                breakdown.waste || 0
            ],
            backgroundColor: [
                chartColors.energy,
                chartColors.transport,
                chartColors.diet,
                chartColors.waste
            ],
            borderColor: 'rgba(8, 13, 10, 0.9)',
            borderWidth: 2
        }]
    };

    footprintPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: chartColors.textColor,
                        font: {
                            family: 'Plus Jakarta Sans',
                            size: 12,
                            weight: 500
                        },
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: '#fff',
                    bodyColor: '#e5e7eb',
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${context.raw.toFixed(2)} kg CO2e`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

function renderTrendChart(canvasId, historyData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (trendLineChart) {
        trendLineChart.destroy();
    }

    // Sort by date ascending
    const sortedData = [...historyData].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Take last 7 entries for weekly trend, or last 15
    const displayData = sortedData.slice(-10);

    const labels = displayData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const datasets = [
        {
            label: 'Total Footprint',
            data: displayData.map(d => d.footprint),
            borderColor: '#ffffff',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            borderWidth: 3,
            tension: 0.3,
            fill: true
        },
        {
            label: 'Energy',
            data: displayData.map(d => d.energy),
            borderColor: chartColors.energy,
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            tension: 0.3,
            borderDash: [5, 5],
            hidden: true
        },
        {
            label: 'Transport',
            data: displayData.map(d => d.transport),
            borderColor: chartColors.transport,
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            tension: 0.3,
            borderDash: [5, 5],
            hidden: true
        }
    ];

    trendLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: chartColors.gridColor
                    },
                    ticks: {
                        color: chartColors.textColor,
                        font: {
                            family: 'Plus Jakarta Sans',
                            size: 11
                        }
                    }
                },
                y: {
                    grid: {
                        color: chartColors.gridColor
                    },
                    ticks: {
                        color: chartColors.textColor,
                        font: {
                            family: 'Plus Jakarta Sans',
                            size: 11
                        }
                    },
                    title: {
                        display: true,
                        text: 'Emissions (kg CO2e)',
                        color: chartColors.textColor,
                        font: {
                            family: 'Plus Jakarta Sans',
                            size: 11,
                            weight: 600
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: chartColors.textColor,
                        font: {
                            family: 'Plus Jakarta Sans',
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    padding: 12
                }
            }
        }
    });
}
