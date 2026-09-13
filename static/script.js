/**
 * Pi Display Control & Slideshow Studio
 * Frontend Application Logic
 */

// Global State
let appState = {
    websites: [],
    images: [],
    schedules: [],
    slideshowConfig: {
        mode: 'random',
        interval: 30,
        transition: 'fade',
        fit: 'contain',
        selected_images: []
    }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    setupEventListeners();
    refreshAllData();

    // Poll live status every 10 seconds
    setInterval(fetchLiveStatus, 10000);
});

// -----------------------------------------------------------------------------
// Tab Navigation
// -----------------------------------------------------------------------------
function setupTabNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetContentId = tab.getAttribute('data-tab');
            const targetContent = document.getElementById(targetContentId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

// -----------------------------------------------------------------------------
// Event Listeners Setup
// -----------------------------------------------------------------------------
function setupEventListeners() {
    // Forms
    const addWebsiteForm = document.getElementById('addWebsiteForm');
    if (addWebsiteForm) addWebsiteForm.addEventListener('submit', handleAddWebsite);

    const uploadImageForm = document.getElementById('uploadImageForm');
    if (uploadImageForm) uploadImageForm.addEventListener('submit', handleUploadImage);

    const createScheduleForm = document.getElementById('createScheduleForm');
    if (createScheduleForm) createScheduleForm.addEventListener('submit', handleCreateSchedule);

    // Screen power buttons
    const stopDisplayBtn = document.getElementById('stopDisplay');
    if (stopDisplayBtn) stopDisplayBtn.addEventListener('click', handleBlankDisplay);

    const wakeDisplayBtn = document.getElementById('wakeDisplay');
    if (wakeDisplayBtn) wakeDisplayBtn.addEventListener('click', handleWakeDisplay);
}

// -----------------------------------------------------------------------------
// Data Fetching & Sync
// -----------------------------------------------------------------------------
async function refreshAllData() {
    await Promise.all([
        loadWebsites(),
        loadImages(),
        loadSlideshowConfig(),
        loadSchedules(),
        fetchLiveStatus()
    ]);
    populateMixerOptions();
}

async function fetchLiveStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.success) {
            const state = data.state;
            const badgeText = document.getElementById('liveStatusText');
            const badge = document.getElementById('liveStatusBadge');

            if (state.status === 'blank') {
                badgeText.textContent = 'Screens Off (Blanked)';
                badge.style.color = '#ef4444';
            } else if (state.mode === 'slideshow') {
                badgeText.textContent = `Slideshow Active (${state.monitor || 'both'})`;
                badge.style.color = '#6366f1';
            } else if (state.mode === 'website') {
                badgeText.textContent = `Website Active (${state.monitor || 'both'})`;
                badge.style.color = '#10b981';
            } else if (state.mode === 'mixed') {
                badgeText.textContent = `Mixed Display Active (${state.monitor || 'both'})`;
                badge.style.color = '#8b5cf6';
            } else {
                badgeText.textContent = 'Display Active';
                badge.style.color = '#10b981';
            }
        }
    } catch (err) {
        console.error('Error fetching live status:', err);
    }
}

// -----------------------------------------------------------------------------
// Dual Monitor Mixer (Independent Screen Control)
// -----------------------------------------------------------------------------
function onMixerTypeChange(monId) {
    const typeSelect = document.getElementById(`mixerMon${monId}Type`);
    const websiteBox = document.getElementById(`mixerMon${monId}WebsiteBox`);
    const imageBox = document.getElementById(`mixerMon${monId}ImageBox`);
    const slideshowBox = document.getElementById(`mixerMon${monId}SlideshowBox`);

    const type = typeSelect ? typeSelect.value : 'website';

    if (type === 'website') {
        if (websiteBox) websiteBox.style.display = 'block';
        if (imageBox) imageBox.style.display = 'none';
        if (slideshowBox) slideshowBox.style.display = 'none';
    } else if (type === 'image') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'block';
        if (slideshowBox) slideshowBox.style.display = 'none';
    } else if (type === 'slideshow') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'none';
        if (slideshowBox) slideshowBox.style.display = 'block';
    }
}

