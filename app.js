let listingsData = [];
let dealsData = [];
let statsData = {};
let sortColumn = 'price_per_tb';
let sortDirection = 'asc';
let priceChart = null;

function getListingAge(dateStr) {
    const now = new Date();
    const listingDate = new Date(dateStr);
    const diffMs = now - listingDate;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    if (diffDays < 30) return `${Math.floor(diffDays/7)}w`;
    return `${Math.floor(diffDays/30)}mo`;
}

function getAgeClass(dateStr) {
    const now = new Date();
    const listingDate = new Date(dateStr);
    const diffHours = (now - listingDate) / 3600000;
    
    if (diffHours < 24) return 'age-fresh';
    if (diffHours < 72) return 'age-recent';
    return 'age-old';
}

async function loadData() {
    try {
        const [listings, deals, stats] = await Promise.all([
            fetch('data/listings.json').then(r => r.json()).catch(() => []),
            fetch('data/deals.json').then(r => r.json()).catch(() => []),
            fetch('data/stats.json').then(r => r.json()).catch(() => ({history: []}))
        ]);
        
        listingsData = listings;
        dealsData = deals;
        statsData = stats;
        
        updateStats();
        renderDeals();
        renderListings();
        updateChart('week');
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('deals-body').innerHTML = '<tr><td colspan="8" class="loading">[FEL: KUNDE INTE LADDA DATA]</td></tr>';
        document.getElementById('listings-body').innerHTML = '<tr><td colspan="8" class="loading">[FEL: KUNDE INTE LADDA DATA]</td></tr>';
    }
}

function updateStats() {
    const avgPrice = listingsData.length > 0
        ? (listingsData.reduce((sum, l) => sum + (l.price_per_tb || 0), 0) / listingsData.length).toFixed(0)
        : '0';
    
    document.getElementById('avg-price').textContent = avgPrice;
    document.getElementById('total-listings').textContent = listingsData.length;
    document.getElementById('total-deals').textContent = dealsData.length;
    
    if (statsData.history && statsData.history.length > 0) {
        const lastUpdate = new Date(statsData.history[statsData.history.length - 1].date);
        document.getElementById('last-updated').textContent = lastUpdate.toLocaleString('sv-SE', { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        }).toUpperCase();
    } else {
        document.getElementById('last-updated').textContent = 'N/A';
    }
}

function updateChart(range) {
    if (!statsData.history || statsData.history.length === 0) return;

    // Update active button state
    document.querySelectorAll('.chart-controls .terminal-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(range === 'week' ? '1V' : range === 'month' ? '1M' : '1Å')) {
            btn.classList.add('active');
        }
    });

    const now = new Date();
    let cutoffDate = new Date();
    
    if (range === 'week') cutoffDate.setDate(now.getDate() - 7);
    else if (range === 'month') cutoffDate.setMonth(now.getMonth() - 1);
    else if (range === 'year') cutoffDate.setFullYear(now.getFullYear() - 1);

    const filteredHistory = statsData.history.filter(entry => new Date(entry.date) >= cutoffDate);
    
    const labels = filteredHistory.map(entry => {
        const date = new Date(entry.date);
        return date.toLocaleDateString('sv-SE', { month: 'short', day: 'numeric' });
    });
    
    const dataPointsHdd = filteredHistory.map(entry => entry.avg_price_hdd || entry.avg_price_per_tb);
    const dataPointsSsd = filteredHistory.map(entry => entry.avg_price_ssd || null);

    const ctx = document.getElementById('priceChart').getContext('2d');
    
    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'HDD (SEK/TB)',
                    data: dataPointsHdd,
                    borderColor: '#50fa7b', // Dracula Green
                    backgroundColor: 'rgba(80, 250, 123, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#282a36',
                    pointBorderColor: '#50fa7b',
                    fill: false
                },
                {
                    label: 'SSD (SEK/TB)',
                    data: dataPointsSsd,
                    borderColor: '#bd93f9', // Dracula Purple
                    backgroundColor: 'rgba(189, 147, 249, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#282a36',
                    pointBorderColor: '#bd93f9',
                    fill: false,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#f8f8f2',
                        font: {
                            family: "'IBM Plex Mono', monospace"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#282a36',
                    titleColor: '#50fa7b',
                    bodyColor: '#f8f8f2',
                    borderColor: '#44475a',
                    borderWidth: 1,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(0);
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: {
                        color: '#44475a',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6272a4',
                        font: {
                            family: "'IBM Plex Mono', monospace"
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6272a4',
                        font: {
                            family: "'IBM Plex Mono', monospace"
                        },
                        maxTicksLimit: 8
                    }
                }
            }
        }
    });
}

