/**
 * Image Library & Uploads
 */

import {
    appState,
    showToast,
    escapeHtml,
    apiFetch,
    apiUrl,
    isRemoteActive,
    getActiveNode,
    getAvailableMonitors
} from './state.js';
import { fetchLiveStatus } from './display.js';
import { populateMixerOptions } from './mixer.js';
import { saveSlideshowConfigChanges, updateSlideshowSummaryText } from './slideshow.js';
import { getIcon } from './icons.js';

export async function loadImages() {
    try {
        const res = await apiFetch('/api/images');
        const images = await res.json();
        if (!Array.isArray(images)) return;

        appState.images = images;
        if (!isRemoteActive()) {
            appState.mainImages = images;
        }
        const countBadge = document.getElementById('imageCountBadge');
        if (countBadge) countBadge.textContent = images.length;
        renderImagesGrid();
        populateMixerOptions();
    } catch (err) {
        showToast('Error loading images: ' + err.message, 'error');
    }
}

export function renderImagesGrid() {
    const list = document.getElementById('imageList');
    if (!list) return;

    list.innerHTML = '';
    if (appState.images.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">No images uploaded yet. Upload images to start your slideshow!</div>';
        return;
    }

    const selectedIds = new Set(appState.slideshowConfig.selected_images || []);
    const hasRemotes = (appState.remoteNodes || []).length > 0 && !isRemoteActive();
    const availCount = getAvailableMonitors().length;
    const loaded = appState.monitorsLoaded;

    appState.images.forEach((img, idx) => {
        const isSelected = selectedIds.size === 0 || selectedIds.has(img.id);
        const card = document.createElement('div');
        card.className = `image-card ${isSelected ? 'selected' : ''}`;
        const thumbUrl = apiUrl(`/api/images/${encodeURIComponent(img.filename)}`);
        const safeFnJs = String(img.filename || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");

        let localMonitorBtns = '';
        if (!loaded || availCount >= 2) {
            localMonitorBtns = `
                <button class="btn btn-xs btn-subtle-secondary" onclick="displaySingleImage('${safeFnJs}', 'both')" title="Show on both monitors">
                    ${getIcon('rocket')} Both
                </button>
                <button class="btn btn-xs btn-subtle-secondary" onclick="displaySingleImage('${safeFnJs}', '1')" title="Show on Monitor 1 only">
                    M1
                </button>
                <button class="btn btn-xs btn-subtle-secondary" onclick="displaySingleImage('${safeFnJs}', '2')" title="Show on Monitor 2 only">
                    M2
                </button>
            `;
        } else if (availCount === 1) {
            localMonitorBtns = `
                <button class="btn btn-xs btn-subtle-secondary" onclick="displaySingleImage('${safeFnJs}', '1')" title="Show on attached Monitor 1">
                    ${getIcon('monitor')} Display
                </button>
            `;
        }

        card.innerHTML = `
            <div class="image-thumbnail-box">
                <img src="${thumbUrl}" alt="${escapeHtml(img.name)}" loading="lazy">
            </div>
            <div class="image-meta">
                <h4>${escapeHtml(img.name)}</h4>
                <p>${escapeHtml(img.original_filename || '')}</p>
            </div>
            <div class="image-card-actions">
                ${localMonitorBtns}
                ${hasRemotes ? `
                <button class="btn btn-xs btn-subtle-secondary" onclick="broadcastSingleImage('${safeFnJs}')" title="Stream image across all connected Pis">
                    ${getIcon('broadcast')} All
                </button>` : ''}
                <button class="btn btn-xs btn-danger" onclick="deleteImage(${idx})" title="Delete image">
                    ${getIcon('trash')}
                </button>
            </div>
        `;
        list.appendChild(card);
    });
}

export async function handleUploadImage(e) {
    e.preventDefault();
    const nameInput = document.getElementById('imageName');
    const fileInput = document.getElementById('imageFile');
    const submitBtn = document.getElementById('uploadSubmitBtn');
    const activeNode = getActiveNode();

    if (!fileInput || !fileInput.files[0]) {
        showToast('Please select a file to upload', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('name', nameInput.value.trim());
    formData.append('file', fileInput.files[0]);

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = `Uploading to ${activeNode.name}...`;

        const res = await apiFetch('/api/images', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            showToast(`Image "${nameInput.value}" uploaded to ${activeNode.name}!`, 'success');
            document.getElementById('uploadImageForm').reset();
            appState.images = data.images;
            if (!isRemoteActive()) {
                appState.mainImages = data.images;
            }
            const countBadge = document.getElementById('imageCountBadge');
            if (countBadge) countBadge.textContent = data.images.length;
            renderImagesGrid();
            populateMixerOptions();
        } else {
            showToast('Upload error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error uploading: ' + err.message, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `${getIcon('upload')} Upload Image`;
        }
    }
}

export async function displaySingleImage(filename, monitor = 'both') {
    const activeNode = getActiveNode();
    if (appState.monitorsLoaded && getAvailableMonitors().length === 0) {
        showToast(`No monitors attached to ${activeNode.name}`, 'error');
        return;
    }
    try {
        showToast(`${activeNode.name}: Displaying image on ${monitor} monitor(s)...`, 'info');
        const payload = {
            mode: 'image',
            monitor: monitor,
            fit: appState.slideshowConfig.fit || 'cover'
        };
        if (monitor === '1') {
            payload.image1 = filename;
        } else if (monitor === '2') {
            payload.image2 = filename;
        } else {
            payload.image1 = filename;
            payload.image2 = filename;
        }

        const res = await apiFetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`${activeNode.name}: Image displayed on ${monitor} monitor(s)`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error displaying image: ' + err.message, 'error');
    }
}

export async function broadcastSingleImage(filename, monitor = 'both') {
    try {
        showToast('Streaming image to all connected Pis...', 'info');
        const res = await fetch('/api/nodes/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'display',
                payload: {
                    mode: 'image',
                    monitor: monitor,
                    image1: filename,
                    image2: filename,
                    fit: appState.slideshowConfig.fit || 'cover',
                    stream_from_main: true
                }
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Image broadcasted to all Pis!', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + (data.error || data.message), 'error');
        }
    } catch (err) {
        showToast('Error broadcasting image: ' + err.message, 'error');
    }
}

export async function deleteImage(index) {
    if (!confirm('Are you sure you want to delete this image?')) return;

    try {
        const res = await apiFetch(`/api/images/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Image deleted successfully', 'success');
            appState.images = data.images;
            if (!isRemoteActive()) {
                appState.mainImages = data.images;
            }
            const countBadge = document.getElementById('imageCountBadge');
            if (countBadge) countBadge.textContent = data.images.length;
            renderImagesGrid();
            populateMixerOptions();
        } else {
            showToast('Error deleting: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error deleting image: ' + err.message, 'error');
    }
}

export function selectAllImages(selectAll) {
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