function populateMixerOptions() {
    ['1', '2'].forEach(monId => {
        // Websites dropdown
        const webSelect = document.getElementById(`mixerMon${monId}Website`);
        if (webSelect) {
            webSelect.innerHTML = appState.websites.map(w => 
                `<option value="${escapeHtml(w.url || '')}">${escapeHtml(w.name)} (${w.url ? escapeHtml(w.url) : 'Autodarts default'})</option>`
            ).join('');
        }

        // Images dropdown
        const imgSelect = document.getElementById(`mixerMon${monId}Image`);
        if (imgSelect) {
            if (appState.images.length === 0) {
                imgSelect.innerHTML = '<option value="">(No uploaded images)</option>';
            } else {
                imgSelect.innerHTML = appState.images.map(img => 
                    `<option value="${escapeHtml(img.filename)}">${escapeHtml(img.name)}</option>`
                ).join('');
            }
        }
    });
}

function getMonitorTargetObject(monId) {
    const type = document.getElementById(`mixerMon${monId}Type`).value;
    if (type === 'website') {
        const url = document.getElementById(`mixerMon${monId}Website`).value;
        return { type: 'website', url: url };
    } else if (type === 'image') {
        const img = document.getElementById(`mixerMon${monId}Image`).value;
        return { type: 'image', image: img };
    } else if (type === 'slideshow') {
        return {
            type: 'slideshow',
            mode: appState.slideshowConfig.mode,
            interval: appState.slideshowConfig.interval
        };
    }
    return { type: 'website', url: '' };
}

async function applyDualMixer() {
    const target1 = getMonitorTargetObject('1');
    const target2 = getMonitorTargetObject('2');

    try {
        showToast('Applying mixed setup to both monitors...', 'info');
        const res = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                monitor: 'both',
                monitor1: target1,
                monitor2: target2
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Dual monitor setup updated!', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error applying setup: ' + err.message, 'error');
    }
}

