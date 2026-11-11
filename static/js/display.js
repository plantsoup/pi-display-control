/**
 * Screen Power Controls & Live Status Monitoring
 */

import {
    appState,
    showToast,
    apiFetch,
    getActiveNode,
    getAvailableMonitors,
    isRemoteActive,
    formatHostShort
} from './state.js';

export async function fetchLiveStatus() {
    const badgeText = document.getElementById('liveStatusText');
    const badge = document.getElementById('liveStatusBadge');
    const dot = badge ? badge.querySelector('.status-dot') : null;
    const activeNode = getActiveNode();
    const prefix = isRemoteActive() ? `${activeNode.name}: ` : '';

    // Update Open Viewer link to point to active Pi's viewer
    const viewerLink = document.getElementById('openViewerLink');
    if (viewerLink) {
        viewerLink.href = isRemoteActive() && activeNode.url
            ? `${activeNode.url.replace(/\/+$/, '')}/viewer`
            : '/viewer';
    }

    try {
        const res = await apiFetch('/api/status');
        const data = await res.json();
        if (res.ok && data.success) {
            const state = data.state || {};
            appState.displayState = state;
            if (!badgeText || !badge) return;

            const availCount = getAvailableMonitors().length;
            if (appState.monitorsLoaded && availCount === 0) {
                badgeText.textContent = `${prefix}Online (No Display Attached)`;
                if (dot) dot.className = 'status-dot no-display';
                return;
            }

            const monLabel = (appState.monitorsLoaded && availCount === 1)
                ? 'Monitor 1'
                : (state.monitor || 'both');

            const blankedList = state.blanked_monitors || [];
            if (state.status === 'blank') {
                badgeText.textContent = `${prefix}Screens Off (Blanked)`;
                if (dot) dot.className = 'status-dot blank';
            } else if (state.mode === 'mon1_blank' || blankedList.includes('1')) {
                badgeText.textContent = `${prefix}Monitor 1 Blanked (Mon 2 Active)`;
                if (dot) dot.className = 'status-dot active';
            } else if (state.mode === 'mon2_blank' || blankedList.includes('2')) {
                badgeText.textContent = `${prefix}Monitor 2 Blanked (Mon 1 Active)`;
                if (dot) dot.className = 'status-dot active';
            } else if (state.mode === 'slideshow') {
                badgeText.textContent = `${prefix}Slideshow Active (${monLabel})`;
                if (dot) dot.className = 'status-dot slideshow';
            } else if (state.mode === 'website') {
                badgeText.textContent = `${prefix}Website Active (${monLabel})`;
                if (dot) dot.className = 'status-dot active';
            } else if (state.mode === 'mixed') {
                badgeText.textContent = `${prefix}Mixed Display (${monLabel})`;
                if (dot) dot.className = 'status-dot active';
            } else {
                badgeText.textContent = `${prefix}Display Active`;
                if (dot) dot.className = 'status-dot active';
            }
        } else {
            if (badgeText) {
                badgeText.textContent = `${activeNode.name} (${formatHostShort(activeNode.url)}) Offline`;
            }
            if (dot) dot.className = 'status-dot blank';
        }
    } catch (err) {
        if (badgeText && isRemoteActive()) {
            badgeText.textContent = `${activeNode.name} Offline`;
            if (dot) dot.className = 'status-dot blank';
        }
        console.error('Error fetching live status:', err);
    }
}

export async function handleBlankDisplay(monitor = 'both') {
    const activeNode = getActiveNode();
    const monStr = monitor && monitor !== 'both' ? `Monitor ${monitor}` : 'screens';
    try {
        showToast(`Turning ${monStr} off on ${activeNode.name}...`, 'info');
        const query = monitor && monitor !== 'both' ? `?monitor=${encodeURIComponent(monitor)}` : '';
        const res = await apiFetch(`/api/display${query}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(`${activeNode.name}: ${monitor && monitor !== 'both' ? `Monitor ${monitor}` : 'Displays'} blanked (screen turned off)`, 'success');
            fetchLiveStatus();
            try {
                const { loadMonitorsData } = await import('./monitors.js');
                await loadMonitorsData();
            } catch (_) {}
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error blanking display: ' + err.message, 'error');
    }
}

export async function handleWakeDisplay(monitor = 'both') {
    const activeNode = getActiveNode();
    const monStr = monitor && monitor !== 'both' ? `Monitor ${monitor}` : 'screens';
    try {
        showToast(`Waking ${monStr} on ${activeNode.name}...`, 'info');
        const res = await apiFetch('/api/display/wake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ monitor })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`${activeNode.name}: ${monitor && monitor !== 'both' ? `Monitor ${monitor}` : 'Displays'} woken up`, 'success');
            fetchLiveStatus();
            try {
                const { loadMonitorsData } = await import('./monitors.js');
                await loadMonitorsData();
            } catch (_) {}
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error waking display: ' + err.message, 'error');
    }
}
