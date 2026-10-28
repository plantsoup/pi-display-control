/**
 * Time-based Scheduler Management
 */

import {
    appState,
    showToast,
    escapeHtml,
    apiFetch,
    isRemoteActive,
    getAvailableMonitors,
    formatHostShort
} from './state.js';
import { getIcon } from './icons.js';

export async function loadSchedules() {
    try {
        const res = await apiFetch('/api/schedules');
        const schedules = await res.json();
        if (!Array.isArray(schedules)) return;

        appState.schedules = schedules;
        const countBadge = document.getElementById('scheduleCountBadge');
        if (countBadge) countBadge.textContent = schedules.length;
        renderSchedulesList();
    } catch (err) {
        showToast('Error loading schedules: ' + err.message, 'error');
    }
}

function _getScheduleNodeLabel(targetNode) {
    if (!targetNode || targetNode === 'local') return 'This Pi';
    if (targetNode === 'all') return 'All Connected Pis';
    const found = (appState.allNodes || []).find(n => n.id === targetNode);
    return found ? `${found.name} (${formatHostShort(found.url)})` : targetNode;
}

export function renderSchedulesList() {
    const list = document.getElementById('schedulesList');
    if (!list) return;

    list.innerHTML = '';
    if (appState.schedules.length === 0) {
        list.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No automated schedules set up yet. Click "New Schedule" above to add one!</div>';
        return;
    }

    appState.schedules.forEach(sch => {
        const row = document.createElement('div');
        row.className = 'schedule-row';

        let actionDesc = sch.action;
        if (sch.action === 'slideshow') {
            const mode = (sch.params && sch.params.mode) || 'random';
            const interval = (sch.params && sch.params.interval) || 30;
            actionDesc = `Start ${mode} slideshow (every ${interval}s)`;
        } else if (sch.action === 'website') {
            actionDesc = `Switch to website/Autodarts`;
        } else if (sch.action === 'blank') {
            actionDesc = `Blank screen (Sleep)`;
        } else if (sch.action === 'wake') {
            actionDesc = `Wake screen (Turn on)`;
        }

        const targetNode = sch.params?.target_node || 'local';
        const nodeLabel = _getScheduleNodeLabel(targetNode);

        row.innerHTML = `
            <div class="schedule-time-box">
                <div class="schedule-time">${escapeHtml(sch.time)}</div>
                <div class="schedule-info">
                    <h4>${escapeHtml(sch.name)}</h4>
                    <p>${escapeHtml(actionDesc)} &bull; Pi: <strong>${escapeHtml(nodeLabel)}</strong> &bull; Monitor: ${escapeHtml(sch.params?.monitor || 'both')}</p>
                </div>
            </div>
            <div class="schedule-controls">
                <label class="switch" title="Toggle active/inactive">
                    <input type="checkbox" ${sch.enabled ? 'checked' : ''} onchange="toggleSchedule('${escapeHtml(sch.id)}')">
                    <span class="slider"></span>
                </label>
                <button class="btn btn-xs btn-danger" onclick="deleteSchedule('${escapeHtml(sch.id)}')" title="Delete schedule">
                    ${getIcon('trash')}
                </button>
            </div>
        `;
        list.appendChild(row);
    });
}

export function populateScheduleTargetNodes() {
    const select = document.getElementById('scheduleTargetNode');
    const group = document.getElementById('scheduleTargetNodeGroup');
    if (!select) return;

    const prevVal = select.value;

    if (isRemoteActive()) {
        if (group) group.style.display = 'none';
        select.innerHTML = '<option value="local" selected>This Pi Only</option>';
        populateScheduleMonitorOptions();
        return;
    }

    if (group) group.style.display = 'flex';
    const localLabel = `${appState.localNode.name} Only (${formatHostShort(appState.localNode.url)})`;
    let html = `<option value="local">${escapeHtml(localLabel)}</option>`;
    if ((appState.remoteNodes || []).length > 0) {
        html += `<option value="all">All Connected Pis</option>`;
        appState.remoteNodes.forEach(n => {
            html += `<option value="${escapeHtml(n.id)}">${escapeHtml(n.name)} (${escapeHtml(formatHostShort(n.url))})</option>`;
        });
    }
    select.innerHTML = html;
    if (prevVal && Array.from(select.options).some(o => o.value === prevVal)) {
        select.value = prevVal;
    }
    select.onchange = () => populateScheduleMonitorOptions();
    populateScheduleMonitorOptions();
}

