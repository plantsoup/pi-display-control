// API base URL
const API_BASE = '';

// Load websites on page load
document.addEventListener('DOMContentLoaded', () => {
    loadWebsites();
    loadImages();
    
    // Form submission handler
    document.getElementById('addWebsiteForm').addEventListener('submit', handleAddWebsite);
    document.getElementById('uploadImageForm').addEventListener('submit', handleUploadImage);
    
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
                    <button class="btn btn-success" onclick="showMonitorDialog(${index})">
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
async function startDisplay(index, monitor = 'both', url2 = null) {
    try {
        const response = await fetch(`${API_BASE}/api/websites`);
        const websites = await response.json();
        const website = websites[index];
        
        if (!website) {
            showStatus('Website not found', 'error');
            return;
        }

        const payload = {
            url1: website.url || '',
            monitor: monitor
        };
        
        // If dual monitor mode and url2 is provided, use it
        if (monitor === 'both' && url2 !== null) {
            payload.url2 = url2;
        } else if (monitor === '2' && url2 !== null) {
            payload.url2 = url2;
        }

        const response2 = await fetch(`${API_BASE}/api/display`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
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

// Show monitor selection dialog
function showMonitorDialog(index) {
    Promise.all([
        fetch(`${API_BASE}/api/websites`).then(res => res.json()),
        fetch(`${API_BASE}/api/images`).then(res => res.json())
    ])
        .then(([websites, images]) => {
            const website = websites[index];
            if (!website) {
                showStatus('Website not found', 'error');
                return;
            }

            // Create dialog
            const dialog = document.createElement('div');
            dialog.className = 'monitor-dialog-overlay';
            dialog.innerHTML = `
                <div class="monitor-dialog">
                    <h3>Select Monitor(s)</h3>
                    <p class="dialog-subtitle">Choose where to display: ${escapeHtml(website.name)}</p>
                    <div class="monitor-options">
                        <button class="btn btn-primary monitor-btn" onclick="startDisplay(${index}, '1'); closeMonitorDialog();">
                            Monitor 1 Only
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="startDisplay(${index}, '2'); closeMonitorDialog();">
                            Monitor 2 Only
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="startDisplay(${index}, 'both'); closeMonitorDialog();">
                            Both Monitors (Same Site)
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="showDualMonitorDialog(${index});">
                            Both Monitors (Different Sites/Images)
                        </button>
                    </div>
                    <button class="btn btn-secondary" onclick="closeMonitorDialog();" style="margin-top: 15px; width: 100%;">
                        Cancel
                    </button>
                </div>
            `;
            // Close on overlay click
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    closeMonitorDialog();
                }
            });
            document.body.appendChild(dialog);
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

// Show dual monitor dialog for selecting different sites or images
function showDualMonitorDialog(index1) {
    Promise.all([
        fetch(`${API_BASE}/api/websites`).then(res => res.json()),
        fetch(`${API_BASE}/api/images`).then(res => res.json())
    ])
        .then(([websites, images]) => {
            const website1 = websites[index1];
            if (!website1) {
                showStatus('Website not found', 'error');
                return;
            }

            // Close existing dialog
            closeMonitorDialog();

            // Create dual monitor dialog
            const dialog = document.createElement('div');
            dialog.className = 'monitor-dialog-overlay';
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
                            <select id="monitor2Type" class="site-select" onchange="updateMonitor2Options()">
                                <option value="website">Website</option>
                                <option value="image">Image</option>
                            </select>
                            <select id="monitor2Site" class="site-select" style="margin-top: 8px;">
                                ${websites.map((site, idx) => 
                                    `<option value="${idx}" ${idx === index1 ? 'selected' : ''}>${escapeHtml(site.name)}</option>`
                                ).join('')}
                            </select>
                            <select id="monitor2Image" class="site-select" style="margin-top: 8px; display: none;">
                                ${images.map((img, idx) => 
                                    `<option value="${idx}">${escapeHtml(img.name)}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="dialog-actions">
                        <button class="btn btn-success" onclick="startDualMonitor(${index1});">
                            Start Both Monitors
                        </button>
                        <button class="btn btn-secondary" onclick="closeMonitorDialog();">
                            Cancel
                        </button>
                    </div>
                </div>
            `;
            // Close on overlay click
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    closeMonitorDialog();
                }
            });
            document.body.appendChild(dialog);
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

// Update monitor 2 options based on type selection
function updateMonitor2Options() {
    const type = document.getElementById('monitor2Type').value;
    const siteSelect = document.getElementById('monitor2Site');
    const imageSelect = document.getElementById('monitor2Image');
    
    if (type === 'image') {
        siteSelect.style.display = 'none';
        imageSelect.style.display = 'block';
    } else {
        siteSelect.style.display = 'block';
        imageSelect.style.display = 'none';
    }
}

// Start dual monitor with different sites or images
function startDualMonitor(index1) {
    const type = document.getElementById('monitor2Type').value;
    const index2 = parseInt(type === 'image' ? document.getElementById('monitor2Image').value : document.getElementById('monitor2Site').value);
    
    Promise.all([
        fetch(`${API_BASE}/api/websites`).then(res => res.json()),
        fetch(`${API_BASE}/api/images`).then(res => res.json())
    ])
        .then(([websites, images]) => {
            const website1 = websites[index1];
            
            if (!website1) {
                showStatus('Website not found', 'error');
                return;
            }

            if (type === 'image') {
                const image2 = images[index2];
                if (!image2) {
                    showStatus('Image not found', 'error');
                    return;
                }
                // Start with website on monitor 1 and image on monitor 2
                const payload = {
                    url1: website1.url || '',
                    image2: image2.filename,
                    monitor: 'both'
                };
                
                fetch(`${API_BASE}/api/display`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                })
                .then(res => res.json())
                .then(result => {
                    if (result.success) {
                        showStatus(result.message, 'success');
                    } else {
                        showStatus('Error: ' + result.error, 'error');
                    }
                    closeMonitorDialog();
                })
                .catch(error => {
                    showStatus('Error: ' + error.message, 'error');
                });
            } else {
                const website2 = websites[index2];
                if (!website2) {
                    showStatus('Website not found', 'error');
                    return;
                }
                startDisplay(index1, 'both', website2.url || '');
                closeMonitorDialog();
            }
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

// Close monitor dialog
function closeMonitorDialog() {
    const dialog = document.querySelector('.monitor-dialog-overlay');
    if (dialog) {
        dialog.remove();
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

// Load and display images
async function loadImages() {
    try {
        const response = await fetch(`${API_BASE}/api/images`);
        const images = await response.json();
        displayImages(images);
    } catch (error) {
        showStatus('Error loading images: ' + error.message, 'error');
    }
}

// Display images in the list
function displayImages(images) {
    const imageList = document.getElementById('imageList');
    imageList.innerHTML = '';

    if (images.length === 0) {
        imageList.innerHTML = '<p style="color: #a0a0a0; text-align: center; padding: 20px;">No images uploaded yet. Upload one below!</p>';
        return;
    }

    images.forEach((image, index) => {
        const item = document.createElement('div');
        item.className = 'image-item';
        
        const imageUrl = `${API_BASE}/api/images/${image.filename}`;
        
        item.innerHTML = `
            <div class="image-preview">
                <img src="${imageUrl}" alt="${escapeHtml(image.name)}" onerror="this.parentElement.style.background='linear-gradient(135deg, #667eea 0%, #764ba2 100%)';">
            </div>
            <div class="image-content">
                <div class="image-info">
                    <h3>${escapeHtml(image.name)}</h3>
                    <p>${escapeHtml(image.original_filename)}</p>
                </div>
                <div class="image-actions">
                    <button class="btn btn-success" onclick="showImageMonitorDialog(${index})">
                        Display Image
                    </button>
                    <button class="btn btn-secondary" onclick="deleteImage(${index})">
                        Delete
                    </button>
                </div>
            </div>
        `;
        
        imageList.appendChild(item);
    });
}

// Upload new image
async function handleUploadImage(e) {
    e.preventDefault();
    
    const name = document.getElementById('imageName').value.trim();
    const fileInput = document.getElementById('imageFile');
    const file = fileInput.files[0];

    if (!name) {
        showStatus('Please enter an image name', 'error');
        return;
    }

    if (!file) {
        showStatus('Please select an image file', 'error');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);

        const response = await fetch(`${API_BASE}/api/images`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus(`Image "${name}" uploaded successfully!`, 'success');
            document.getElementById('uploadImageForm').reset();
            displayImages(result.images);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error uploading image: ' + error.message, 'error');
    }
}

// Delete image
async function deleteImage(index) {
    if (!confirm('Are you sure you want to delete this image?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/images/${index}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            showStatus('Image deleted successfully', 'success');
            displayImages(result.images);
        } else {
            showStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showStatus('Error deleting image: ' + error.message, 'error');
    }
}

// Show image monitor selection dialog
function showImageMonitorDialog(index) {
    fetch(`${API_BASE}/api/images`)
        .then(res => res.json())
        .then(images => {
            const image = images[index];
            if (!image) {
                showStatus('Image not found', 'error');
                return;
            }

            // Create dialog
            const dialog = document.createElement('div');
            dialog.className = 'monitor-dialog-overlay';
            dialog.innerHTML = `
                <div class="monitor-dialog">
                    <h3>Select Monitor(s)</h3>
                    <p class="dialog-subtitle">Choose where to display: ${escapeHtml(image.name)}</p>
                    <div class="image-preview-dialog">
                        <img src="${API_BASE}/api/images/${image.filename}" alt="${escapeHtml(image.name)}" style="max-width: 100%; max-height: 200px; border-radius: 8px; margin-bottom: 15px;">
                    </div>
                    <div class="monitor-options">
                        <button class="btn btn-primary monitor-btn" onclick="startImageDisplay(${index}, '1'); closeMonitorDialog();">
                            Monitor 1 Only
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="startImageDisplay(${index}, '2'); closeMonitorDialog();">
                            Monitor 2 Only
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="startImageDisplay(${index}, 'both'); closeMonitorDialog();">
                            Both Monitors (Same Image)
                        </button>
                        <button class="btn btn-primary monitor-btn" onclick="showDualImageMonitorDialog(${index});">
                            Both Monitors (Different Images)
                        </button>
                    </div>
                    <button class="btn btn-secondary" onclick="closeMonitorDialog();" style="margin-top: 15px; width: 100%;">
                        Cancel
                    </button>
                </div>
            `;
            // Close on overlay click
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    closeMonitorDialog();
                }
            });
            document.body.appendChild(dialog);
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

// Start display with an image
async function startImageDisplay(index, monitor = 'both', image2Index = null) {
    try {
        const response = await fetch(`${API_BASE}/api/images`);
        const images = await response.json();
        const image = images[index];
        
        if (!image) {
            showStatus('Image not found', 'error');
            return;
        }

        const payload = {
            image1: image.filename,
            monitor: monitor
        };
        
        // If dual monitor mode and image2Index is provided, use it
        if (monitor === 'both' && image2Index !== null) {
            const image2 = images[image2Index];
            if (image2) {
                payload.image2 = image2.filename;
            }
        } else if (monitor === '2' && image2Index !== null) {
            const image2 = images[image2Index];
            if (image2) {
                payload.image2 = image2.filename;
            }
        }

        const response2 = await fetch(`${API_BASE}/api/display`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
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

// Show dual image monitor dialog
function showDualImageMonitorDialog(index1) {
    Promise.all([
        fetch(`${API_BASE}/api/images`).then(res => res.json()),
        fetch(`${API_BASE}/api/websites`).then(res => res.json())
    ])
        .then(([images, websites]) => {
            const image1 = images[index1];
            if (!image1) {
                showStatus('Image not found', 'error');
                return;
            }

            // Close existing dialog
            closeMonitorDialog();

            // Create dual monitor dialog
            const dialog = document.createElement('div');
            dialog.className = 'monitor-dialog-overlay';
            dialog.innerHTML = `
                <div class="monitor-dialog" style="max-width: 500px;">
                    <h3>Dual Monitor Setup</h3>
                    <div class="dual-monitor-form">
                        <div class="monitor-selection">
                            <label><strong>Monitor 1:</strong></label>
                            <div class="selected-site">
                                <img src="${API_BASE}/api/images/${image1.filename}" alt="${escapeHtml(image1.name)}" style="max-width: 100px; max-height: 60px; border-radius: 4px; margin-right: 10px; vertical-align: middle;">
                                ${escapeHtml(image1.name)}
                            </div>
                        </div>
                        <div class="monitor-selection">
                            <label><strong>Monitor 2:</strong></label>
                            <select id="monitor2ImageType" class="site-select" onchange="updateMonitor2ImageOptions()">
                                <option value="image">Image</option>
                                <option value="website">Website</option>
                            </select>
                            <select id="monitor2Image" class="site-select" style="margin-top: 8px;">
                                ${images.map((img, idx) => 
                                    `<option value="${idx}" ${idx === index1 ? 'selected' : ''}>${escapeHtml(img.name)}</option>`
                                ).join('')}
                            </select>
                            <select id="monitor2ImageSite" class="site-select" style="margin-top: 8px; display: none;">
                                ${websites.map((site, idx) => 
                                    `<option value="${idx}">${escapeHtml(site.name)}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="dialog-actions">
                        <button class="btn btn-success" onclick="startDualImageMonitor(${index1});">
                            Start Both Monitors
                        </button>
                        <button class="btn btn-secondary" onclick="closeMonitorDialog();">
                            Cancel
                        </button>
                    </div>
                </div>
            `;
            // Close on overlay click
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    closeMonitorDialog();
                }
            });
            document.body.appendChild(dialog);
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

// Update monitor 2 image options based on type selection
function updateMonitor2ImageOptions() {
    const type = document.getElementById('monitor2ImageType').value;
    const imageSelect = document.getElementById('monitor2Image');
    const siteSelect = document.getElementById('monitor2ImageSite');
    
    if (type === 'website') {
        imageSelect.style.display = 'none';
        siteSelect.style.display = 'block';
    } else {
        imageSelect.style.display = 'block';
        siteSelect.style.display = 'none';
    }
}

// Start dual monitor with different images or websites
function startDualImageMonitor(index1) {
    const type = document.getElementById('monitor2ImageType').value;
    const index2 = parseInt(type === 'website' ? document.getElementById('monitor2ImageSite').value : document.getElementById('monitor2Image').value);
    
    Promise.all([
        fetch(`${API_BASE}/api/images`).then(res => res.json()),
        fetch(`${API_BASE}/api/websites`).then(res => res.json())
    ])
        .then(([images, websites]) => {
            const image1 = images[index1];
            
            if (!image1) {
                showStatus('Image not found', 'error');
                return;
            }

            if (type === 'website') {
                const website2 = websites[index2];
                if (!website2) {
                    showStatus('Website not found', 'error');
                    return;
                }
                // Start with image on monitor 1 and website on monitor 2
                const payload = {
                    image1: image1.filename,
                    url2: website2.url || '',
                    monitor: 'both'
                };
                
                fetch(`${API_BASE}/api/display`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                })
                .then(res => res.json())
                .then(result => {
                    if (result.success) {
                        showStatus(result.message, 'success');
                    } else {
                        showStatus('Error: ' + result.error, 'error');
                    }
                    closeMonitorDialog();
                })
                .catch(error => {
                    showStatus('Error: ' + error.message, 'error');
                });
            } else {
                startImageDisplay(index1, 'both', index2);
                closeMonitorDialog();
            }
        })
        .catch(error => {
            showStatus('Error: ' + error.message, 'error');
        });
}

