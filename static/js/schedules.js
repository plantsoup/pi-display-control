/**
 * Time-based Scheduler Management
 */

import { appState, showToast, escapeHtml } from './state.js';

export async function loadSchedules() {
    try {
        const res = await fetch('/api/schedules');
        const schedules = await res.json();
        appState.schedules = schedules;
        const countBadge = document.getElementById('scheduleCountBadge');
        if (countBadge) countBadge.textContent = schedules.length;
        renderSchedulesList();
    } catch (err) {
        showToast('Error loading schedules: ' + err.message, 'error');
    }
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

        row.innerHTML = `
            <div class="schedule-time-box">
                <div class="schedule-time">${escapeHtml(sch.time)}</div>
                <div class="schedule-info">
                    <h4>${escapeHtml(sch.name)}</h4>
                    <p>${actionDesc} &bull; Target: ${sch.params?.monitor || 'both'}</p>
                </div>
            </div>
            <div class="schedule-controls">
                <label class="switch" title="Toggle active/inactive">
                    <input type="checkbox" ${sch.enabled ? 'checked' : ''} onchange="toggleSchedule('${sch.id}')">
                    <span class="slider"></span>
                </label>
                <button class="btn btn-xs btn-danger" onclick="deleteSchedule('${sch.id}')" title="Delete schedule">
                    🗑️
                </button>
            </div>
        `;
        list.appendChild(row);
    });
}

export function openAddScheduleModal() {
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

    const params = { monitor: monitor };

    if (action === 'slideshow') {
        params.mode = document.getElementById('scheduleSlideshowMode').value;
        params.interval = parseInt(document.getElementById('scheduleSlideshowInterval').value) || 30;
    } else if (action === 'website') {
        params.url1 = document.getElementById('scheduleWebsitePicker').value;
    }

    try {
        const res = await fetch('/api/schedules', {
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
        const res = await fetch(`/api/schedules/${scheduleId}/toggle`, { method: 'PUT' });
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
        const res = await fetch(`/api/schedules/${scheduleId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Schedule deleted', 'success');
            appState.schedules = data.schedules;
            const countBadge = document.getElementById('scheduleCountBadge');
            if (countBadge) countBadge.textContent = data.schedules.length;
            renderSchedulesList();
        }
    } catch (err) {
        showToast('Error deleting schedule: ' + err.message, 'error');
    }
}
