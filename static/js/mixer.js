/**
 * Dual Monitor Mixer (Independent Screen Control & Live Previews)
 */

import {
    appState,
    showToast,
    escapeHtml,
    apiFetch,
    apiUrl,
    isRemoteActive,
    getActiveNode,
    formatHostShort
} from './state.js';
import { fetchLiveStatus } from './display.js';
import { getIcon } from './icons.js';

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
    } else if (type === 'image' || type === 'main_image') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'block';
        if (slideshowBox) slideshowBox.style.display = 'none';
        if (fitBox) fitBox.style.display = 'block';
        _populateMixerImageDropdown(monId, type === 'main_image');
    } else if (type === 'slideshow' || type === 'main_slideshow') {
        if (websiteBox) websiteBox.style.display = 'none';
        if (imageBox) imageBox.style.display = 'none';
        if (slideshowBox) slideshowBox.style.display = 'block';
        if (fitBox) fitBox.style.display = 'block';
    }

    updateMixerPreview(monId);
}

function _populateMixerImageDropdown(monId, useMainLibrary = false) {
    const imgSelect = document.getElementById(`mixerMon${monId}Image`);
    if (!imgSelect) return;

    const prevVal = imgSelect.value;
    const sourceImages = useMainLibrary ? (appState.mainImages || []) : (appState.images || []);

    if (sourceImages.length === 0) {
        imgSelect.innerHTML = `<option value="">(No uploaded images${useMainLibrary ? ' on Main Pi' : ''})</option>`;
    } else {
        imgSelect.innerHTML = sourceImages.map(img =>
            `<option value="${escapeHtml(img.filename)}">${escapeHtml(img.name)}</option>`
        ).join('');
        if (prevVal && sourceImages.some(i => i.filename === prevVal)) {
            imgSelect.value = prevVal;
        }
    }
    imgSelect.onchange = () => updateMixerPreview(monId);
}

export function updateMixerPreview(monId) {
    const screen = document.getElementById(`mon${monId}PreviewScreen`);
    const title = document.getElementById(`mon${monId}PreviewTitle`);
    const typeSelect = document.getElementById(`mixerMon${monId}Type`);
    if (!screen) return;

    const type = typeSelect ? typeSelect.value : 'website';

    if (type === 'website') {
        const webSelect = document.getElementById(`mixerMon${monId}Website`);
        const url = webSelect ? webSelect.value : '';
        const selectedOption = webSelect && webSelect.selectedIndex >= 0 ? webSelect.options[webSelect.selectedIndex] : null;
        const siteName = selectedOption ? selectedOption.getAttribute('data-name') || selectedOption.textContent.split('(')[0].trim() : 'Website';

        if (title) title.innerHTML = `${getIcon('globe')} Website: ${escapeHtml(siteName)}`;

        screen.innerHTML = `
            <div class="preview-website-view">
                <div class="preview-website-icon">
                    ${getIcon('globe')}
                </div>
                <div class="preview-website-name">${escapeHtml(siteName)}</div>
                <div class="preview-website-url">${escapeHtml(url || 'Autodarts Kiosk')}</div>
            </div>
            <div class="preview-screen-overlay"></div>
        `;
    } else if (type === 'image' || type === 'main_image') {
        const imgSelect = document.getElementById(`mixerMon${monId}Image`);
        const fitSelect = document.getElementById(`mixerMon${monId}Fit`);
        const filename = imgSelect ? imgSelect.value : '';
        const fit = fitSelect ? fitSelect.value : 'cover';
        const selectedOption = imgSelect && imgSelect.selectedIndex >= 0 ? imgSelect.options[imgSelect.selectedIndex] : null;
        const imgName = selectedOption ? selectedOption.textContent : 'Image';
        const imgSrc = type === 'main_image'
            ? `/api/images/${encodeURIComponent(filename)}`
            : apiUrl(`/api/images/${encodeURIComponent(filename)}`);

        if (title) {
            const prefix = type === 'main_image' ? 'Streamed Image' : 'Single Image';
            title.innerHTML = `${getIcon('image')} ${prefix}: ${escapeHtml(imgName)}`;
        }

        if (filename) {
            screen.innerHTML = `
                <img src="${imgSrc}" class="preview-img-element fit-${fit}" alt="${escapeHtml(imgName)}">
                <div class="preview-screen-overlay"></div>
            `;
        } else {
            screen.innerHTML = `
                <div class="preview-website-view">
                    <div class="preview-website-icon">${getIcon('image')}</div>
                    <div class="preview-website-name">No Image Selected</div>
                </div>
                <div class="preview-screen-overlay"></div>
            `;
        }
    } else if (type === 'slideshow' || type === 'main_slideshow') {
        const cfg = appState.slideshowConfig || {};
        const mode = cfg.mode || 'random';
        const interval = cfg.interval || 30;
        const isStream = type === 'main_slideshow';
        const imageCount = isStream ? (appState.mainImages || []).length : appState.images.length;
        const mainHost = formatHostShort(appState.localNode.url);

        if (title) {
            title.innerHTML = `${getIcon('shuffle')} ${isStream ? `Stream from ${escapeHtml(mainHost)}` : 'Slideshow Studio'}`;
        }

        screen.innerHTML = `
            <div class="preview-slideshow-view">
                ${getIcon('image')}
                <div class="preview-slideshow-title">${isStream ? `Main Pi Slideshow (${escapeHtml(mode)})` : `Slideshow (${escapeHtml(mode)})`}</div>
                <div class="preview-slideshow-pill">${interval}s rotation &bull; ${imageCount} items</div>
            </div>
            <div class="preview-screen-overlay"></div>
        `;
    }
}