async function applySingleMonitor(monId) {
    const target = getMonitorTargetObject(monId);

    try {
        showToast(`Updating Monitor ${monId}...`, 'info');
        const payload = {
            monitor: monId
        };
        if (monId === '1') {
            payload.monitor1 = target;
        } else {
            payload.monitor2 = target;
        }

        const res = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Monitor ${monId} updated!`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast(`Error updating Monitor ${monId}: ` + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Slideshow Studio Controller
// -----------------------------------------------------------------------------
async function loadSlideshowConfig() {
    try {
        const res = await fetch('/api/slideshow');
        const data = await res.json();
        if (data.success && data.config) {
            appState.slideshowConfig = data.config;
            renderSlideshowControls();
        }
    } catch (err) {
        console.error('Error loading slideshow config:', err);
    }
}

function renderSlideshowControls() {
    const cfg = appState.slideshowConfig;

    // Segmented buttons
    const randomBtn = document.getElementById('modeRandomBtn');
    const sequentialBtn = document.getElementById('modeSequentialBtn');
    if (cfg.mode === 'random') {
        randomBtn?.classList.add('active');
        sequentialBtn?.classList.remove('active');
    } else {
        sequentialBtn?.classList.add('active');
        randomBtn?.classList.remove('active');
    }

    // Interval selector
    const intervalSelect = document.getElementById('slideshowInterval');
    if (intervalSelect) intervalSelect.value = cfg.interval || 30;

    // Fit mode
    const fitSelect = document.getElementById('slideshowFit');
    if (fitSelect) fitSelect.value = cfg.fit || 'contain';

    // Transition
    const transSelect = document.getElementById('slideshowTransition');
    if (transSelect) transSelect.value = cfg.transition || 'fade';

    updateSlideshowSummaryText();
}

function updateSlideshowSummaryText() {
    const cfg = appState.slideshowConfig;
    const summaryText = document.getElementById('slideshowSummaryText');
    if (summaryText) {
        const modeLabel = cfg.mode === 'random' ? 'Random Shuffle' : 'Sequential';
        const intervalText = cfg.interval >= 60 ? `${cfg.interval / 60}m` : `${cfg.interval}s`;
        const count = cfg.selected_images && cfg.selected_images.length > 0 
            ? `${cfg.selected_images.length} selected images` 
            : 'All uploaded images';
        summaryText.textContent = `${modeLabel} every ${intervalText} (${count})`;
    }
}

async function setSlideshowMode(mode) {
    appState.slideshowConfig.mode = mode;
    renderSlideshowControls();
    await saveSlideshowConfigChanges();
}

async function updateSlideshowSetting(key, value) {
    appState.slideshowConfig[key] = key === 'interval' ? parseInt(value) : value;
    updateSlideshowSummaryText();
    await saveSlideshowConfigChanges();
}

async function saveSlideshowConfigChanges() {
    try {
        await fetch('/api/slideshow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appState.slideshowConfig)
        });
    } catch (err) {
        showToast('Error saving slideshow settings: ' + err.message, 'error');
    }
}

async function launchSlideshow(monitor = 'both') {
    if (appState.images.length === 0) {
        showToast('Please upload at least one image before starting slideshow', 'error');
        return;
    }

    try {
        showToast(`Launching ${appState.slideshowConfig.mode} slideshow on ${monitor} monitor(s)...`, 'info');

        const res = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: 'slideshow',
                monitor: monitor,
                interval: appState.slideshowConfig.interval,
                slideshow_mode: appState.slideshowConfig.mode
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Slideshow started successfully!', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error starting slideshow: ' + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Image Library & Uploads
// -----------------------------------------------------------------------------
async function loadImages() {
    try {
        const res = await fetch('/api/images');
        const images = await res.json();
        appState.images = images;
        document.getElementById('imageCountBadge').textContent = images.length;
        renderImagesGrid();
        populateMixerOptions();
    } catch (err) {
        showToast('Error loading images: ' + err.message, 'error');
    }
}

function renderImagesGrid() {
    const list = document.getElementById('imageList');
    if (!list) return;

    list.innerHTML = '';
    if (appState.images.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">No images uploaded yet. Upload images above to start your slideshow!</div>';
        return;
    }

    const selectedIds = new Set(appState.slideshowConfig.selected_images || []);

    appState.images.forEach((img, idx) => {
        const isSelected = selectedIds.size === 0 || selectedIds.has(img.id);
        const card = document.createElement('div');
        card.className = `image-card ${isSelected ? 'selected' : ''}`;
        
        card.innerHTML = `
            <div class="image-thumbnail-box">
                <img src="/api/images/${img.filename}" alt="${escapeHtml(img.name)}" loading="lazy">
            </div>
            <div class="image-meta">
                <h4>${escapeHtml(img.name)}</h4>
                <p>${escapeHtml(img.original_filename || '')}</p>
            </div>
            <div class="image-card-actions">
                <button class="btn btn-xs btn-primary" onclick="displaySingleImage('${img.filename}', 'both')" title="Show on both monitors">
                    🚀 Both
                </button>
                <button class="btn btn-xs btn-secondary" onclick="displaySingleImage('${img.filename}', '1')" title="Show on Monitor 1 only">
                    🖥️ M1
                </button>
                <button class="btn btn-xs btn-secondary" onclick="displaySingleImage('${img.filename}', '2')" title="Show on Monitor 2 only">
                    🖥️ M2
                </button>
                <button class="btn btn-xs btn-danger" onclick="deleteImage(${idx})" title="Delete image">
                    🗑️
                </button>
            </div>
        `;
        list.appendChild(card);
    });
}

async function handleUploadImage(e) {
    e.preventDefault();
    const nameInput = document.getElementById('imageName');
    const fileInput = document.getElementById('imageFile');
    const submitBtn = document.getElementById('uploadSubmitBtn');

    if (!fileInput.files[0]) {
        showToast('Please select a file to upload', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('name', nameInput.value.trim());
    formData.append('file', fileInput.files[0]);

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading...';

        const res = await fetch('/api/images', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            showToast(`Image "${nameInput.value}" uploaded successfully!`, 'success');
            document.getElementById('uploadImageForm').reset();
            appState.images = data.images;
            document.getElementById('imageCountBadge').textContent = data.images.length;
            renderImagesGrid();
            populateMixerOptions();
        } else {
            showToast('Upload error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error uploading: ' + err.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload Image';
    }
}

async function displaySingleImage(filename, monitor = 'both') {
    try {
        showToast(`Displaying image on ${monitor} monitor(s)...`, 'info');
        const payload = {
            mode: 'image',
            monitor: monitor
        };
        if (monitor === '1') {
            payload.image1 = filename;
        } else if (monitor === '2') {
            payload.image2 = filename;
        } else {
            payload.image1 = filename;
            payload.image2 = filename;
        }

        const res = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Image displayed on ${monitor} monitor(s)`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error displaying image: ' + err.message, 'error');
    }
}

