/**
 * YouTube Behavioral Analytics Dashboard - Frontend Controller
 */

// Helper to escape HTML and prevent XSS
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadSection = document.getElementById('upload-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('zip-file-input');
    const reuploadBtn = document.getElementById('reupload-btn');
    
    const progressContainer = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('upload-progress-text');
    const progressPercentage = document.getElementById('upload-percentage');
    
    const statusTag = document.getElementById('status-tag');
    const statusText = document.getElementById('status-text');

    // Chart instances store to destroy/re-create on upload
    let charts = {};

    // Base Chart.js styling overrides for glassmorphism dark theme
    Chart.defaults.color = 'hsl(210, 15%, 70%)'; // --text-secondary
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
    Chart.defaults.plugins.tooltip.borderColor = 'hsla(230, 25%, 30%, 0.5)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleColor = 'hsl(210, 20%, 95%)';
    Chart.defaults.plugins.tooltip.bodyColor = 'hsl(210, 15%, 70%)';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;

    // Define colors matching style.css tokens
    const colors = {
        purple: 'rgb(168, 85, 247)',
        purpleGlow: 'rgba(168, 85, 247, 0.2)',
        blue: 'rgb(59, 130, 246)',
        blueGlow: 'rgba(59, 130, 246, 0.2)',
        green: 'rgb(16, 185, 129)',
        greenGlow: 'rgba(16, 185, 129, 0.2)',
        orange: 'rgb(245, 158, 11)',
        orangeGlow: 'rgba(245, 158, 11, 0.2)',
        red: 'rgb(239, 68, 68)',
        redGlow: 'rgba(239, 68, 68, 0.2)',
        pink: 'rgb(236, 72, 153)',
        pinkGlow: 'rgba(236, 72, 153, 0.2)',
        cyan: 'rgb(6, 182, 212)',
        grey: 'rgb(107, 114, 128)'
    };

    // Initialize Navigation Active Class State (Scrollspy / Clicks)
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });

    // Check if data is already loaded on page load
    const isDataLoaded = !dashboardSection.classList.contains('hidden');
    if (isDataLoaded) {
        loadDashboardData();
    }

    // -------------------------------------------------------------
    // Drag & Drop Functionality
    // -------------------------------------------------------------
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight dropzone on drag enter/over
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('dragover');
        }, false);
    });

    // Unhighlight dropzone on drag leave/drop
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Click to browse file input
    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
    });

    // Validate and upload files
    function handleFiles(files) {
        if (files.length === 0) return;
        const file = files[0];
        
        // Check extension (.zip only)
        if (!file.name.endsWith('.zip')) {
            alert('Error: Please upload a valid Google Takeout .zip archive.');
            return;
        }

        uploadFile(file);
    }

    // -------------------------------------------------------------
    // AJAX Upload with Progress Reporting
    // -------------------------------------------------------------
    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Reset progress bar
        progressContainer.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressPercentage.innerText = '0%';
        progressText.innerText = 'Uploading your archive...';

        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percentComplete + '%';
                progressPercentage.innerText = percentComplete + '%';
                
                if (percentComplete === 100) {
                    progressText.innerText = 'Extracting and parsing history files (this might take a moment)...';
                }
            }
        });

        // Request finished
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                const response = JSON.parse(xhr.responseText);
                progressText.innerText = 'Analysis complete!';
                progressBar.style.width = '100%';
                progressPercentage.innerText = '100%';
                
                // Show success behavior, load dashboard
                setTimeout(() => {
                    progressContainer.classList.add('hidden');
                    uploadSection.classList.add('hidden');
                    dashboardSection.classList.remove('hidden');
                    
                    statusTag.className = 'status-indicator ready';
                    statusText.innerText = 'Data Loaded';
                    
                    loadDashboardData();
                }, 800);
            } else {
                let errorMsg = 'An error occurred during upload.';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMsg = response.error || errorMsg;
                } catch(e) {}
                
                alert('Upload failed: ' + errorMsg);
                progressContainer.classList.add('hidden');
            }
        });

        xhr.addEventListener('error', () => {
            alert('Upload failed: Network error.');
            progressContainer.classList.add('hidden');
        });

        xhr.open('POST', '/upload', true);
        xhr.send(formData);
    }

    // -------------------------------------------------------------
    // Reupload Action
    // -------------------------------------------------------------
    if (reuploadBtn) {
        reuploadBtn.addEventListener('click', () => {
            uploadSection.classList.remove('hidden');
            dashboardSection.classList.add('hidden');
            progressContainer.classList.add('hidden');
            progressBar.style.width = '0%';
            progressPercentage.innerText = '0%';
            fileInput.value = ''; // Clear file input selection
            
            statusTag.className = 'status-indicator pending';
            statusText.innerText = 'No Data Uploaded';
        });
    }

    // -------------------------------------------------------------
    // Load Dashboard Logic
    // -------------------------------------------------------------
    function loadDashboardData() {
        // Fetch core statistics
        fetch('/api/stats')
            .then(res => {
                if (!res.ok) throw new Error('No statistics found');
                return res.json();
            })
            .then(data => {
                populateMetrics(data);
                renderCategoryChart(data.category_counts);
                renderSearchIntentChart(data.search_intents);
                renderComfortTable(data.top_channels);
            })
            .catch(err => {
                console.error('Error fetching statistics:', err);
            });

        // Fetch aggregation charts
        fetch('/api/charts')
            .then(res => {
                if (!res.ok) throw new Error('No chart data found');
                return res.json();
            })
            .then(data => {
                renderVolumeChart(data.volume);
                renderExplorationChart(data.exploration);
                renderHhiChart(data.hhi);
                renderSearchWordsChart(data.search_words);
                renderCircadianHeatmap(data.circadian);
                
                // Set the HHI Concentration value label
                updateHhiLabel(data.hhi.values);
                // Set the Average Novelty discovery rate label
                updateNoveltyLabel(data.exploration.values);
            })
            .catch(err => {
                console.error('Error fetching chart data:', err);
            });
    }

    // -------------------------------------------------------------
    // Populate Dynamic DOM Elements
    // -------------------------------------------------------------
    function populateMetrics(data) {
        document.getElementById('stat-total-watched').innerText = parseInt(data.total_watched).toLocaleString();
        document.getElementById('stat-unique-channels').innerText = parseInt(data.unique_channels).toLocaleString();
        document.getElementById('stat-avg-daily').innerText = parseFloat(data.avg_views_per_day).toFixed(1);
        document.getElementById('stat-binge-sessions').innerText = parseInt(data.binge_sessions).toLocaleString();
        
        // Loop count percentage
        document.getElementById('stat-loop-pct').innerText = parseFloat(data.loop_percentage).toFixed(1) + '%';
        
        // Binge Diagnostic widgets
        const burnoutDaysEl = document.getElementById('stat-burnout-days');
        const burnoutCount = parseInt(data.burnout_alert_days || 0);
        burnoutDaysEl.innerText = `${burnoutCount} days`;
        if (burnoutCount > 0) {
            burnoutDaysEl.className = 'badge badge-danger';
        } else {
            burnoutDaysEl.className = 'badge badge-success';
        }
        
        document.getElementById('stat-subs-overlap').innerText = parseFloat(data.subs_overlap_pct || 0).toFixed(1) + '%';
        document.getElementById('stat-subs-watched').innerText = parseFloat(data.subs_watched_pct || 0).toFixed(1) + '%';
    }

    function updateHhiLabel(hhiValues) {
        if (!hhiValues || hhiValues.length === 0) return;
        const avgHhi = hhiValues.reduce((a, b) => a + b, 0) / hhiValues.length;
        
        const hhiValEl = document.getElementById('stat-avg-hhi');
        
        let rating = '';
        if (avgHhi < 1500) {
            rating = 'Low (Diverse)';
            hhiValEl.style.color = colors.green;
        } else if (avgHhi <= 2500) {
            rating = 'Mod (Stable)';
            hhiValEl.style.color = colors.blue;
        } else {
            rating = 'High (Bubble)';
            hhiValEl.style.color = colors.red;
        }
        
        hhiValEl.innerText = `${Math.round(avgHhi).toLocaleString()} (${rating})`;
    }

    function updateNoveltyLabel(noveltyValues) {
        if (!noveltyValues || noveltyValues.length === 0) return;
        const avgNovelty = noveltyValues.reduce((a, b) => a + b, 0) / noveltyValues.length;
        const pct = avgNovelty * 100;
        
        const noveltyEl = document.getElementById('stat-avg-novelty');
        noveltyEl.innerText = pct.toFixed(1) + '%';
        
        if (pct > 25) {
            noveltyEl.style.color = colors.green;
        } else if (pct >= 10) {
            noveltyEl.style.color = colors.blue;
        } else {
            noveltyEl.style.color = colors.orange;
        }
    }

    function renderComfortTable(channels) {
        const tbody = document.getElementById('comfort-channels-table-body');
        tbody.innerHTML = '';
        
        if (!channels || channels.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center">No comfort channel data available</td></tr>`;
            return;
        }

        channels.forEach((ch, idx) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="comfort-rank">#${idx + 1}</td>
                <td style="font-weight: 500; color: var(--text-primary);">${escapeHtml(ch.channel)}</td>
                <td>${parseInt(ch.views).toLocaleString()}</td>
                <td>${parseInt(ch.loops).toLocaleString()}</td>
                <td><span class="comfort-score-badge">${parseFloat(ch.comfort_score).toFixed(1)}</span></td>
            `;
            tbody.appendChild(row);
        });
    }

    // -------------------------------------------------------------
    // Circadian Heatmap Rendering
    // -------------------------------------------------------------
    function renderCircadianHeatmap(circadian) {
        const grid = document.getElementById('circadian-heatmap-grid');
        grid.innerHTML = '';

        const days = circadian.days;
        const data = circadian.data;

        // Find max value to calibrate opacity
        const maxVal = Math.max(...data.map(d => d.v), 1);

        // 1. Create header row (blank cell + 24 hours)
        const emptyHeader = document.createElement('div');
        emptyHeader.className = 'heatmap-header-cell';
        grid.appendChild(emptyHeader);

        for (let hour = 0; hour < 24; hour++) {
            const hourHeader = document.createElement('div');
            hourHeader.className = 'heatmap-header-cell';
            // Format hour label: 12am, 6am, 12pm, 6pm, etc.
            if (hour === 0) hourHeader.innerText = '12a';
            else if (hour === 12) hourHeader.innerText = '12p';
            else if (hour % 4 === 0) hourHeader.innerText = (hour > 12 ? hour - 12 : hour) + (hour >= 12 ? 'p' : 'a');
            else hourHeader.innerText = '';
            grid.appendChild(hourHeader);
        }

        // 2. Populate cell row-by-row
        days.forEach((dayName, dayIdx) => {
            // Day label
            const labelCell = document.createElement('div');
            labelCell.className = 'heatmap-label';
            labelCell.innerText = dayName.substring(0, 3); // Mon, Tue, etc.
            grid.appendChild(labelCell);

            // 24 Hour cells
            for (let hour = 0; hour < 24; hour++) {
                // Find matching data point
                const dp = data.find(item => item.x === hour && item.y === dayIdx);
                const val = dp ? dp.v : 0;
                
                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';
                
                // Color scale interpolation using purple theme HSL (270, 85%, 65%)
                if (val > 0) {
                    const ratio = val / maxVal;
                    // Scale opacity from 0.15 to 0.95
                    const alpha = 0.15 + (ratio * 0.80);
                    cell.style.backgroundColor = `hsla(270, 85%, 65%, ${alpha})`;
                    cell.style.boxShadow = `0 0 6px hsla(270, 85%, 65%, ${ratio * 0.4})`;
                }

                // Interactive tooltip titles
                cell.title = `${dayName}, ${hour}:00 - ${val.toLocaleString()} videos watched`;
                grid.appendChild(cell);
            }
        });
    }

    // -------------------------------------------------------------
    // Chart.js Graph Initialization & Rendering
    // -------------------------------------------------------------
    
    function initChart(id, config) {
        if (charts[id]) {
            charts[id].destroy();
        }
        const ctx = document.getElementById(id).getContext('2d');
        charts[id] = new Chart(ctx, config);
    }

    // 1. Monthly Volume Bar Chart
    function renderVolumeChart(volume) {
        initChart('chart-volume', {
            type: 'bar',
            data: {
                labels: volume.labels,
                datasets: [{
                    label: 'Videos Watched',
                    data: volume.values,
                    backgroundColor: colors.purpleGlow,
                    borderColor: colors.purple,
                    borderWidth: 1.5,
                    borderRadius: 6,
                    hoverBackgroundColor: colors.purple,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 45, minRotation: 45 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // 2. Categories Doughnut Chart
    function renderCategoryChart(categoriesData) {
        const labels = Object.keys(categoriesData);
        const values = Object.values(categoriesData);
        
        const palette = [
            colors.purple,
            colors.blue,
            colors.green,
            colors.orange,
            colors.red,
            colors.pink,
            colors.cyan,
            colors.grey
        ];

        initChart('chart-categories', {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: palette.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: 'hsl(230, 25%, 10%)', // matches dark card theme border
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: 'hsl(210, 20%, 95%)',
                            boxWidth: 12,
                            padding: 15,
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    // 3. Exploration Score over Time Line Chart
    function renderExplorationChart(exploration) {
        const pctValues = exploration.values.map(v => v * 100);
        
        initChart('chart-exploration', {
            type: 'line',
            data: {
                labels: exploration.labels,
                datasets: [{
                    label: 'Exploration Rate',
                    data: pctValues,
                    borderColor: colors.green,
                    backgroundColor: 'rgba(16, 185, 129, 0.08)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointBackgroundColor: colors.green,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) { return value + '%'; }
                        }
                    }
                }
            }
        });
    }

    // 4. HHI Concentration Line Chart
    function renderHhiChart(hhi) {
        initChart('chart-hhi', {
            type: 'line',
            data: {
                labels: hhi.labels,
                datasets: [{
                    label: 'HHI Concentration',
                    data: hhi.values,
                    borderColor: colors.blue,
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointBackgroundColor: colors.blue,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // 5. Search Intent Classification Doughnut Chart
    function renderSearchIntentChart(intentsData) {
        const labels = Object.keys(intentsData);
        const values = Object.values(intentsData);
        
        // Sum values to check if there is any search data
        const total = values.reduce((a, b) => a + b, 0);
        if (total === 0) {
            // Draw empty state
            initChart('chart-search-intent', {
                type: 'doughnut',
                data: {
                    labels: ['No Search History Found'],
                    datasets: [{
                        data: [1],
                        backgroundColor: ['rgba(255,255,255,0.05)'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '72%',
                    plugins: {
                        legend: { position: 'right', labels: { color: 'hsl(210, 10%, 50%)' } },
                        tooltip: { enabled: false }
                    }
                }
            });
            return;
        }

        const palette = [
            colors.blue,
            colors.purple,
            colors.orange,
            colors.grey
        ];

        initChart('chart-search-intent', {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: palette.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: 'hsl(230, 25%, 10%)',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: 'hsl(210, 20%, 95%)',
                            boxWidth: 12,
                            padding: 15,
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    // 6. Most Frequent Search Terms Horizontal Bar Chart
    function renderSearchWordsChart(searchWords) {
        if (!searchWords || !searchWords.labels || searchWords.labels.length === 0) {
            // Draw empty state on canvas
            const canvas = document.getElementById('chart-search-words');
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '14px Inter, sans-serif';
            ctx.fillStyle = 'hsl(210, 10%, 50%)';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('No search history word clouds available', canvas.width / 2, canvas.height / 2);
            return;
        }

        initChart('chart-search-words', {
            type: 'bar',
            data: {
                labels: searchWords.labels,
                datasets: [{
                    label: 'Word Count',
                    data: searchWords.values,
                    backgroundColor: colors.orangeGlow,
                    borderColor: colors.orange,
                    borderWidth: 1.5,
                    borderRadius: 4,
                    hoverBackgroundColor: colors.orange
                }]
            },
            options: {
                indexAxis: 'y', // Makes it horizontal!
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
    }
});
