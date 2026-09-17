/**
 * Websites & Autodarts Management
 */

import { appState, showToast, escapeHtml } from './state.js';
import { fetchLiveStatus } from './display.js';
import { populateMixerOptions } from './mixer.js';

export async function loadWebsites() {
    try {
        const res = await fetch('/api/websites');
        const websites = await res.json();
        appState.websites = websites;
        const countBadge = document.getElementById('websiteCountBadge');
        if (countBadge) countBadge.textContent = websites.length;
        renderWebsitesGrid();
        populateWebsiteOptions();
        populateMixerOptions();
    } catch (err) {
        showToast('Error loading websites: ' + err.message, 'error');
    }
}

export function getFaviconUrl(url) {
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

export function renderWebsitesGrid() {
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

export async function handleAddWebsite(e) {
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
            const countBadge = document.getElementById('websiteCountBadge');
            if (countBadge) countBadge.textContent = data.websites.length;
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

export async function launchWebsite(index, monitor = 'both') {
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

export async function deleteWebsite(index) {
    if (!confirm('Are you sure you want to delete this website?')) return;

    try {
        const res = await fetch(`/api/websites/${index}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Website deleted', 'success');
            appState.websites = data.websites;
            const countBadge = document.getElementById('websiteCountBadge');
            if (countBadge) countBadge.textContent = data.websites.length;
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

export function populateWebsiteOptions() {
    const picker = document.getElementById('scheduleWebsitePicker');
    if (!picker) return;
    picker.innerHTML = appState.websites.map(w => 
        `<option value="${escapeHtml(w.url || '')}">${escapeHtml(w.name)}</option>`
    ).join('');
}
