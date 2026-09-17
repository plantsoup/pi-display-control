/**
 * Screen Power Controls & Live Status Monitoring
 */

import { showToast } from './state.js';

export async function fetchLiveStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.success) {
            const state = data.state;
            const badgeText = document.getElementById('liveStatusText');
            const badge = document.getElementById('liveStatusBadge');
            if (!badgeText || !badge) return;

            if (state.status === 'blank') {
                badgeText.textContent = 'Screens Off (Blanked)';
                badge.style.color = '#ef4444';
            } else if (state.mode === 'slideshow') {
                badgeText.textContent = `Slideshow Active (${state.monitor || 'both'})`;
                badge.style.color = '#6366f1';
            } else if (state.mode === 'website') {
                badgeText.textContent = `Website Active (${state.monitor || 'both'})`;
                badge.style.color = '#10b981';
            } else if (state.mode === 'mixed') {
                badgeText.textContent = `Mixed Display Active (${state.monitor || 'both'})`;
                badge.style.color = '#8b5cf6';
            } else {
                badgeText.textContent = 'Display Active';
                badge.style.color = '#10b981';
            }
        }
    } catch (err) {
        console.error('Error fetching live status:', err);
    }
}

export async function handleBlankDisplay() {
    try {
        showToast('Turning screens off...', 'info');
        const res = await fetch('/api/display', { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Displays blanked (screens turned off)', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error blanking display: ' + err.message, 'error');
    }
}

export async function handleWakeDisplay() {
    try {
        showToast('Waking screens...', 'info');
        const res = await fetch('/api/display/wake', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('Displays woken up', 'success');
            fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error waking display: ' + err.message, 'error');
    }
}
