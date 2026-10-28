/**
 * Monitor Hardware, Orientations & Default Persistence Management
 */

import {
    appState,
    showToast,
    escapeHtml,
    apiFetch,
    getActiveNode,
    getAvailableMonitors,
    formatHostShort
} from './state.js';
import { getIcon } from './icons.js';
import { fetchLiveStatus } from './display.js';
import { renderSlideshowControls } from './slideshow.js';
import { renderWebsitesGrid } from './websites.js';
import { renderImagesGrid } from './images.js';
import { populateScheduleMonitorOptions } from './schedules.js';

export async function loadMonitorsData() {
    try {
        const res = await apiFetch('/api/display/monitors');
        const data = await res.json();
        if (res.ok && data.success) {
            appState.monitors = getAvailableMonitors(data.monitors || []);
            appState.monitorsLoaded = true;
            appState.monitorDefaults = data.defaults || { "1": "left", "2": "right" };
            appState.availableRotations = data.available_rotations || [];

            updateMonitorAvailabilityUI();
            renderMonitorRotationControls();
            updateHardwareStatusBar();
            renderSlideshowControls();
            renderWebsitesGrid();
            renderImagesGrid();
            populateScheduleMonitorOptions();
            fetchLiveStatus();
        }
    } catch (err) {
        console.error('Error fetching monitor configurations:', err);
    }
}

export function updateMonitorAvailabilityUI() {
    const avail = getAvailableMonitors();
    const count = avail.length;
    const activeNode = getActiveNode();
    const hostShort = formatHostShort(activeNode.url);

    const emptyState = document.getElementById('mixerNoMonitorsState');
    const emptyTitle = document.getElementById('noMonitorsTitle');
    const emptyDesc = document.getElementById('noMonitorsDesc');
    const defaultsBanner = document.getElementById('mixerDefaultsBanner');
    const monitorsGrid = document.getElementById('mixerMonitorsGrid');
    const mon1Card = document.getElementById('mon1Card');
    const mon2Card = document.getElementById('mon2Card');
    const mon1SingleBtn = document.getElementById('mon1ApplySingleBtn');
    const primaryBtn = document.getElementById('applyMixerPrimaryBtn');
    const primaryLabel = document.getElementById('applyMixerPrimaryLabel');
    const headingText = document.getElementById('mixerHeadingText');
    const subtext = document.getElementById('mixerSubtext');
    const mixerTabLabel = document.querySelector('.nav-tab[data-tab="mixerTab"] .tab-label');
    const wakeBtn = document.getElementById('wakeDisplay');
    const stopBtn = document.getElementById('stopDisplay');

    if (count === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        if (emptyTitle) emptyTitle.textContent = `No Monitors Attached to ${activeNode.name}`;
        if (emptyDesc) {
            emptyDesc.textContent = `No connected displays were detected on ${activeNode.name} (${hostShort}). Plug in a monitor and click Refresh Monitors to configure it.`;
        }
        if (defaultsBanner) defaultsBanner.style.display = 'none';
        if (monitorsGrid) monitorsGrid.style.display = 'none';
        if (primaryBtn) primaryBtn.style.display = 'none';
        if (headingText) headingText.textContent = 'Monitor Mixer';
        if (subtext) subtext.textContent = 'No physical displays currently attached to this Pi';
        if (mixerTabLabel) mixerTabLabel.textContent = 'Monitor Mixer';
        if (wakeBtn) {
            wakeBtn.disabled = true;
            wakeBtn.title = `No monitors attached to ${activeNode.name}`;
        }
        if (stopBtn) {
            stopBtn.disabled = true;
            stopBtn.title = `No monitors attached to ${activeNode.name}`;
        }
    } else if (count === 1) {
        if (emptyState) emptyState.style.display = 'none';
        if (defaultsBanner) defaultsBanner.style.display = '';
        if (monitorsGrid) {
            monitorsGrid.style.display = 'grid';
            monitorsGrid.style.gridTemplateColumns = '1fr';
        }
        if (mon1Card) mon1Card.style.display = '';
        if (mon2Card) mon2Card.style.display = 'none';
        if (mon1SingleBtn) mon1SingleBtn.style.display = 'none';
        if (primaryBtn) primaryBtn.style.display = 'inline-flex';
        if (primaryLabel) primaryLabel.textContent = 'Apply Display';
        if (headingText) headingText.textContent = 'Monitor Controller';
        if (subtext) subtext.textContent = 'Configure orientation and content for the attached display';
        if (mixerTabLabel) mixerTabLabel.textContent = 'Monitor Mixer';
        if (wakeBtn) {
            wakeBtn.disabled = false;
            wakeBtn.title = 'Turn screen on';
        }
        if (stopBtn) {
            stopBtn.disabled = false;
            stopBtn.title = 'Turn screen off';
        }
    } else {
        if (emptyState) emptyState.style.display = 'none';
        if (defaultsBanner) defaultsBanner.style.display = '';
        if (monitorsGrid) {
            monitorsGrid.style.display = 'grid';
            monitorsGrid.style.gridTemplateColumns = '';
        }
        if (mon1Card) mon1Card.style.display = '';
        if (mon2Card) mon2Card.style.display = '';
        if (mon1SingleBtn) mon1SingleBtn.style.display = 'inline-flex';
        if (primaryBtn) primaryBtn.style.display = 'inline-flex';
        if (primaryLabel) primaryLabel.textContent = 'Apply Both Monitors';
        if (headingText) headingText.textContent = 'Dual Monitor Mixer';
        if (subtext) subtext.textContent = 'Control Monitor 1 and Monitor 2 with different websites, slideshows, or images independently';
        if (mixerTabLabel) mixerTabLabel.textContent = 'Dual Monitor Mixer';
        if (wakeBtn) {
            wakeBtn.disabled = false;
            wakeBtn.title = 'Turn screens on';
        }
        if (stopBtn) {
            stopBtn.disabled = false;
            stopBtn.title = 'Turn screens off';
        }
    }
}