async function deleteImage(index) {
    if (!confirm('Are you sure you want to delete this image?')) return;

    try {
        const res = await fetch(`/api/images/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Image deleted successfully', 'success');
            appState.images = data.images;
            document.getElementById('imageCountBadge').textContent = data.images.length;
            renderImagesGrid();
            populateMixerOptions();
        } else {
            showToast('Error deleting: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error deleting image: ' + err.message, 'error');
    }
}

function selectAllImages(selectAll) {
    if (selectAll) {
        appState.slideshowConfig.selected_images = appState.images.map(i => i.id);
    } else {
        appState.slideshowConfig.selected_images = [];
    }
    saveSlideshowConfigChanges();
    renderImagesGrid();
    updateSlideshowSummaryText();
    showToast(selectAll ? 'All images selected for slideshow' : 'Selection cleared (all images enabled)', 'info');
}

// -----------------------------------------------------------------------------
// Websites & Autodarts
// -----------------------------------------------------------------------------
async function loadWebsites() {
    try {
        const res = await fetch('/api/websites');
        const websites = await res.json();
        appState.websites = websites;
        document.getElementById('websiteCountBadge').textContent = websites.length;
        renderWebsitesGrid();
        populateWebsiteOptions();
        populateMixerOptions();
    } catch (err) {
        showToast('Error loading websites: ' + err.message, 'error');
    }
}

function getFaviconUrl(url) {
    if (!url || url.trim() === '') {
        return 'https://www.google.com/s2/favicons?domain=autodarts.io&sz=128';
    }
    try {
        const domain = new URL(url).hostname;
        return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
    } catch (e) {
        return 'https://www.google.com/s2/favicons?domain=example.com&sz=128';
    }
}

function renderWebsitesGrid() {
    const list = document.getElementById('websiteList');
    if (!list) return;

    list.innerHTML = '';
    if (appState.websites.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">No websites saved yet.</div>';
        return;
    }

    appState.websites.forEach((site, idx) => {
        const isDefault = !site.url || site.is_default;
        const favicon = getFaviconUrl(site.url);

        const card = document.createElement('div');
        card.className = 'website-card';
        card.innerHTML = `
            <div class="website-header">
                <div class="website-favicon">
                    <img src="${favicon}" alt="${escapeHtml(site.name)}" onerror="this.parentElement.innerHTML='🌐';">
                </div>
                <div class="website-info">
                    <h4>
                        ${escapeHtml(site.name)}
                        ${isDefault ? '<span class="website-badge">Default</span>' : ''}
                    </h4>
                    <p>${escapeHtml(site.url || 'Autodarts Board Kiosk')}</p>
                </div>
            </div>
            <div class="website-actions">
                <button class="btn btn-sm btn-primary" onclick="launchWebsite(${idx}, 'both')">
                    🚀 Both Displays
                </button>
                <button class="btn btn-sm btn-secondary" onclick="launchWebsite(${idx}, '1')">
                    🖥️ Monitor 1
                </button>
                <button class="btn btn-sm btn-secondary" onclick="launchWebsite(${idx}, '2')">
                    🖥️ Monitor 2
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteWebsite(${idx})">
                    🗑️ Delete
                </button>
            </div>
        `;
        list.appendChild(card);
    });
}

async function handleAddWebsite(e) {
    e.preventDefault();
    const name = document.getElementById('websiteName').value.trim();
    const url = document.getElementById('websiteUrl').value.trim();

    try {
        const res = await fetch('/api/websites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Website "${name}" saved!`, 'success');
            document.getElementById('addWebsiteForm').reset();
            appState.websites = data.websites;
            document.getElementById('websiteCountBadge').textContent = data.websites.length;
            renderWebsitesGrid();
            populateWebsiteOptions();
            populateMixerOptions();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error adding website: ' + err.message, 'error');
    }
}

