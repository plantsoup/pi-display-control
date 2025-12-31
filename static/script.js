// API base URL
const API_BASE = '';

// Cache for websites
let websitesCache = null;
let isLoading = false;

// Load websites on page load
document.addEventListener('DOMContentLoaded', () => {
    loadWebsites();
    
    // Form submission handler
    document.getElementById('addWebsiteForm').addEventListener('submit', handleAddWebsite);
    
    // Display control buttons
    document.getElementById('stopDisplay').addEventListener('click', handleStopDisplay);
    document.getElementById('wakeDisplay').addEventListener('click', handleWakeDisplay);
    
    // Event delegation for dynamically created buttons
    document.addEventListener('click', handleButtonClick);
});

// Handle button clicks via event delegation
function handleButtonClick(e) {
    const btn = e.target.closest('button');
    if (!btn) return;
    
    const action = btn.dataset.action;
    const index = btn.dataset.index ? parseInt(btn.dataset.index) : null;
    
    if (action === 'start-display' && index !== null) {
        e.preventDefault();
        showMonitorDialog(index);
    } else if (action === 'delete' && index !== null) {
        e.preventDefault();
        deleteWebsite(index);
    }
}

// Load and display websites
async function loadWebsites(force = false) {
    if (isLoading) return;
    
    isLoading = true;
    showLoadingState();
    
    try {
        const response = await fetch(`${API_BASE}/api/websites`, {
            cache: force ? 'no-cache' : 'default'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const websites = await response.json();
        websitesCache = websites;
        displayWebsites(websites);
    } catch (error) {
        showStatus('Error loading websites: ' + error.message, 'error');
        displayErrorState();
    } finally {
        isLoading = false;
        hideLoadingState();
    }
}

// Show loading state
function showLoadingState() {
    const websiteList = document.getElementById('websiteList');
    websiteList.innerHTML = '<div class="loading-skeleton"></div>'.repeat(6);
}

// Hide loading state
function hideLoadingState() {
    // Already handled by displayWebsites
}

// Show error state
function displayErrorState() {
    const websiteList = document.getElementById('websiteList');
    websiteList.innerHTML = '<p style="color: #a0a0a0; text-align: center; padding: 20px;">Error loading websites. Please refresh the page.</p>';
}

// Get favicon URL for a website
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

// Get gradient color based on index
const GRADIENTS = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)'
];

function getGradientColor(index) {
    return GRADIENTS[index % GRADIENTS.length];
}

// Display websites using document fragment for better performance
function displayWebsites(websites) {
    const websiteList = document.getElementById('websiteList');
    
    if (websites.length === 0) {
        websiteList.innerHTML = '<p style="color: #a0a0a0; text-align: center; padding: 20px;">No websites added yet. Add one below!</p>';
        return;
    }
    
    const fragment = document.createDocumentFragment();
    
    websites.forEach((website, index) => {
        const item = document.createElement('div');
        item.className = 'website-item';
        
        const displayUrl = website.url || '(default - Autodarts Board)';
        const isDefault = !website.url || website.is_default;
        const faviconUrl = getFaviconUrl(website.url);
        const gradientColor = getGradientColor(index);
        
        item.innerHTML = `
            <div class="website-image" style="background: ${gradientColor};">
                <div class="favicon">
                    <img src="${faviconUrl}" alt="${escapeHtml(website.name)}" loading="lazy" onerror="this.parentElement.innerHTML='🌐';">
                </div>
            </div>
            <div class="website-content">
                <div class="website-info">
                    <h3>
                        ${escapeHtml(website.name)}
                        ${isDefault ? '<span class="badge">Default</span>' : ''}
                    </h3>
                    <p>${escapeHtml(displayUrl)}</p>
                </div>
                <div class="website-actions">
                    <button class="btn btn-success" data-action="start-display" data-index="${index}">
                        Start Display
                    </button>
                    <button class="btn btn-secondary" data-action="delete" data-index="${index}">
                        Delete
                    </button>
                </div>
            </div>
        `;
        
        fragment.appendChild(item);
    });
    
    websiteList.innerHTML = '';
    websiteList.appendChild(fragment);
}

// Start display with a website
async function startDisplay(index, monitor = 'both', url2 = null) {
    if (!websitesCache || !websitesCache[index]) {
        await loadWebsites(true);
    }
    
    const website = websitesCache[index];
    if (!website) {
        showStatus('Website not found', 'error');
        return;
    }

    const payload = {
        url1: website.url || '',
        monitor: monitor
    };
    
    if ((monitor === 'both' || monitor === '2') && url2 !== null) {
        payload.url2 = url2;
    }

    try {
        setButtonLoading(true);
        const response = await fetch(`${API_BASE}/api/display`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(result.message, 'success');
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error starting display: ' + error.message, 'error');
    } finally {
        setButtonLoading(false);
    }
}

// Set button loading state
function setButtonLoading(loading) {
    document.querySelectorAll('.btn').forEach(btn => {
        btn.disabled = loading;
        if (loading) {
            btn.classList.add('loading');
        } else {
            btn.classList.remove('loading');
        }
    });
}

// Show monitor selection dialog
function showMonitorDialog(index) {
    if (!websitesCache || !websitesCache[index]) {
        loadWebsites(true).then(() => showMonitorDialog(index));
        return;
    }
    
    const website = websitesCache[index];
    if (!website) {
        showStatus('Website not found', 'error');
        return;
    }

    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'monitor-dialog-overlay';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.innerHTML = `
        <div class="monitor-dialog">
            <h3>Select Monitor(s)</h3>
            <p class="dialog-subtitle">Choose where to display: ${escapeHtml(website.name)}</p>
            <div class="monitor-options">
                <button class="btn btn-primary monitor-btn" data-monitor="1" data-index="${index}">
                    Monitor 1 Only
                </button>
                <button class="btn btn-primary monitor-btn" data-monitor="2" data-index="${index}">
                    Monitor 2 Only
                </button>
                <button class="btn btn-primary monitor-btn" data-monitor="both" data-index="${index}">
                    Both Monitors (Same Site)
                </button>
                <button class="btn btn-primary monitor-btn" data-action="dual-dialog" data-index="${index}">
                    Both Monitors (Different Sites)
                </button>
            </div>
            <button class="btn btn-secondary" data-action="close-dialog" style="margin-top: 15px; width: 100%;">
                Cancel
            </button>
        </div>
    `;
    
    // Handle dialog button clicks
    dialog.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) {
            if (e.target === dialog) closeMonitorDialog();
            return;
        }
        
        const monitor = btn.dataset.monitor;
        const action = btn.dataset.action;
        const idx = btn.dataset.index ? parseInt(btn.dataset.index) : null;
        
        if (monitor) {
            startDisplay(idx, monitor);
            closeMonitorDialog();
        } else if (action === 'dual-dialog') {
            showDualMonitorDialog(idx);
        } else if (action === 'close-dialog') {
            closeMonitorDialog();
        }
    });
    
    // Close on Escape key
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeMonitorDialog();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
    
    document.body.appendChild(dialog);
    dialog.focus();
}

