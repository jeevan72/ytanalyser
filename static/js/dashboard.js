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
    const processingSection = document.getElementById('processing-section');
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
        
        const zipFiles = [];
        for (let i = 0; i < files.length; i++) {
            if (!files[i].name.endsWith('.zip')) {
                alert(`Error: File "${files[i].name}" is not a valid Google Takeout .zip archive.`);
                return;
            }
            zipFiles.push(files[i]);
        }

        uploadFiles(zipFiles);
    }

    // Processing Checklist Step State Management
    function setStepState(stepId, state) {
        const el = document.getElementById(stepId);
        if (!el) return;
        
        const icon = el.querySelector('.step-icon');
        
        if (state === 'pending') {
            el.className = 'step-item pending';
            if (icon) icon.className = 'fa-solid fa-circle-notch step-icon';
        } else if (state === 'active') {
            el.className = 'step-item';
            if (icon) icon.className = 'fa-solid fa-spinner fa-spin step-icon';
        } else if (state === 'completed') {
            el.className = 'step-item completed';
            if (icon) icon.className = 'fa-solid fa-circle-check step-icon';
        }
    }

    // -------------------------------------------------------------
    // AJAX Upload with Progress Reporting & Checklist Transitions
    // -------------------------------------------------------------
    function uploadFiles(files) {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('file', file);
        });

        // Hide upload view and show processing steps
        uploadSection.classList.add('hidden');
        processingSection.classList.remove('hidden');

        // Reset checklist steps states
        setStepState('step-upload', 'active');
        setStepState('step-extract', 'pending');
        setStepState('step-parse', 'pending');
        setStepState('step-nlp', 'pending');
        setStepState('step-compile', 'pending');

        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                const uploadText = document.getElementById('step-upload').querySelector('span');
                if (uploadText) {
                    uploadText.innerText = `Uploading archive files (${percentComplete}%)...`;
                }
            }
        });

        // Request finished
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                // Upload step done
                setStepState('step-upload', 'completed');
                const uploadText = document.getElementById('step-upload').querySelector('span');
                if (uploadText) uploadText.innerText = 'Uploading archive files...';
                
                // Animate through extract -> parse -> nlp -> compile sequentially
                setStepState('step-extract', 'active');
                
                setTimeout(() => {
                    setStepState('step-extract', 'completed');
                    setStepState('step-parse', 'active');
                }, 800);
                
                setTimeout(() => {
                    setStepState('step-parse', 'completed');
                    setStepState('step-nlp', 'active');
                }, 1600);
                
                setTimeout(() => {
                    setStepState('step-nlp', 'completed');
                    setStepState('step-compile', 'active');
                }, 2400);
                
                setTimeout(() => {
                    setStepState('step-compile', 'completed');
                }, 3200);
                
                setTimeout(() => {
                    processingSection.classList.add('hidden');
                    dashboardSection.classList.remove('hidden');
                    
                    statusTag.className = 'status-indicator ready';
                    statusText.innerText = 'Data Loaded';
                    
                    loadDashboardData();
                }, 4000);
            } else {
                let errorMsg = 'An error occurred during upload.';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMsg = response.error || errorMsg;
                } catch(e) {}
                
                alert('Upload failed: ' + errorMsg);
                processingSection.classList.add('hidden');
                uploadSection.classList.remove('hidden');
            }
        });

        xhr.addEventListener('error', () => {
            alert('Upload failed: Network error.');
            processingSection.classList.add('hidden');
            uploadSection.classList.remove('hidden');
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
            processingSection.classList.add('hidden');
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
                renderYoYChart(data.yoy_trend);
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
        
        // Estimated Hours and Date Range
        document.getElementById('stat-total-hours').innerText = parseFloat(data.estimated_hours || 0).toFixed(1) + ' hrs';
        document.getElementById('stat-hours-desc').innerText = `From ${data.watch_start_date || 'N/A'} to ${data.watch_end_date || 'N/A'}`;
        
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

        // Late Night Binging Index
        const lateNightEl = document.getElementById('stat-late-night');
        const lateNightPct = parseFloat(data.late_night_pct || 0);
        lateNightEl.innerText = lateNightPct.toFixed(1) + '%';
        if (lateNightPct > 35) {
            lateNightEl.className = 'badge badge-danger';
        } else if (lateNightPct > 20) {
            lateNightEl.className = 'badge badge-warning';
        } else {
            lateNightEl.className = 'badge badge-success';
        }

        // Focus vs. Distraction Index
        const focusScoreEl = document.getElementById('stat-focus-score');
        const focusRatingEl = document.getElementById('stat-focus-rating');
        const focusScore = parseFloat(data.focus_score || 0);
        focusScoreEl.innerText = focusScore.toFixed(1) + '%';
        if (focusScore >= 70) {
            focusRatingEl.innerText = 'High Focus';
            focusRatingEl.className = 'badge badge-success';
            focusRatingEl.style.backgroundColor = colors.greenGlow;
            focusRatingEl.style.color = colors.green;
            focusRatingEl.style.border = `1px solid hsla(150, 75%, 50%, 0.2)`;
        } else if (focusScore >= 40) {
            focusRatingEl.innerText = 'Moderate Focus';
            focusRatingEl.className = 'badge badge-warning';
            focusRatingEl.style.backgroundColor = colors.orangeGlow;
            focusRatingEl.style.color = colors.orange;
            focusRatingEl.style.border = `1px solid hsla(30, 90%, 55%, 0.2)`;
        } else {
            focusRatingEl.innerText = 'Distracted';
            focusRatingEl.className = 'badge badge-danger';
            focusRatingEl.style.backgroundColor = colors.redGlow;
            focusRatingEl.style.color = colors.red;
            focusRatingEl.style.border = `1px solid hsla(355, 80%, 55%, 0.2)`;
        }

        // Longest Binge Sitting Record
        const binge = data.longest_binge || {};
        document.getElementById('binge-record-videos').innerText = parseInt(binge.video_count || 0).toLocaleString();
        document.getElementById('binge-record-duration').innerText = `${parseInt(binge.duration_mins || 0)} mins`;
        document.getElementById('binge-record-date').innerText = binge.date || 'N/A';
        
        const bingeLink = document.getElementById('binge-record-channel-link');
        bingeLink.innerText = binge.primary_channel || 'Unknown';
        bingeLink.href = binge.primary_channel_url || '#';

        // Nostalgia Channels
        populateNostalgia(data.nostalgia_channels);
        
        // Repeat Videos
        populateRepeatVideos(data.top_videos);
        
        // Ghost Subscriptions
        populateGhostSubscriptions(data.ghost_subscriptions, data.ghost_count);
    }

    function populateNostalgia(channels) {
        const container = document.getElementById('nostalgia-container');
        container.innerHTML = '';
        if (!channels || channels.length === 0) {
            container.innerHTML = `<li class="text-center" style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem 0;">No nostalgia channels found</li>`;
            return;
        }
        
        channels.forEach(ch => {
            const li = document.createElement('li');
            li.className = 'nostalgia-item';
            li.innerHTML = `
                <a href="${escapeHtml(ch.channel_url)}" target="_blank" class="nostalgia-channel-link">${escapeHtml(ch.channel)} <i class="fa-solid fa-external-link" style="font-size: 0.7rem; margin-left: 3px; color: var(--text-muted);"></i></a>
                <span class="nostalgia-meta"><i class="fa-solid fa-clock-rotate-left"></i> ${ch.past_views} past views</span>
            `;
            container.appendChild(li);
        });
    }

    function populateRepeatVideos(videos) {
        const container = document.getElementById('repeat-videos-container');
        container.innerHTML = '';
        if (!videos || videos.length === 0) {
            container.innerHTML = `<div class="text-center" style="color: var(--text-muted); font-size: 0.85rem; padding: 1.5rem 0;">No repeat video data available</div>`;
            return;
        }
        
        videos.forEach(vid => {
            const div = document.createElement('div');
            div.className = 'repeat-video-item';
            div.innerHTML = `
                <div class="repeat-video-main">
                    <a href="${escapeHtml(vid.url)}" target="_blank" class="repeat-video-title">${escapeHtml(vid.title)} <i class="fa-solid fa-external-link" style="font-size: 0.75rem; margin-left: 4px; color: var(--text-muted);"></i></a>
                    <div class="repeat-video-channel">
                        <span>by <a href="${escapeHtml(vid.channel_url)}" target="_blank" class="premium-link" style="color: var(--text-secondary); text-decoration: underline;">${escapeHtml(vid.channel)}</a></span>
                        <span class="badge ${vid.is_subscribed ? 'badge-subbed' : 'badge-unsubbed'}">${vid.is_subscribed ? '<i class="fa-solid fa-bell"></i> Subscribed' : '<i class="fa-solid fa-bell-slash"></i> Not Subscribed'}</span>
                    </div>
                </div>
                <div class="repeat-video-meta">
                    <span class="repeat-watch-count">${vid.watch_count}</span>
                    <span class="repeat-watch-label">plays</span>
                </div>
            `;
            container.appendChild(div);
        });
    }

    function populateGhostSubscriptions(subs, count) {
        document.getElementById('ghost-subs-count').innerText = count;
        const container = document.getElementById('ghost-subs-container');
        container.innerHTML = '';
        if (!subs || subs.length === 0) {
            container.innerHTML = `<li class="text-center" style="color: var(--text-muted); font-size: 0.85rem; padding: 1.5rem 0;">No ghost subscriptions found! Active viewer!</li>`;
            return;
        }
        
        subs.forEach(sub => {
            const li = document.createElement('li');
            li.className = 'ghost-sub-item';
            li.innerHTML = `
                <a href="${escapeHtml(sub.channel_url)}" target="_blank" class="ghost-sub-channel-link">${escapeHtml(sub.channel)} <i class="fa-solid fa-external-link" style="font-size: 0.7rem; margin-left: 3px; color: var(--text-muted);"></i></a>
                <span class="ghost-badge"><i class="fa-solid fa-eye-slash"></i> 0 views</span>
            `;
            container.appendChild(li);
        });
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
            tbody.innerHTML = `<tr><td colspan="6" class="text-center">No comfort channel data available</td></tr>`;
            return;
        }

        channels.forEach((ch, idx) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="comfort-rank">#${idx + 1}</td>
                <td style="font-weight: 500;">
                    <a href="${escapeHtml(ch.channel_url)}" target="_blank" class="premium-link" style="color: var(--text-primary); text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                        ${escapeHtml(ch.channel)}
                        <i class="fa-solid fa-external-link" style="font-size: 0.7rem; color: var(--text-muted);"></i>
                    </a>
                </td>
                <td>${parseInt(ch.views).toLocaleString()}</td>
                <td>${parseInt(ch.loops).toLocaleString()}</td>
                <td><span class="comfort-score-badge">${parseFloat(ch.comfort_score).toFixed(1)}</span></td>
                <td>
                    <span class="badge ${ch.is_subscribed ? 'badge-subbed' : 'badge-unsubbed'}">
                        ${ch.is_subscribed ? '<i class="fa-solid fa-bell" style="margin-right: 4px;"></i> Subscribed' : '<i class="fa-solid fa-bell-slash" style="margin-right: 4px;"></i> Not Subscribed'}
                    </span>
                </td>
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
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
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
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '14px Inter, sans-serif';
                ctx.fillStyle = 'hsl(210, 10%, 50%)';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('No search history word clouds available', canvas.width / 2, canvas.height / 2);
            }
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

    // 7. YoY Activity Trends Line Chart
    function renderYoYChart(yoyTrend) {
        if (!yoyTrend || Object.keys(yoyTrend).length === 0) {
            const canvas = document.getElementById('chart-yoy');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '14px Inter, sans-serif';
                ctx.fillStyle = 'hsl(210, 10%, 50%)';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('No YoY activity trend data available', canvas.width / 2, canvas.height / 2);
            }
            return;
        }

        const years = Object.keys(yoyTrend).sort();
        const counts = years.map(y => yoyTrend[y]);

        initChart('chart-yoy', {
            type: 'line',
            data: {
                labels: years,
                datasets: [{
                    label: 'Videos Watched',
                    data: counts,
                    borderColor: colors.purple,
                    backgroundColor: colors.purpleGlow,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointBackgroundColor: colors.purple,
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
});