export function renderMonitorRotationControls() {
    ['1', '2'].forEach(monId => {
        const select = document.getElementById(`mixerMon${monId}Rotation`);
        if (!select) return;

        const mon = appState.monitors.find(m => String(m.index) === String(monId)) || null;
        const currentRot = (mon && mon.current_rotation) || appState.monitorDefaults[monId] || 'normal';
        const defaultRot = appState.monitorDefaults[monId] || 'normal';

        // Populate options if empty
        if (select.children.length === 0 && appState.availableRotations.length > 0) {
            select.innerHTML = appState.availableRotations.map(r =>
                `<option value="${escapeHtml(r.value)}">${escapeHtml(r.label)}</option>`
            ).join('');
        }

        // Set value to current active rotation
        select.value = currentRot;

        // Update connector badge & resolution badge on monitor card
        const hwBadge = document.getElementById(`mon${monId}HwBadge`);
        if (hwBadge) {
            if (mon && mon.name) {
                hwBadge.textContent = mon.name;
            } else {
                hwBadge.textContent = `HDMI-${monId}`;
            }
        }

        const resBadge = document.getElementById(`mon${monId}ResBadge`);
        if (resBadge) {
            if (mon && mon.width && mon.height) {
                resBadge.textContent = `${mon.width}×${mon.height}`;
            } else {
                resBadge.textContent = '1080p';
            }
        }

        // Update badge and default indicator
        const badge = document.getElementById(`mixerMon${monId}RotationBadge`);
        if (badge) {
            const rotMeta = appState.availableRotations.find(r => r.value === currentRot);
            const label = rotMeta ? rotMeta.label.split('(')[0].trim() : currentRot;
            const isDefault = currentRot === defaultRot;

            badge.innerHTML = `
                <span class="active-rot-pill">${escapeHtml(label)}</span>
                ${isDefault
                    ? `<span class="default-star-badge" title="Saved as Startup Default">${getIcon('star')} Default</span>`
                    : `<span class="default-rot-hint">Default: ${escapeHtml(defaultRot)}</span>`}
            `;
        }

        // Update preview frame orientation aspect ratio indicator
        const previewFrame = document.getElementById(`mon${monId}PreviewFrame`);
        const orientBadge = document.getElementById(`mon${monId}OrientationBadge`);
        const isPortrait = ['left', 'right'].includes(currentRot);

        if (previewFrame) {
            if (isPortrait) {
                previewFrame.classList.add('is-portrait');
            } else {
                previewFrame.classList.remove('is-portrait');
            }
        }

        if (orientBadge) {
            orientBadge.textContent = isPortrait ? 'Portrait' : 'Landscape';
            orientBadge.className = `preview-orientation-badge ${isPortrait ? 'portrait' : 'landscape'}`;
        }
    });
}

