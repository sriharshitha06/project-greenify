// Greenify SPA Controller
document.addEventListener('DOMContentLoaded', () => {
    // 1. Session check
    if (!api.isLoggedIn()) {
        window.location.href = 'login.html';
        return;
    }

    // Initialize UI
    initNavigation();
    loadUserData();
    loadDashboardStats();
    setupCalculator();
    setupVerifier();
    setupAdvisor();
    
    // Add logout action
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            api.logout();
        });
    }
    
    // Add download report trigger
    const downloadBtn = document.getElementById('btn-download-report');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async () => {
            try {
                await api.downloadReport();
            } catch (err) {
                alert('Failed to download report: ' + err.message);
            }
        });
    }
});

// Tab Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            const targetId = item.getAttribute('data-tab');
            if (!targetId) return;

            // Remove active class
            navItems.forEach(n => n.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class
            item.classList.add('active');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
            }

            // Lazy load tab data
            onTabActivate(targetId);
        });
    });
}

function onTabActivate(tabId) {
    if (tabId === 'dashboard') {
        loadDashboardStats();
    } else if (tabId === 'tracker') {
        loadTrackerHistory();
    } else if (tabId === 'verify') {
        loadVerifyHistory();
    } else if (tabId === 'leaderboard') {
        loadLeaderboard();
    } else if (tabId === 'advisor') {
        loadAdvisorData();
    } else if (tabId === 'badges') {
        loadBadges();
    }
}

// Global user profile fetch
async function loadUserData() {
    try {
        const user = await api.getMe();
        
        // Update sidebar and topbar
        const nameElems = document.querySelectorAll('.user-name');
        nameElems.forEach(el => el.textContent = user.username);
        
        const ptElems = document.querySelectorAll('.user-points');
        ptElems.forEach(el => el.textContent = `${user.points} Points`);

        const avatarElems = document.querySelectorAll('.user-avatar');
        avatarElems.forEach(el => {
            el.textContent = user.username.substring(0, 2).toUpperCase();
        });
    } catch (err) {
        console.error('Failed to load user profile:', err);
    }
}