// Show dual monitor dialog
function showDualMonitorDialog(index1) {
    if (!websitesCache) {
        loadWebsites(true).then(() => showDualMonitorDialog(index1));
        return;
    }
    
    const website1 = websitesCache[index1];
    if (!website1) {
        showStatus('Website not found', 'error');
        return;
    }

    closeMonitorDialog();

    const dialog = document.createElement('div');
    dialog.className = 'monitor-dialog-overlay';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.innerHTML = `
        <div class="monitor-dialog" style="max-width: 500px;">
            <h3>Dual Monitor Setup</h3>
            <div class="dual-monitor-form">
                <div class="monitor-selection">
                    <label><strong>Monitor 1:</strong></label>
                    <div class="selected-site">${escapeHtml(website1.name)}</div>
                    <small>${escapeHtml(website1.url || 'default (Autodarts)')}</small>
                </div>
                <div class="monitor-selection">
                    <label><strong>Monitor 2:</strong></label>
                    <select id="monitor2Site" class="site-select">
                        ${websitesCache.map((site, idx) => 
                            `<option value="${idx}" ${idx === index1 ? 'selected' : ''}>${escapeHtml(site.name)}</option>`
                        ).join('')}
                    </select>
                </div>
            </div>
            <div class="dialog-actions">
                <button class="btn btn-success" data-action="start-dual" data-index="${index1}">
                    Start Both Monitors
                </button>
                <button class="btn btn-secondary" data-action="close-dialog">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    dialog.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) {
            if (e.target === dialog) closeMonitorDialog();
            return;
        }
        
        const action = btn.dataset.action;
        const idx = btn.dataset.index ? parseInt(btn.dataset.index) : null;
        
        if (action === 'start-dual' && idx !== null) {
            const index2 = parseInt(document.getElementById('monitor2Site').value);
            const website2 = websitesCache[index2];
            if (website2) {
                startDisplay(idx, 'both', website2.url || '');
                closeMonitorDialog();
            }
        } else if (action === 'close-dialog') {
            closeMonitorDialog();
        }
    });
    
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeMonitorDialog();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
    
    document.body.appendChild(dialog);
    dialog.focus();
}

// Close monitor dialog
function closeMonitorDialog() {
    const dialog = document.querySelector('.monitor-dialog-overlay');
    if (dialog) {
        dialog.remove();
    }
}

// Stop display
async function handleStopDisplay() {
    try {
        setButtonLoading(true);
        const response = await fetch(`${API_BASE}/api/display`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(result.message, 'success');
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error blanking display: ' + error.message, 'error');
    } finally {
        setButtonLoading(false);
    }
}

// Wake display
async function handleWakeDisplay() {
    try {
        setButtonLoading(true);
        const response = await fetch(`${API_BASE}/api/display/wake`, {
            method: 'POST'
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(result.message, 'success');
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error waking display: ' + error.message, 'error');
    } finally {
        setButtonLoading(false);
    }
}

// Add new website
async function handleAddWebsite(e) {
    e.preventDefault();
    
    const name = document.getElementById('websiteName').value.trim();
    const url = document.getElementById('websiteUrl').value.trim();

    if (!name) {
        showStatus('Please enter a website name', 'error');
        return;
    }

    try {
        setButtonLoading(true);
        const response = await fetch(`${API_BASE}/api/websites`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, url })
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(`Website "${name}" added successfully!`, 'success');
            document.getElementById('addWebsiteForm').reset();
            websitesCache = result.websites;
            displayWebsites(result.websites);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error adding website: ' + error.message, 'error');
    } finally {
        setButtonLoading(false);
    }
}

// Delete website
async function deleteWebsite(index) {
    if (!confirm('Are you sure you want to delete this website?')) {
        return;
    }

    try {
        setButtonLoading(true);
        const response = await fetch(`${API_BASE}/api/websites/${index}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus('Website deleted successfully', 'success');
            websitesCache = result.websites;
            displayWebsites(result.websites);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error deleting website: ' + error.message, 'error');
    } finally {
        setButtonLoading(false);
    }
}

// Show status message
function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type} show`;
    
    setTimeout(() => {
        statusEl.classList.remove('show');
    }, 4000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
