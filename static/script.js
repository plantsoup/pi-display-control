// API base URL
const API_BASE = '';

// Load websites on page load
document.addEventListener('DOMContentLoaded', () => {
    loadWebsites();
    
    // Form submission handler
    document.getElementById('addWebsiteForm').addEventListener('submit', handleAddWebsite);
    
    // Display control buttons
    document.getElementById('stopDisplay').addEventListener('click', handleStopDisplay);
    document.getElementById('wakeDisplay').addEventListener('click', handleWakeDisplay);
});

// Load and display websites
async function loadWebsites() {
    try {
        const response = await fetch(`${API_BASE}/api/websites`);
        const websites = await response.json();
        displayWebsites(websites);
    } catch (error) {
        showStatus('Error loading websites: ' + error.message, 'error');
    }
}

// Get favicon URL for a website
function getFaviconUrl(url) {
    if (!url || url.trim() === '') {
        // Default favicon for Autodarts
        return 'https://www.google.com/s2/favicons?domain=autodarts.io&sz=128';
    }
    try {
        const domain = new URL(url).hostname;
        return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
    } catch (e) {
        return 'https://www.google.com/s2/favicons?domain=example.com&sz=128';
    }
}

// Get a gradient color based on index for fallback images
function getGradientColor(index) {
    const gradients = [
        'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
        'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)'
    ];
    return gradients[index % gradients.length];
}

// Display websites in the list
function displayWebsites(websites) {
    const websiteList = document.getElementById('websiteList');
    websiteList.innerHTML = '';

    if (websites.length === 0) {
        websiteList.innerHTML = '<p style="color: #a0a0a0; text-align: center; padding: 20px;">No websites added yet. Add one below!</p>';
        return;
    }

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
                    <img src="${faviconUrl}" alt="${escapeHtml(website.name)}" onerror="this.parentElement.innerHTML='🌐';">
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
                    <button class="btn btn-success" onclick="startDisplay(${index})">
                        Start Display
                    </button>
                    <button class="btn btn-secondary" onclick="deleteWebsite(${index})">
                        Delete
                    </button>
                </div>
            </div>
        `;
        
        websiteList.appendChild(item);
    });
}

// Start display with a website
async function startDisplay(index) {
    try {
        const response = await fetch(`${API_BASE}/api/websites`);
        const websites = await response.json();
        const website = websites[index];
        
        if (!website) {
            showStatus('Website not found', 'error');
            return;
        }

        const response2 = await fetch(`${API_BASE}/api/display`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: website.url || ''
            })
        });

        const result = await response2.json();
        
        if (result.success) {
            showStatus(result.message, 'success');
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error starting display: ' + error.message, 'error');
    }
}

// Stop display (blank screen)
async function handleStopDisplay() {
    try {
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
    }
}

// Wake display
async function handleWakeDisplay() {
    try {
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
        const response = await fetch(`${API_BASE}/api/websites`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                url: url
            })
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(`Website "${name}" added successfully!`, 'success');
            document.getElementById('addWebsiteForm').reset();
            displayWebsites(result.websites);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error adding website: ' + error.message, 'error');
    }
}

// Delete website
async function deleteWebsite(index) {
    if (!confirm('Are you sure you want to delete this website?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/websites/${index}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus('Website deleted successfully', 'success');
            displayWebsites(result.websites);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error deleting website: ' + error.message, 'error');
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

