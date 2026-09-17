/**
 * Slideshow Studio Controller
 */

import { appState, showToast } from './state.js';
import { fetchLiveStatus } from './display.js';

export async function loadSlideshowConfig() {
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
        await fetch('/api/slideshow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appState.slideshowConfig)
        });
    } catch (err) {
        showToast('Error saving slideshow settings: ' + err.message, 'error');
    }
}

export async function launchSlideshow(monitor = 'both') {
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
                slideshow_mode: appState.slideshowConfig.mode,
                fit: appState.slideshowConfig.fit || 'cover'
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
