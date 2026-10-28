/**
 * Slideshow Studio Controller
 */

import {
    appState,
    showToast,
    apiFetch,
    getActiveNode,
    getAvailableMonitors,
    isRemoteActive
} from './state.js';
import { fetchLiveStatus } from './display.js';

export async function loadSlideshowConfig() {
    try {
        const res = await apiFetch('/api/slideshow');
        const data = await res.json();
        if (data.success && data.config) {
            appState.slideshowConfig = data.config;
            renderSlideshowControls();
        }
    } catch (err) {
        console.error('Error loading slideshow config:', err);
    }
}

export function renderSlideshowControls() {
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

    // Show launch buttons only for physically available monitors
    const avail = getAvailableMonitors();
    const count = avail.length;
    const loaded = appState.monitorsLoaded;
    const bothBtn = document.getElementById('launchSlideshowBothBtn');
    const mon1Btn = document.getElementById('launchSlideshowMon1Btn');
    const mon2Btn = document.getElementById('launchSlideshowMon2Btn');
    const noMonTag = document.getElementById('slideshowNoLocalMonTag');

    if (bothBtn) {
        bothBtn.style.display = (!loaded || count >= 2) ? 'inline-flex' : 'none';
    }
    if (mon1Btn) {
        mon1Btn.style.display = (!loaded || count >= 1) ? 'inline-flex' : 'none';
        mon1Btn.className = (loaded && count === 1) ? 'btn btn-hero-primary' : 'btn btn-subtle-secondary';
    }
    if (mon2Btn) {
        mon2Btn.style.display = (!loaded || count >= 2) ? 'inline-flex' : 'none';
    }
    if (noMonTag) {
        if (loaded && count === 0) {
            const activeNode = getActiveNode();
            noMonTag.textContent = `No monitor attached to ${activeNode.name}`;
            noMonTag.style.display = 'inline-flex';
        } else {
            noMonTag.style.display = 'none';
        }
    }

    updateSlideshowSummaryText();
}

export function updateSlideshowSummaryText() {
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

export async function setSlideshowMode(mode) {
    appState.slideshowConfig.mode = mode;
    renderSlideshowControls();
    await saveSlideshowConfigChanges();
}

export async function updateSlideshowSetting(key, value) {
    appState.slideshowConfig[key] = key === 'interval' ? parseInt(value) : value;
    updateSlideshowSummaryText();
    await saveSlideshowConfigChanges();
}

export async function saveSlideshowConfigChanges() {
    try {
        await apiFetch('/api/slideshow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appState.slideshowConfig)
        });
    } catch (err) {
        showToast('Error saving slideshow settings: ' + err.message, 'error');
    }
}

export async function launchSlideshow(monitor = 'both') {
    const activeNode = getActiveNode();
    if (appState.monitorsLoaded && getAvailableMonitors().length === 0) {
        showToast(`No monitors attached to ${activeNode.name}`, 'error');
        return;
    }
    if (appState.images.length === 0) {
        showToast(`Please upload at least one image on ${activeNode.name} (or stream from Main Pi in Mixer / Connected Pis)`, 'error');
        return;
    }

    try {
        showToast(`${activeNode.name}: Launching ${appState.slideshowConfig.mode} slideshow on ${monitor} monitor(s)...`, 'info');

        const res = await apiFetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: 'slideshow',
                monitor: monitor,
                interval: appState.slideshowConfig.interval,
                slideshow_mode: appState.slideshowConfig.mode,
                fit: appState.slideshowConfig.fit || 'cover'
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`${activeNode.name}: ${data.message || 'Slideshow started successfully!'}`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error starting slideshow: ' + err.message, 'error');
    }
}

export async function broadcastSlideshow(monitor = 'both') {
    const sourceCount = isRemoteActive() ? appState.mainImages.length : appState.images.length;
    if (sourceCount === 0) {
        showToast('Upload at least one image on Main Pi before broadcasting slideshow', 'error');
        return;
    }

    try {
        showToast('Broadcasting slideshow stream across all connected Pis...', 'info');
        const res = await fetch('/api/nodes/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'display',
                payload: {
                    mode: 'slideshow',
                    monitor: monitor,
                    interval: appState.slideshowConfig.interval,
                    slideshow_mode: appState.slideshowConfig.mode,
                    fit: appState.slideshowConfig.fit || 'cover',
                    stream_from_main: true
                }
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Slideshow active across all connected Pis!', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + (data.error || data.message), 'error');
        }
    } catch (err) {
        showToast('Error broadcasting slideshow: ' + err.message, 'error');
    }
}