async function launchWebsite(index, monitor = 'both') {
    const site = appState.websites[index];
    if (!site) return;

    try {
        showToast(`Launching ${site.name} on ${monitor} monitor(s)...`, 'info');
        const payload = {
            mode: 'website',
            monitor: monitor
        };
        if (monitor === '1') {
            payload.url1 = site.url || '';
        } else if (monitor === '2') {
            payload.url2 = site.url || '';
        } else {
            payload.url1 = site.url || '';
            payload.url2 = site.url || '';
        }

        const res = await fetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Website launched successfully', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error launching website: ' + err.message, 'error');
    }
}

async function deleteWebsite(index) {
    if (!confirm('Are you sure you want to delete this website?')) return;

    try {
        const res = await fetch(`/api/websites/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Website deleted', 'success');
            appState.websites = data.websites;
            document.getElementById('websiteCountBadge').textContent = data.websites.length;
            renderWebsitesGrid();
            populateWebsiteOptions();
            populateMixerOptions();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error deleting website: ' + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Time-based Scheduler
// -----------------------------------------------------------------------------
async function loadSchedules() {
    try {
        const res = await fetch('/api/schedules');
        const schedules = await res.json();
        appState.schedules = schedules;
        document.getElementById('scheduleCountBadge').textContent = schedules.length;
        renderSchedulesList();
    } catch (err) {
        showToast('Error loading schedules: ' + err.message, 'error');
    }
}

function renderSchedulesList() {
    const list = document.getElementById('schedulesList');
    if (!list) return;

    list.innerHTML = '';
    if (appState.schedules.length === 0) {
        list.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No automated schedules set up yet. Click "New Schedule" above to add one!</div>';
        return;
    }

    appState.schedules.forEach(sch => {
        const row = document.createElement('div');
        row.className = 'schedule-row';

        let actionDesc = sch.action;
        if (sch.action === 'slideshow') {
            const mode = (sch.params && sch.params.mode) || 'random';
            const interval = (sch.params && sch.params.interval) || 30;
            actionDesc = `Start ${mode} slideshow (every ${interval}s)`;
        } else if (sch.action === 'website') {
            actionDesc = `Switch to website/Autodarts`;
        } else if (sch.action === 'blank') {
            actionDesc = `Blank screen (Sleep)`;
        } else if (sch.action === 'wake') {
            actionDesc = `Wake screen (Turn on)`;
        }

        row.innerHTML = `
            <div class="schedule-time-box">
                <div class="schedule-time">${escapeHtml(sch.time)}</div>
                <div class="schedule-info">
                    <h4>${escapeHtml(sch.name)}</h4>
                    <p>${actionDesc} &bull; Target: ${sch.params?.monitor || 'both'}</p>
                </div>
            </div>
            <div class="schedule-controls">
                <label class="switch" title="Toggle active/inactive">
                    <input type="checkbox" ${sch.enabled ? 'checked' : ''} onchange="toggleSchedule('${sch.id}')">
                    <span class="slider"></span>
                </label>
                <button class="btn btn-xs btn-danger" onclick="deleteSchedule('${sch.id}')" title="Delete schedule">
                    🗑️
                </button>
            </div>
        `;
        list.appendChild(row);
    });
}

function openAddScheduleModal() {
    document.getElementById('scheduleModal').style.display = 'flex';
}

function closeScheduleModal() {
    document.getElementById('scheduleModal').style.display = 'none';
}

function onScheduleActionChange() {
    const action = document.getElementById('scheduleAction').value;
    const slideshowOptions = document.getElementById('scheduleSlideshowOptions');
    const websiteOptions = document.getElementById('scheduleWebsiteOptions');
    const monitorGroup = document.getElementById('scheduleMonitorGroup');

    if (action === 'slideshow') {
        slideshowOptions.style.display = 'block';
        websiteOptions.style.display = 'none';
        monitorGroup.style.display = 'block';
    } else if (action === 'website') {
        slideshowOptions.style.display = 'none';
        websiteOptions.style.display = 'block';
        monitorGroup.style.display = 'block';
    } else {
        slideshowOptions.style.display = 'none';
        websiteOptions.style.display = 'none';
        monitorGroup.style.display = 'none';
    }
}

function populateWebsiteOptions() {
    const picker = document.getElementById('scheduleWebsitePicker');
    if (!picker) return;
    picker.innerHTML = appState.websites.map(w => 
        `<option value="${escapeHtml(w.url || '')}">${escapeHtml(w.name)}</option>`
    ).join('');
}

async function handleCreateSchedule(e) {
    e.preventDefault();
    const name = document.getElementById('scheduleName').value.trim();
    const timeVal = document.getElementById('scheduleTime').value.trim();
    const action = document.getElementById('scheduleAction').value;
    const monitor = document.getElementById('scheduleMonitor').value;

    const params = { monitor: monitor };

    if (action === 'slideshow') {
        params.mode = document.getElementById('scheduleSlideshowMode').value;
        params.interval = parseInt(document.getElementById('scheduleSlideshowInterval').value) || 30;
    } else if (action === 'website') {
        params.url1 = document.getElementById('scheduleWebsitePicker').value;
    }

    try {
        const res = await fetch('/api/schedules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                time: timeVal,
                action: action,
                params: params
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Schedule created successfully!', 'success');
            closeScheduleModal();
            document.getElementById('createScheduleForm').reset();
            appState.schedules = data.schedules;
            document.getElementById('scheduleCountBadge').textContent = data.schedules.length;
            renderSchedulesList();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error saving schedule: ' + err.message, 'error');
    }
}

async function toggleSchedule(scheduleId) {
    try {
        const res = await fetch(`/api/schedules/${scheduleId}/toggle`, { method: 'PUT' });
        const data = await res.json();
        if (data.success) {
            appState.schedules = data.schedules;
            renderSchedulesList();
        }
    } catch (err) {
        showToast('Error toggling schedule: ' + err.message, 'error');
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
        const res = await fetch(`/api/schedules/${scheduleId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Schedule deleted', 'success');
            appState.schedules = data.schedules;
            document.getElementById('scheduleCountBadge').textContent = data.schedules.length;
            renderSchedulesList();
        }
    } catch (err) {
        showToast('Error deleting schedule: ' + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Screen Wake / Blank Handlers
// -----------------------------------------------------------------------------
async function handleBlankDisplay() {
    try {
        showToast('Turning screens off...', 'info');
        const res = await fetch('/api/display', { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Displays blanked (screens turned off)', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error blanking display: ' + err.message, 'error');
    }
}

async function handleWakeDisplay() {
    try {
        showToast('Waking screens...', 'info');
        const res = await fetch('/api/display/wake', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('Displays woken up', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error waking display: ' + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Toast Notifications & Helpers
// -----------------------------------------------------------------------------
let toastTimeout;
function showToast(message, type = 'info') {
    const toast = document.getElementById('statusMessage');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast-notification ${type} show`;

    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