export function updateHardwareStatusBar() {
    const bar = document.getElementById('hardwareDefaultsSummary');
    const avail = getAvailableMonitors();
    const count = avail.length;
    const def1 = appState.monitorDefaults['1'] || 'left';
    const def2 = appState.monitorDefaults['2'] || 'right';

    const getCleanName = (val) => {
        const r = (appState.availableRotations || []).find(x => x.value === val);
        return r ? r.label.split('/')[0].replace('Landscape', 'Land').replace('Portrait', 'Port').replace('(', '').trim() : val;
    };

    if (bar) {
        if (count === 0) {
            bar.innerHTML = '';
        } else if (count === 1) {
            bar.innerHTML = `
                <span class="def-mon-tag">Mon 1: <strong>${escapeHtml(getCleanName(def1))}</strong></span>
            `;
        } else {
            bar.innerHTML = `
                <span class="def-mon-tag">Mon 1: <strong>${escapeHtml(getCleanName(def1))}</strong></span>
                <span class="def-mon-separator">&bull;</span>
                <span class="def-mon-tag">Mon 2: <strong>${escapeHtml(getCleanName(def2))}</strong></span>
            `;
        }
    }

    // Update sidebar hardware summary for active Pi
    const activeNode = getActiveNode();
    const sbDot = document.getElementById('sidebarHwDot');
    const sbTarget = document.getElementById('sidebarActivePi');
    const sbHost = document.getElementById('sidebarHostVal');
    const sbMon1Row = document.getElementById('sidebarMon1Row');
    const sbMon2Row = document.getElementById('sidebarMon2Row');
    const sbRow1 = document.getElementById('sidebarMon1Rot');
    const sbRow2 = document.getElementById('sidebarMon2Rot');
    const sbDisplays = document.getElementById('sidebarDisplayMode');

    if (sbTarget) sbTarget.textContent = activeNode.name || 'Main Pi';
    if (sbHost) sbHost.textContent = formatHostShort(activeNode.url || 'pi.spear.ac');
    if (sbDot) {
        sbDot.classList.toggle('is-empty', appState.monitorsLoaded && count === 0);
    }
    if (sbDisplays) {
        if (!appState.monitorsLoaded) {
            sbDisplays.textContent = 'Checking...';
        } else if (count === 0) {
            sbDisplays.textContent = 'No Display';
        } else if (count === 1) {
            sbDisplays.textContent = `1 Display (${avail[0].name || 'HDMI-1'})`;
        } else {
            sbDisplays.textContent = `${count} Displays`;
        }
    }
    if (sbMon1Row) {
        sbMon1Row.style.display = (appState.monitorsLoaded && count < 1) ? 'none' : '';
    }
    if (sbMon2Row) {
        sbMon2Row.style.display = (appState.monitorsLoaded && count < 2) ? 'none' : '';
    }
    if (sbRow1) sbRow1.textContent = def1;
    if (sbRow2) sbRow2.textContent = def2;
}

export async function handleApplyMonitorRotation(monId) {
    const select = document.getElementById(`mixerMon${monId}Rotation`);
    const saveDefaultBox = document.getElementById(`mixerMon${monId}SaveDefault`);
    if (!select) return;

    const rotation = select.value;
    const saveDefault = saveDefaultBox ? saveDefaultBox.checked : false;
    const activeNode = getActiveNode();

    try {
        showToast(`${activeNode.name}: Applying ${rotation} rotation to Monitor ${monId}...`, 'info');
        const res = await apiFetch('/api/display/rotate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                monitor: String(monId),
                rotation: rotation,
                save_default: saveDefault,
                restart_browser: true
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || `Monitor ${monId} rotated to ${rotation}`, 'success');
            await loadMonitorsData();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast(`Error rotating monitor ${monId}: ` + err.message, 'error');
    }
}

export async function handleSetDefaultRotation(monId) {
    const select = document.getElementById(`mixerMon${monId}Rotation`);
    if (!select) return;

    const rotation = select.value;
    const activeNode = getActiveNode();
    try {
        showToast(`${activeNode.name}: Saving ${rotation} as startup default for Monitor ${monId}...`, 'info');
        const res = await apiFetch('/api/display/defaults', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rotations: { [String(monId)]: rotation },
                apply_now: false
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Monitor ${monId} startup default saved as ${rotation}`, 'success');
            await loadMonitorsData();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error saving default: ' + err.message, 'error');
    }
}

export async function handleSaveAllCurrentAsDefault() {
    const avail = getAvailableMonitors();
    if (avail.length === 0) {
        showToast('No monitors attached to save defaults for', 'info');
        return;
    }
    const sel1 = document.getElementById('mixerMon1Rotation');
    const sel2 = document.getElementById('mixerMon2Rotation');
    const rot1 = sel1 ? sel1.value : (appState.monitorDefaults['1'] || 'left');
    const rot2 = sel2 ? sel2.value : (appState.monitorDefaults['2'] || 'right');
    const rotations = avail.length >= 2 ? { "1": rot1, "2": rot2 } : { "1": rot1 };
    const activeNode = getActiveNode();

    try {
        showToast(`${activeNode.name}: Saving current rotation(s) as startup default...`, 'info');
        const res = await apiFetch('/api/display/defaults', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rotations,
                apply_now: false
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(
                avail.length >= 2
                    ? 'Saved both monitor rotations as startup defaults!'
                    : 'Saved Monitor 1 rotation as startup default!',
                'success'
            );
            await loadMonitorsData();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error saving defaults: ' + err.message, 'error');
    }
}

export async function handleResetToDefaults() {
    const activeNode = getActiveNode();
    try {
        showToast(`${activeNode.name}: Restoring monitors to saved startup defaults...`, 'info');
        const res = await apiFetch('/api/display/reset-defaults', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ restart_browser: true })
        });

        const data = await res.json();
        if (data.success) {
            showToast('Monitors restored to default rotations!', 'success');
            await loadMonitorsData();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error restoring defaults: ' + err.message, 'error');
    }
}