// Load and render dashboard stats and charts
async function loadDashboardStats() {
    try {
        const stats = await api.getAnalytics();
        
        // Update stats counts
        document.getElementById('stat-avg-footprint').textContent = `${stats.average_footprint.toFixed(1)} kg`;
        
        const savedEl = document.getElementById('stat-carbon-saved');
        savedEl.textContent = `${stats.total_carbon_saved.toFixed(1)} kg`;
        if (stats.total_carbon_saved >= 0) {
            savedEl.className = 'stat-value text-primary'; // Green
        } else {
            savedEl.className = 'stat-value text-danger';  // Red
        }

        document.getElementById('stat-logs-count').textContent = stats.total_entries;

        // Render charts
        if (stats.total_entries > 0) {
            document.getElementById('no-data-alert').style.display = 'none';
            document.getElementById('charts-wrapper').style.display = 'grid';
            
            // Render Pie chart
            renderPieChart('doughnut-chart', stats.category_breakdown);
            
            // Render Line trend chart
            renderTrendChart('line-trend-chart', stats.history_chart_data);
        } else {
            document.getElementById('no-data-alert').style.display = 'block';
            document.getElementById('charts-wrapper').style.display = 'none';
        }
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

// Tracker Panel: load history table
async function loadTrackerHistory() {
    const tableBody = document.getElementById('tracker-history-table');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;"><div class="spinner"></div></td></tr>';

    try {
        const history = await api.getHistory();
        tableBody.innerHTML = '';
        
        if (history.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);">No carbon entries recorded yet. Submit your first calculations!</td></tr>';
            return;
        }

        history.forEach(log => {
            const tr = document.createElement('tr');
            
            const badgeClass = log.classification.toLowerCase() === 'low' ? 'badge-low' : 
                               (log.classification.toLowerCase() === 'medium' ? 'badge-medium' : 
                               (log.classification.toLowerCase() === 'high' ? 'badge-high' : 'badge-extreme'));

            tr.innerHTML = `
                <td><strong>${log.date}</strong></td>
                <td>${log.electricity_kwh} kWh</td>
                <td>${log.petrol_liters + log.diesel_liters + log.cng_liters} L</td>
                <td><span class="verify-status verified">${log.diet_type}</span></td>
                <td><strong>${log.carbon_footprint.toFixed(1)} kg CO2e</strong></td>
                <td><span class="result-badge ${badgeClass}">${log.classification}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--accent-red);">Error loading history: ${err.message}</td></tr>`;
    }
}

// Form logic and real-time predictor hooks
function setupCalculator() {
    const calcForm = document.getElementById('carbon-calculator-form');
    if (!calcForm) return;

    const inputs = calcForm.querySelectorAll('input, select');
    const realTimeVal = document.getElementById('realtime-calc-val');
    const realTimeBadge = document.getElementById('realtime-calc-badge');

    // Run real-time preview
    const updatePreview = async () => {
        const data = getFormData();
        try {
            const res = await api.predictCarbon(data);
            realTimeVal.textContent = res.carbon_footprint.toFixed(1);
            
            // Set classification class
            const badgeClass = res.classification.toLowerCase() === 'low' ? 'badge-low' : 
                               (res.classification.toLowerCase() === 'medium' ? 'badge-medium' : 
                               (res.classification.toLowerCase() === 'high' ? 'badge-high' : 'badge-extreme'));
            
            realTimeBadge.className = `result-badge ${badgeClass}`;
            realTimeBadge.textContent = res.classification;
            realTimeBadge.style.display = 'inline-block';
            
            // Anomaly indicator
            if (res.is_anomaly) {
                document.getElementById('anomaly-calc-warning').style.display = 'block';
            } else {
                document.getElementById('anomaly-calc-warning').style.display = 'none';
            }
        } catch (err) {
            console.error('Prediction failed:', err);
        }
    };

    // Attach listeners
    inputs.forEach(input => {
        input.addEventListener('input', updatePreview);
        input.addEventListener('change', updatePreview);
    });

    // Form submission
    calcForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = getFormData();
        
        const btn = calcForm.querySelector('button[type="submit"]');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Logging emissions...';

        try {
            const logResult = await api.logActivity(data);
            
            // Pop success message
            const alert = document.getElementById('tracker-success-alert');
            alert.textContent = `Emissions logged successfully! Footprint: ${logResult.carbon_footprint.toFixed(1)} kg (${logResult.classification}).`;
            alert.style.display = 'block';
            
            // Clear message after 4s
            setTimeout(() => alert.style.display = 'none', 5000);
            
            // Refresh stats & profile
            loadUserData();
            loadDashboardStats();
            loadTrackerHistory();
            
        } catch (err) {
            alert('Failed to log emissions: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    });

    function getFormData() {
        return {
            date: document.getElementById('calc-date').value || null,
            electricity_kwh: parseFloat(document.getElementById('calc-electricity').value) || 0,
            lpg_cylinders: parseFloat(document.getElementById('calc-lpg').value) || 0,
            petrol_liters: parseFloat(document.getElementById('calc-petrol').value) || 0,
            diesel_liters: parseFloat(document.getElementById('calc-diesel').value) || 0,
            cng_liters: parseFloat(document.getElementById('calc-cng').value) || 0,
            diet_type: document.getElementById('calc-diet').value || 'vegetarian',
            waste_recycled_pct: parseFloat(document.getElementById('calc-waste').value) || 0,
            public_transport_km: parseFloat(document.getElementById('calc-transit').value) || 0,
            cycling_walking_km: parseFloat(document.getElementById('calc-cycling').value) || 0
        };
    }
}

// OpenCV Verification Panel
function setupVerifier() {
    const fileInput = document.getElementById('verify-file-input');
    const dropzone = document.getElementById('verify-dropzone');
    const preview = document.getElementById('verify-preview-img');
    const uploadForm = document.getElementById('verify-upload-form');
    
    if (!dropzone) return;

    // File selection clicks
    dropzone.addEventListener('click', () => fileInput.click());

    // File changes
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file) {
            showPreview(file);
        }
    });

    // Drag and drop actions
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--primary)';
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            showPreview(file);
        }
    });

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            document.querySelector('.dropzone-icon').style.display = 'none';
            document.querySelector('.dropzone-text').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    // Submit image to OpenCV backend
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = fileInput.files[0];
        const activityType = document.getElementById('verify-activity-type').value;

        if (!file) {
            alert('Please select or drop an image first!');
            return;
        }

        const btn = uploadForm.querySelector('button[type="submit"]');
        const originalText = btn.textContent;
        const spinner = document.getElementById('verify-spinner');
        const outputCard = document.getElementById('verify-output-card');

        btn.disabled = true;
        btn.textContent = 'Verifying image...';
        spinner.style.display = 'block';
        outputCard.style.display = 'none';

        try {
            const res = await api.uploadImage(file, activityType);
            
            // Render results
            spinner.style.display = 'none';
            outputCard.style.display = 'block';

            const statusEl = document.getElementById('verify-result-status');
            const confEl = document.getElementById('verify-result-confidence');
            const ptsEl = document.getElementById('verify-result-points');
            const msgEl = document.getElementById('verify-result-msg');
            const resImg = document.getElementById('verify-result-img');

            statusEl.textContent = res.status;
            statusEl.className = `verify-status ${res.status.toLowerCase() === 'verified' ? 'verified' : 'rejected'}`;
            
            confEl.textContent = `${(res.confidence * 100).toFixed(0)}%`;
            ptsEl.textContent = `+${res.points_earned} PTS`;
            msgEl.textContent = res.status === 'Verified' ? 'Your activity was validated by OpenCV. Keep up the eco-habits!' : 'OpenCV verification failed. Ensure the activity photo is clear.';
            
            // Set image source. We query the backend static server
            resImg.src = `http://127.0.0.1:8000${res.image_path}?t=${Date.now()}`; // cache bust query
            resImg.style.display = 'block';

            // Refresh profile and history
            loadUserData();
            loadVerifyHistory();
            
            // Reset upload form
            fileInput.value = '';
            preview.style.display = 'none';
            document.querySelector('.dropzone-icon').style.display = 'block';
            document.querySelector('.dropzone-text').style.display = 'block';
            
        } catch (err) {
            spinner.style.display = 'none';
            alert('Verification upload error: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    });
}

// Load verification history
async function loadVerifyHistory() {
    const list = document.getElementById('verify-history-list');
    if (!list) return;

    list.innerHTML = '<div class="spinner"></div>';

    try {
        const history = await api.getVerifyHistory();
        list.innerHTML = '';

        if (history.length === 0) {
            list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-secondary);">No verifications uploaded yet. Check your eco habits!</div>';
            return;
        }

        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'verify-item';
            
            const dateStr = new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            const labelClass = item.status.toLowerCase() === 'verified' ? 'verified' : 'rejected';
            
            div.innerHTML = `
                <img class="verify-img-thumb" src="http://127.0.0.1:8000${item.image_path}" alt="upload">
                <div class="verify-details">
                    <div class="verify-type">${item.activity_type.replace('_', ' ')}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top:2px;">Logged: ${dateStr}</div>
                    <span class="verify-status ${labelClass}">${item.status} (${(item.confidence * 100).toFixed(0)}%)</span>
                </div>
                <div class="verify-points">+${item.points_earned} PTS</div>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        list.innerHTML = `<div style="text-align:center;color:var(--accent-red);padding:20px;">Failed to load upload history: ${err.message}</div>`;
    }
}

// Leaderboard Loading
async function loadLeaderboard() {
    const tableBody = document.getElementById('leaderboard-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center;"><div class="spinner"></div></td></tr>';

    try {
        const rankList = await api.getLeaderboard();
        tableBody.innerHTML = '';

        rankList.forEach(user => {
            const tr = document.createElement('tr');
            tr.className = 'leaderboard-row';

            let rankContent = user.rank;
            if (user.rank === 1) {
                rankContent = '<div class="rank-medal medal-1">1</div>';
            } else if (user.rank === 2) {
                rankContent = '<div class="rank-medal medal-2">2</div>';
            } else if (user.rank === 3) {
                rankContent = '<div class="rank-medal medal-3">3</div>';
            }

            tr.innerHTML = `
                <td class="leaderboard-rank">${rankContent}</td>
                <td>
                    <div class="leaderboard-user">
                        <div class="user-avatar" style="width:30px;height:30px;font-size:12px;">${user.username.substring(0, 2).toUpperCase()}</div>
                        <span>${user.username}</span>
                    </div>
                </td>
                <td class="leaderboard-points">${user.points} PTS</td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="3" style="text-align:center;color:var(--accent-red);">Failed to load rankings: ${err.message}</td></tr>`;
    }
}

// Badges Loading
async function loadBadges() {
    const grid = document.getElementById('badges-grid-container');
    if (!grid) return;

    grid.innerHTML = '<div class="spinner"></div>';

    try {
        const badges = await api.getBadges();
        grid.innerHTML = '';

        badges.forEach(badge => {
            const card = document.createElement('div');
            card.className = `glass-panel badge-card ${badge.unlocked ? '' : 'locked'}`;

            // Map standard keys to FontAwesome or similar classes
            let iconClass = 'fa-leaf';
            if (badge.icon === 'bicycle') iconClass = 'fa-bicycle';
            else if (badge.icon === 'recycle') iconClass = 'fa-recycle';
            else if (badge.icon === 'bus') iconClass = 'fa-bus';
            else if (badge.icon === 'camera') iconClass = 'fa-camera';
            else if (badge.icon === 'trophy') iconClass = 'fa-trophy';

            card.innerHTML = `
                <div class="badge-icon-wrapper">
                    <i class="fas ${iconClass}"></i>
                </div>
                <div class="badge-info">
                    <div class="badge-name">${badge.name}</div>
                    <div class="badge-desc">${badge.description}</div>
                    ${badge.unlocked ? `<div style="font-size:11px;color:var(--primary);margin-top:5px;font-weight:600;">Earned: ${badge.earned_at.split(' ')[0]}</div>` : '<div style="font-size:11px;color:var(--text-muted);margin-top:5px;">Locked</div>'}
                </div>
                ${badge.unlocked ? '<div class="badge-unlocked-status"><i class="fas fa-check-circle"></i></div>' : ''}
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        grid.innerHTML = `<div style="text-align:center;color:var(--accent-red);padding:20px;grid-column: 1 / -1;">Failed to load badges: ${err.message}</div>`;
    }
}

