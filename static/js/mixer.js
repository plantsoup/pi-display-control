/**
 * Dual Monitor Mixer (Independent Screen Control)
 */

import { appState, showToast, escapeHtml } from './state.js';
import { fetchLiveStatus } from './display.js';

export function onMixerTypeChange(monId) {
    const typeSelect = document.getElementById(`mixerMon${monId}Type`);
    const websiteBox = document.getElementById(`mixerMon${monId}WebsiteBox`);
    const imageBox = document.getElementById(`mixerMon${monId}ImageBox`);
    const slideshowBox = document.getElementById(`mixerMon${monId}SlideshowBox`);
    const fitBox = document.getElementById(`mixerMon${monId}FitBox`);

    const type = typeSelect ? typeSelect.value : 'website';

    if (type === 'website') {
        if (websiteBox) websiteBox.style.display = 'block';
        if (imageBox) imageBox.style.display = 'none';
        if (slideshowBox) slideshowBox.style.display = 'none';
        if (fitBox) fitBox.style.display = 'none';
    } else if (type === 'image') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'block';
        if (slideshowBox) slideshowBox.style.display = 'none';
        if (fitBox) fitBox.style.display = 'block';
    } else if (type === 'slideshow') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'none';
        if (slideshowBox) slideshowBox.style.display = 'block';
        if (fitBox) fitBox.style.display = 'block';
    }
}

export function populateMixerOptions() {
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

export function getMonitorTargetObject(monId) {
    const type = document.getElementById(`mixerMon${monId}Type`).value;
    const fitSelect = document.getElementById(`mixerMon${monId}Fit`);
    const fit = fitSelect ? fitSelect.value : 'cover';

    if (type === 'website') {
        const url = document.getElementById(`mixerMon${monId}Website`).value;
        return { type: 'website', url: url };
    } else if (type === 'image') {
        const img = document.getElementById(`mixerMon${monId}Image`).value;
        return { type: 'image', image: img, fit: fit };
    } else if (type === 'slideshow') {
        return {
            type: 'slideshow',
            mode: appState.slideshowConfig.mode || 'random',
            interval: appState.slideshowConfig.interval || 30,
            fit: fit
        };
    }
    return { type: 'website', url: '' };
}

export async function applyDualMixer() {
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

export async function applySingleMonitor(monId) {
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