function renderDeals() {
    const tbody = document.getElementById('deals-body');
    
    if (dealsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">[INGA AKTIVA FYND HITTADES]</td></tr>';
        return;
    }
    
    tbody.innerHTML = dealsData.map(deal => {
        const driveType = deal.is_ssd ? 'SSD' : 'HDD';
        const typeClass = deal.is_ssd ? 'type-ssd' : 'type-hdd';
        const age = getListingAge(deal.date);
        const ageClass = getAgeClass(deal.date);
        
        return `
            <tr class="deal-row">
                <td class="text-center"><span class="type-badge ${typeClass}">${driveType}</span></td>
                <td class="text-center">${deal.capacity_tb}TB</td>
                <td class="text-center">${deal.price_sek} SEK</td>
                <td class="text-center price-excellent">${deal.price_per_tb}</td>
                <td class="text-center ${ageClass}">${age}</td>
                <td>${escapeHtml(deal.location)}</td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(deal.title)}</td>
                <td class="text-center"><a href="${deal.url}" target="_blank" class="terminal-btn">VISA</a></td>
            </tr>
        `;
    }).join('');
}

function renderListings() {
    const tbody = document.getElementById('listings-body');
    
    if (listingsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">[INGEN DATA TILLGÄNGLIG]</td></tr>';
        return;
    }
    
    const sortedData = [...listingsData].sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];
        
        // Handle missing values
        if (aVal === undefined) aVal = '';
        if (bVal === undefined) bVal = '';
        
        if (sortColumn === 'age') {
            aVal = new Date(a.date).getTime();
            bVal = new Date(b.date).getTime();
        } else if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        if (sortDirection === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
    
    tbody.innerHTML = sortedData.map(listing => {
        const driveType = listing.is_ssd ? 'SSD' : 'HDD';
        const typeClass = listing.is_ssd ? 'type-ssd' : 'type-hdd';
        const threshold = listing.is_ssd ? 600 : 150;
        
        let priceClass = 'price-high';
        if (listing.price_per_tb <= threshold) priceClass = 'price-excellent';
        else if (listing.price_per_tb <= threshold * 1.5) priceClass = 'price-good';
        else if (listing.price_per_tb <= threshold * 2) priceClass = 'price-ok';
        
        const age = getListingAge(listing.date);
        const ageClass = getAgeClass(listing.date);
        
        // Only show badge for SSDs
        const typeDisplay = listing.is_ssd ? `<span class="type-badge ${typeClass}">${driveType}</span>` : driveType;
        
        return `
            <tr>
                <td class="text-center">${typeDisplay}</td>
                <td class="text-center">${listing.capacity_tb}TB</td>
                <td class="text-center">${listing.price_sek} SEK</td>
                <td class="text-center ${priceClass}">${listing.price_per_tb}</td>
                <td class="text-center ${ageClass}">${age}</td>
                <td>${escapeHtml(listing.location)}</td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(listing.title)}</td>
                <td class="text-center"><a href="${listing.url}" target="_blank" class="terminal-btn">VISA</a></td>
            </tr>
        `;
    }).join('');
}

function sortTable(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    renderListings();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

loadData();
