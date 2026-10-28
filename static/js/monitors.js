/**
 * Monitor Hardware, Orientations & Default Persistence Management
 */

import { appState, showToast, escapeHtml, apiFetch, getActiveNode, formatHostShort } from './state.js';
import { getIcon } from './icons.js';

export async function loadMonitorsData() {
    try {
        const res = await apiFetch('/api/display/monitors');
        const data = await res.json();
        if (res.ok && data.success) {
            appState.monitors = data.monitors || [];
            appState.monitorDefaults = data.defaults || { "1": "left", "2": "right" };
            appState.availableRotations = data.available_rotations || [];

            renderMonitorRotationControls();
            updateHardwareStatusBar();
        }
    } catch (err) {
        console.error('Error fetching monitor configurations:', err);
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
    const def1 = appState.monitorDefaults['1'] || 'left';
    const def2 = appState.monitorDefaults['2'] || 'right';

    const getCleanName = (val) => {
        const r = (appState.availableRotations || []).find(x => x.value === val);
        return r ? r.label.split('/')[0].replace('Landscape', 'Land').replace('Portrait', 'Port').replace('(', '').trim() : val;
    };

    if (bar) {
        bar.innerHTML = `
            <span class="def-mon-tag">Mon 1: <strong>${escapeHtml(getCleanName(def1))}</strong></span>
            <span class="def-mon-separator">&bull;</span>
            <span class="def-mon-tag">Mon 2: <strong>${escapeHtml(getCleanName(def2))}</strong></span>
        `;
    }

    // Update sidebar hardware summary for active Pi
    const activeNode = getActiveNode();
    const sbTarget = document.getElementById('sidebarActivePi');
    const sbHost = document.getElementById('sidebarHostVal');
    const sbRow1 = document.getElementById('sidebarMon1Rot');
    const sbRow2 = document.getElementById('sidebarMon2Rot');
    const sbDisplays = document.getElementById('sidebarDisplayMode');

    if (sbTarget) sbTarget.textContent = activeNode.name || 'Main Pi';
    if (sbHost) sbHost.textContent = formatHostShort(activeNode.url || 'pi.spear.ac');
    if (sbDisplays) {
        const count = appState.monitors.length || 2;
        sbDisplays.textContent = count === 1 ? 'Single HDMI' : `${count} Displays`;
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
    const sel1 = document.getElementById('mixerMon1Rotation');
    const sel2 = document.getElementById('mixerMon2Rotation');
    const rot1 = sel1 ? sel1.value : (appState.monitorDefaults['1'] || 'left');
    const rot2 = sel2 ? sel2.value : (appState.monitorDefaults['2'] || 'right');
    const activeNode = getActiveNode();

    try {
        showToast(`${activeNode.name}: Saving current rotations as startup defaults...`, 'info');
        const res = await apiFetch('/api/display/defaults', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rotations: { "1": rot1, "2": rot2 },
                apply_now: false
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast('Saved both monitor rotations as startup defaults!', 'success');
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