export function populateMixerOptions() {
    const remote = isRemoteActive();
    const mainHost = formatHostShort(appState.localNode.url);
    const activeNode = getActiveNode();

    // Update Mixer header badge showing active Pi
    const mixerBadge = document.getElementById('mixerActivePiBadge');
    if (mixerBadge) {
        mixerBadge.textContent = `${activeNode.name} (${formatHostShort(activeNode.url)})`;
        mixerBadge.className = `mixer-target-pi-badge ${remote ? 'is-remote' : 'is-local'}`;
    }

    ['1', '2'].forEach(monId => {
        // Sync content type options (include Main Pi stream options when controlling a remote Pi)
        const typeSelect = document.getElementById(`mixerMon${monId}Type`);
        if (typeSelect) {
            const currentVal = typeSelect.value || (monId === '2' ? 'slideshow' : 'website');
            const options = [
                { value: 'website', label: 'Website / Autodarts' },
                { value: 'slideshow', label: remote ? `${activeNode.name} Local Slideshow` : 'Random / Timed Slideshow' },
                { value: 'image', label: remote ? `${activeNode.name} Local Image` : 'Single Uploaded Image' }
            ];
            if (remote) {
                options.push({ value: 'main_slideshow', label: `Stream Slideshow from ${appState.localNode.name} (${mainHost})` });
                options.push({ value: 'main_image', label: `Stream Image from ${appState.localNode.name} (${mainHost})` });
            }
            typeSelect.innerHTML = options.map(o =>
                `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`
            ).join('');

            if (options.some(o => o.value === currentVal)) {
                typeSelect.value = currentVal;
            } else {
                typeSelect.value = currentVal.replace('main_', '');
            }
        }

        // Websites dropdown
        const webSelect = document.getElementById(`mixerMon${monId}Website`);
        if (webSelect) {
            const prevWeb = webSelect.value;
            webSelect.innerHTML = appState.websites.map(w =>
                `<option value="${escapeHtml(w.url || '')}" data-name="${escapeHtml(w.name)}">${escapeHtml(w.name)} (${w.url ? escapeHtml(w.url) : 'Autodarts default'})</option>`
            ).join('');
            if (prevWeb && appState.websites.some(w => (w.url || '') === prevWeb)) {
                webSelect.value = prevWeb;
            }
            webSelect.onchange = () => updateMixerPreview(monId);
        }

        // Images dropdown
        const currentType = typeSelect ? typeSelect.value : 'website';
        _populateMixerImageDropdown(monId, currentType === 'main_image');

        // Fit dropdown
        const fitSelect = document.getElementById(`mixerMon${monId}Fit`);
        if (fitSelect) {
            fitSelect.onchange = () => updateMixerPreview(monId);
        }

        // Sync visibility and preview
        onMixerTypeChange(monId);
    });
}

export function getMonitorTargetObject(monId) {
    const typeEl = document.getElementById(`mixerMon${monId}Type`);
    const type = typeEl ? typeEl.value : 'website';
    const fitSelect = document.getElementById(`mixerMon${monId}Fit`);
    const fit = fitSelect ? fitSelect.value : 'cover';

    if (type === 'website') {
        const webEl = document.getElementById(`mixerMon${monId}Website`);
        const url = webEl ? webEl.value : '';
        return { type: 'website', url: url };
    } else if (type === 'image' || type === 'main_image') {
        const imgEl = document.getElementById(`mixerMon${monId}Image`);
        const img = imgEl ? imgEl.value : '';
        return { type: type, image: img, fit: fit };
    } else if (type === 'slideshow' || type === 'main_slideshow') {
        return {
            type: type,
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
    const activeNode = getActiveNode();

    try {
        showToast(`Applying mixed setup to ${activeNode.name}...`, 'info');
        const res = await apiFetch('/api/display', {
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
            showToast(`${activeNode.name}: ${data.message || 'Dual monitor setup updated!'}`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error applying setup: ' + err.message, 'error');
    }
}

export async function applyDualMixerAllPis() {
    const target1 = getMonitorTargetObject('1');
    const target2 = getMonitorTargetObject('2');

    try {
        showToast('Broadcasting monitor layout to all connected Pis...', 'info');
        const res = await fetch('/api/nodes/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'display',
                payload: {
                    monitor: 'both',
                    monitor1: target1,
                    monitor2: target2,
                    stream_from_main: !isRemoteActive()
                }
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Broadcasted layout to all connected Pis!', 'success');
            fetchLiveStatus();
        } else {
            showToast('Broadcast error: ' + (data.error || data.message), 'error');
        }
    } catch (err) {
        showToast('Error broadcasting layout: ' + err.message, 'error');
    }
}

export async function applySingleMonitor(monId) {
    const target = getMonitorTargetObject(monId);
    const activeNode = getActiveNode();

    try {
        showToast(`${activeNode.name}: Updating Monitor ${monId}...`, 'info');
        const payload = {
            monitor: monId
        };
        if (monId === '1') {
            payload.monitor1 = target;
        } else {
            payload.monitor2 = target;
        }

        const res = await apiFetch('/api/display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`${activeNode.name}: Monitor ${monId} updated!`, 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast(`Error updating Monitor ${monId}: ` + err.message, 'error');
    }
}