export function populateScheduleMonitorOptions() {
    const monSelect = document.getElementById('scheduleMonitor');
    if (!monSelect) return;

    const targetSelect = document.getElementById('scheduleTargetNode');
    const targetVal = (!isRemoteActive() && targetSelect) ? (targetSelect.value || 'local') : 'local';
    const prevMon = monSelect.value;

    let targetCount = null;
    if (targetVal === 'all') {
        targetCount = 2;
    } else if (isRemoteActive()) {
        targetCount = appState.monitorsLoaded ? getAvailableMonitors().length : null;
    } else if (targetVal === 'local') {
        const localOv = (appState.nodesOverview || []).find(n => n.id === 'local');
        if (localOv && localOv.online) {
            targetCount = getAvailableMonitors(localOv.monitors).length;
        } else if (appState.monitorsLoaded) {
            targetCount = getAvailableMonitors().length;
        }
    } else {
        const remoteOv = (appState.nodesOverview || []).find(n => n.id === targetVal);
        if (remoteOv && remoteOv.online) {
            targetCount = getAvailableMonitors(remoteOv.monitors).length;
        }
    }

    if (targetCount === 1) {
        monSelect.innerHTML = `<option value="1">Monitor 1</option>`;
    } else if (targetCount === 0) {
        monSelect.innerHTML = `<option value="1">First Attached Monitor (None Currently Connected)</option>`;
    } else {
        monSelect.innerHTML = `
            <option value="both">Both Monitors</option>
            <option value="1">Monitor 1 Only</option>
            <option value="2">Monitor 2 Only</option>
        `;
        if (prevMon && ['both', '1', '2'].includes(prevMon)) {
            monSelect.value = prevMon;
        }
    }
}

export function openAddScheduleModal() {
    populateScheduleTargetNodes();
    populateScheduleMonitorOptions();
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'flex';
}

export function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'none';
}

export function onScheduleActionChange() {
    const actionEl = document.getElementById('scheduleAction');
    const slideshowOptions = document.getElementById('scheduleSlideshowOptions');
    const websiteOptions = document.getElementById('scheduleWebsiteOptions');
    const monitorGroup = document.getElementById('scheduleMonitorGroup');

    if (!actionEl) return;
    const action = actionEl.value;

    if (action === 'slideshow') {
        if (slideshowOptions) slideshowOptions.style.display = 'block';
        if (websiteOptions) websiteOptions.style.display = 'none';
        if (monitorGroup) monitorGroup.style.display = 'block';
    } else if (action === 'website') {
        if (slideshowOptions) slideshowOptions.style.display = 'none';
        if (websiteOptions) websiteOptions.style.display = 'block';
        if (monitorGroup) monitorGroup.style.display = 'block';
    } else {
        if (slideshowOptions) slideshowOptions.style.display = 'none';
        if (websiteOptions) websiteOptions.style.display = 'none';
        if (monitorGroup) monitorGroup.style.display = 'none';
    }
}

export async function handleCreateSchedule(e) {
    e.preventDefault();
    const name = document.getElementById('scheduleName').value.trim();
    const timeVal = document.getElementById('scheduleTime').value.trim();
    const action = document.getElementById('scheduleAction').value;
    const monitor = document.getElementById('scheduleMonitor').value;
    const targetNodeEl = document.getElementById('scheduleTargetNode');
    const targetNode = (!isRemoteActive() && targetNodeEl) ? targetNodeEl.value : 'local';

    const params = {
        monitor: monitor,
        target_node: targetNode
    };

    if (action === 'slideshow') {
        params.mode = document.getElementById('scheduleSlideshowMode').value;
        params.interval = parseInt(document.getElementById('scheduleSlideshowInterval').value) || 30;
    } else if (action === 'website') {
        params.url1 = document.getElementById('scheduleWebsitePicker').value;
    }

    try {
        const res = await apiFetch('/api/schedules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                time: timeVal,
                action: action,
                params: params
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Schedule created successfully!', 'success');
            closeScheduleModal();
            document.getElementById('createScheduleForm').reset();
            appState.schedules = data.schedules;
            const countBadge = document.getElementById('scheduleCountBadge');
            if (countBadge) countBadge.textContent = data.schedules.length;
            renderSchedulesList();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error saving schedule: ' + err.message, 'error');
    }
}

export async function toggleSchedule(scheduleId) {
    try {
        const res = await apiFetch(`/api/schedules/${scheduleId}/toggle`, { method: 'PUT' });
        const data = await res.json();
        if (data.success) {
            appState.schedules = data.schedules;
            renderSchedulesList();
        }
    } catch (err) {
        showToast('Error toggling schedule: ' + err.message, 'error');
    }
}

export async function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
        const res = await apiFetch(`/api/schedules/${scheduleId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Schedule deleted', 'success');
            appState.schedules = data.schedules;
            const countBadge = document.getElementById('scheduleCountBadge');
            if (countBadge) countBadge.textContent = data.schedules.length;
            renderSchedulesList();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error deleting schedule: ' + err.message, 'error');
    }
}