// AI Advisor RAG section
function setupAdvisor() {
    const advForm = document.getElementById('advisor-search-form');
    if (!advForm) return;

    advForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = document.getElementById('advisor-query-input').value;
        loadAdvisorData(query);
    });
}

async function loadAdvisorData(query = null) {
    const wrapper = document.getElementById('advisor-report-wrapper');
    if (!wrapper) return;

    wrapper.innerHTML = '<div class="spinner"></div>';

    try {
        const report = await api.getRecommendations(query);
        
        // Use marked library if available, otherwise write basic custom Markdown parser
        // Fast, simple Markdown parsing for titles, highlights, warning tags
        let parsedHtml = report.advice
            .replace(/## (.*)/g, '<h2>$1</h2>')
            .replace(/### (.*)/g, '<h3>$1</h3>')
            .replace(/#### (.*)/g, '<h4>$1</h4>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/> \[\!WARNING\]\n> (.*)/g, '<blockquote><strong>Warning:</strong> $1</blockquote>')
            .replace(/> \[\!IMPORTANT\]\n> (.*)/g, '<blockquote><strong>Important:</strong> $1</blockquote>')
            .replace(/> (.*)/g, '<blockquote>$1</blockquote>')
            .replace(/\n\n/g, '<p></p>')
            .replace(/- (.*)/g, '<li>$1</li>');
            
        // Close list blocks if list items are inside
        parsedHtml = parsedHtml.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

        wrapper.innerHTML = `<div class="advice-content">${parsedHtml}</div>`;
        
    } catch (err) {
        wrapper.innerHTML = `<div style="text-align:center;color:var(--accent-red);padding:40px;">RAG Advisor failed to compile recommendation: ${err.message}</div>`;
    }
}
