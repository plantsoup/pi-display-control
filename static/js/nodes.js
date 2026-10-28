/**
 * Connected Pis & Multi-Display Fleet Management
 * Connects Main Pi (pi.spear.ac), Secondary Pi (pi2.spear.ac), and additional Pi Display Control nodes.
 */

import {
    appState,
    showToast,
    escapeHtml,
    isRemoteActive,
    getActiveNode,
    formatHostShort
} from './state.js';
import { getIcon } from './icons.js';
import { fetchLiveStatus } from './display.js';
import { renderWebsitesGrid } from './websites.js';
import { renderImagesGrid } from './images.js';
import { populateScheduleTargetNodes } from './schedules.js';

export async function loadNodesConfig() {
    try {
        const res = await fetch('/api/nodes');
        const data = await res.json();
        if (data.success) {
            appState.localNode = data.local || appState.localNode;
            appState.remoteNodes = data.nodes || [];
            appState.allNodes = data.all_nodes || [appState.localNode, ...appState.remoteNodes];
            appState.mainBaseUrl = data.main_base_url || appState.localNode.url;

            // If active node was deleted, revert to local
            if (isRemoteActive() && !appState.allNodes.some(n => n.id === appState.activeNodeId)) {
                appState.activeNodeId = 'local';
            }

            _updateNodeCountBadge();
            renderNodeSwitcherBar();
            populateBroadcastOptions();
            populateScheduleTargetNodes();
            renderWebsitesGrid();
            renderImagesGrid();
            if (appState.nodesOverview.length === 0) {
                renderNodesGrid();
            }
        }
    } catch (err) {
        console.error('Error loading Pi nodes config:', err);
    }
}

export async function refreshNodesOverview(showFeedback = false) {
    try {
        if (showFeedback) {
            showToast('Polling connected Pis & displays...', 'info');
        }
        const res = await fetch('/api/nodes/overview');
        const data = await res.json();
        if (data.success) {
            appState.nodesOverview = data.nodes || [];
            _updateNodeCountBadge();
            renderNodeSwitcherBar();
            populateBroadcastOptions();
            renderNodesGrid();
            if (showFeedback) {
                const online = data.summary?.online_nodes ?? appState.nodesOverview.filter(n => n.online).length;
                const total = data.summary?.total_nodes ?? appState.nodesOverview.length;
                showToast(`Connected Pis refreshed (${online}/${total} online)`, 'success');
            }
        }
    } catch (err) {
        console.error('Error refreshing nodes overview:', err);
        if (showFeedback) {
            showToast('Error polling Pis: ' + err.message, 'error');
        }
    }
}

function _updateNodeCountBadge() {
    const badge = document.getElementById('nodeCountBadge');
    if (!badge) return;
    if (appState.nodesOverview.length > 0) {
        const online = appState.nodesOverview.filter(n => n.online).length;
        badge.textContent = `${online}/${appState.nodesOverview.length}`;
    } else {
        badge.textContent = String((appState.allNodes || []).length || 1);
    }
}

function _getMergedNodesList() {
    if (appState.nodesOverview && appState.nodesOverview.length > 0) {
        return appState.nodesOverview;
    }
    return (appState.allNodes || [appState.localNode]).map(n => ({
        ...n,
        online: Boolean(n.is_local),
        monitors: [],
        monitor_count: 2
    }));
}

export async function switchActiveNode(nodeId, jumpToMixer = false) {
    const prevId = appState.activeNodeId;
    appState.activeNodeId = nodeId || 'local';
    const target = getActiveNode();

    renderNodeSwitcherBar();
    renderNodesGrid();

    if (jumpToMixer) {
        const mixerTabBtn = document.querySelector('.nav-tab[data-tab="mixerTab"]');
        if (mixerTabBtn) mixerTabBtn.click();
    }

    if (prevId !== appState.activeNodeId) {
        showToast(`Now controlling ${target.name} (${formatHostShort(target.url)})`, 'info');
    }

    if (typeof window.refreshActiveNodeData === 'function') {
        await window.refreshActiveNodeData();
    }
}

export function renderNodeSwitcherBar() {
    const pillsContainer = document.getElementById('nodeSwitcherPills');
    const actionsContainer = document.getElementById('nodeSwitcherRight');
    const mixerAllBtn = document.getElementById('applyMixerAllPisBtn');
    const slideshowAllBtn = document.getElementById('launchSlideshowAllPisBtn');

    const nodes = _getMergedNodesList();
    const hasMultipleNodes = nodes.length > 1;

    if (mixerAllBtn) {
        mixerAllBtn.style.display = hasMultipleNodes ? 'inline-flex' : 'none';
    }
    if (slideshowAllBtn) {
        slideshowAllBtn.style.display = hasMultipleNodes ? 'inline-flex' : 'none';
    }

    if (pillsContainer) {
        pillsContainer.innerHTML = nodes.map(node => {
            const isActive = node.id === appState.activeNodeId;
            const hostShort = formatHostShort(node.url);
            const isBlank = node.online && node.state?.status === 'blank';
            const dotClass = !node.online ? 'offline' : (isBlank ? 'blank' : 'online');
            const monCount = node.monitor_count || (node.monitors ? node.monitors.length : 0);
            const monTag = node.online && monCount > 0 ? `<span class="node-pill-monitors">${monCount} disp</span>` : '';

            return `
                <button type="button"
                        class="node-switch-pill ${isActive ? 'active' : ''}"
                        onclick="switchActiveNode('${escapeHtml(node.id)}')"
                        title="${escapeHtml(node.name)} (${escapeHtml(node.url || 'local')}) - ${node.online ? 'Online' : (node.error || 'Unreachable')}">
                    <span class="node-dot ${dotClass}"></span>
                    <span class="node-pill-name">${escapeHtml(node.name)}</span>
                    <span class="node-pill-host">${escapeHtml(hostShort)}</span>
                    ${monTag}
                </button>
            `;
        }).join('') + `
            <button type="button" class="node-add-pill" onclick="openAddNodeModal()" title="Connect another Pi running Pi Display Control">
                ${getIcon('plus')}
                <span>Connect Pi</span>
            </button>
        `;
    }

    if (actionsContainer) {
        const activeNode = getActiveNode();
        let rightHtml = '';

        if (isRemoteActive()) {
            const remoteUrl = activeNode.url || '#';
            rightHtml += `
                <span class="remote-control-banner-pill">
                    ${getIcon('link')}
                    <span>Remote: <strong>${escapeHtml(formatHostShort(remoteUrl))}</strong></span>
                    <a href="${escapeHtml(remoteUrl)}" target="_blank" rel="noopener" class="remote-ext-link" title="Open ${escapeHtml(remoteUrl)} directly">
                        ${getIcon('externalLink')}
                    </a>
                </span>
            `;
        }

        if (hasMultipleNodes) {
            rightHtml += `
                <button type="button" class="btn btn-xs btn-neutral" onclick="handleFleetPower('wake')" title="Wake displays on all connected Pis">
                    ${getIcon('sun')}
                    <span>Wake All Pis</span>
                </button>
                <button type="button" class="btn btn-xs btn-muted-danger" onclick="handleFleetPower('blank')" title="Blank displays on all connected Pis">
                    ${getIcon('moon')}
                    <span>Blank All Pis</span>
                </button>
            `;
        }

        actionsContainer.innerHTML = rightHtml;
    }
}

export function populateBroadcastOptions() {
    const webSelect = document.getElementById('broadcastWebsitePicker');
    const imgSelect = document.getElementById('broadcastImagePicker');

    const sites = (appState.mainWebsites && appState.mainWebsites.length > 0)
        ? appState.mainWebsites
        : appState.websites;
    if (webSelect) {
        webSelect.innerHTML = sites.map(w =>
            `<option value="${escapeHtml(w.url || '')}">${escapeHtml(w.name)} (${w.url ? escapeHtml(w.url) : 'Autodarts default'})</option>`
        ).join('');
    }

    const imgs = (appState.mainImages && appState.mainImages.length > 0)
        ? appState.mainImages
        : appState.images;
    if (imgSelect) {
        if (imgs.length === 0) {
            imgSelect.innerHTML = '<option value="">(No uploaded images on Main Pi)</option>';
        } else {
            imgSelect.innerHTML = imgs.map(i =>
                `<option value="${escapeHtml(i.filename)}">${escapeHtml(i.name)}</option>`
            ).join('');
        }
    }

    onBroadcastTypeChange();
}

export function onBroadcastTypeChange() {
    const typeEl = document.getElementById('broadcastContentType');
    const webGroup = document.getElementById('broadcastWebsiteGroup');
    const imgGroup = document.getElementById('broadcastImageGroup');
    if (!typeEl) return;

    const val = typeEl.value;
    if (webGroup) webGroup.style.display = val === 'website' ? 'flex' : 'none';
    if (imgGroup) imgGroup.style.display = val === 'main_image' ? 'flex' : 'none';
}

export async function handleBroadcastSubmit() {
    const type = document.getElementById('broadcastContentType')?.value || 'website';
    const monitor = document.getElementById('broadcastMonitorTarget')?.value || 'both';
    let payload = { monitor };

    if (type === 'website') {
        const url = document.getElementById('broadcastWebsitePicker')?.value || '';
        payload.mode = 'website';
        payload.url1 = url;
        payload.url2 = url;
    } else if (type === 'main_slideshow') {
        payload.mode = 'slideshow';
        payload.slideshow_mode = appState.slideshowConfig.mode || 'random';
        payload.interval = appState.slideshowConfig.interval || 30;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = true;
    } else if (type === 'local_slideshow') {
        payload.mode = 'slideshow';
        payload.slideshow_mode = appState.slideshowConfig.mode || 'random';
        payload.interval = appState.slideshowConfig.interval || 30;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = false;
    } else if (type === 'main_image') {
        const img = document.getElementById('broadcastImagePicker')?.value || '';
        if (!img) {
            showToast('Please upload or select an image on Main Pi first', 'error');
            return;
        }
        payload.mode = 'image';
        payload.image1 = img;
        payload.image2 = img;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = true;
    }

    try {
        showToast('Broadcasting display command to all connected Pis...', 'info');
        const res = await fetch('/api/nodes/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'display',
                payload: payload
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Broadcast complete!', 'success');
            fetchLiveStatus();
            refreshNodesOverview(false);
        } else {
            showToast('Broadcast error: ' + (data.error || data.message), 'error');
        }
    } catch (err) {
        showToast('Broadcast error: ' + err.message, 'error');
    }
}

export async function handleFleetPower(action) {
    const verb = action === 'blank' ? 'Blanking screens' : 'Waking screens';
    try {
        showToast(`${verb} across all connected Pis...`, 'info');
        const res = await fetch('/api/nodes/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Updated all Pis!', 'success');
            fetchLiveStatus();
            refreshNodesOverview(false);
        } else {
            showToast('Error: ' + (data.error || data.message), 'error');
        }
    } catch (err) {
        showToast('Fleet command error: ' + err.message, 'error');
    }
}

function _buildQuickPushOptionsHtml() {
    const sites = (appState.mainWebsites && appState.mainWebsites.length > 0)
        ? appState.mainWebsites
        : appState.websites;
    const imgs = (appState.mainImages && appState.mainImages.length > 0)
        ? appState.mainImages
        : appState.images;
    const mainHost = formatHostShort(appState.localNode.url);

    let html = `<optgroup label="Slideshow">`;
    html += `<option value="stream_slideshow">Stream Slideshow from ${escapeHtml(appState.localNode.name)} (${escapeHtml(mainHost)})</option>`;
    html += `<option value="local_slideshow">Run Pi's Own Local Slideshow</option>`;
    html += `</optgroup>`;

    if (sites.length > 0) {
        html += `<optgroup label="Saved Websites">`;
        sites.forEach((s, idx) => {
            html += `<option value="web:${idx}" ${idx === 0 ? 'selected' : ''}>Website: ${escapeHtml(s.name)}</option>`;
        });
        html += `</optgroup>`;
    }

    if (imgs.length > 0) {
        html += `<optgroup label="Images from ${escapeHtml(appState.localNode.name)}">`;
        imgs.forEach(img => {
            html += `<option value="img:${escapeHtml(img.filename)}">Image: ${escapeHtml(img.name)}</option>`;
        });
        html += `</optgroup>`;
    }

    return html;
}

export function renderNodesGrid() {
    const grid = document.getElementById('connectedNodesGrid');
    if (!grid) return;

    const nodes = _getMergedNodesList();
    const pushOptionsHtml = _buildQuickPushOptionsHtml();
    const rotChoices = [
        { value: 'left', label: 'Portrait Left (270°)' },
        { value: 'right', label: 'Portrait Right (90°)' },
        { value: 'normal', label: 'Landscape (0°)' },
        { value: 'inverted', label: 'Inverted (180°)' }
    ];

    grid.innerHTML = nodes.map(node => {
        const isActive = node.id === appState.activeNodeId;
        const isLocal = Boolean(node.is_local);
        const hostShort = formatHostShort(node.url);
        const state = node.state || {};
        const isBlank = node.online && state.status === 'blank';

        let statusLabel = 'Offline / Unreachable';
        let statusClass = 'offline';
        if (node.online) {
            if (isBlank) {
                statusLabel = 'Screens Off (Blanked)';
                statusClass = 'blank';
            } else if (state.mode === 'slideshow') {
                statusLabel = `Slideshow (${state.monitor || 'both'})`;
                statusClass = 'online';
            } else if (state.mode === 'mixed') {
                statusLabel = `Mixed Display (${state.monitor || 'both'})`;
                statusClass = 'online';
            } else if (state.mode === 'website') {
                statusLabel = `Website Active (${state.monitor || 'both'})`;
                statusClass = 'online';
            } else {
                statusLabel = 'Online & Ready';
                statusClass = 'online';
            }
        } else if (!node.enabled) {
            statusLabel = 'Disabled';
        }

        const latencyTag = isLocal
            ? `<span class="node-latency-badge">This Pi</span>`
            : (node.online && node.latency_ms !== null && node.latency_ms !== undefined
                ? `<span class="node-latency-badge">${node.latency_ms}ms</span>`
                : '');

        const monitors = (node.monitors && node.monitors.length > 0) ? node.monitors : [
            { index: 1, name: 'HDMI-1', current_rotation: node.defaults?.['1'] || 'normal', width: 1920, height: 1080 },
            { index: 2, name: 'HDMI-2', current_rotation: node.defaults?.['2'] || 'normal', width: 1920, height: 1080 }
        ];

        const monitorsHtml = monitors.map(m => {
            const idx = m.index || 1;
            const curRot = m.current_rotation || 'normal';
            const resText = (m.width && m.height) ? `${m.width}×${m.height}` : '';
            const rotSelectHtml = rotChoices.map(rc =>
                `<option value="${rc.value}" ${rc.value === curRot ? 'selected' : ''}>${rc.label}</option>`
            ).join('');

            return `
                <div class="node-monitor-row">
                    <div class="node-monitor-meta">
                        <span class="monitor-badge mon${idx}-accent">Monitor ${idx}</span>
                        <span class="node-mon-connector">${escapeHtml(m.name || `HDMI-${idx}`)}</span>
                        ${resText ? `<span class="node-mon-res">${escapeHtml(resText)}</span>` : ''}
                    </div>
                    <div class="node-monitor-controls">
                        <select id="nodeRot_${escapeHtml(node.id)}_${idx}" class="form-select node-inline-select" ${!node.online ? 'disabled' : ''}>
                            ${rotSelectHtml}
                        </select>
                        <button type="button" class="btn btn-xs btn-subtle-secondary"
                                onclick="handleNodeQuickRotate('${escapeHtml(node.id)}', '${idx}')"
                                ${!node.online ? 'disabled' : ''}
                                title="Rotate Monitor ${idx} on ${escapeHtml(node.name)}">
                            ${getIcon('rotate')} Rotate
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        const counts = node.counts || {};
        const statsHtml = node.online ? `
            <div class="node-stats-strip">
                <span><strong>${monitors.length}</strong> Displays</span>
                <span>&bull;</span>
                <span><strong>${counts.websites ?? 0}</strong> Websites</span>
                <span>&bull;</span>
                <span><strong>${counts.images ?? 0}</strong> Images</span>
                <span>&bull;</span>
                <span><strong>${counts.active_schedules ?? 0}</strong> Active Schedules</span>
            </div>
        ` : `
            <div class="node-offline-hint">
                ${escapeHtml(node.error || `Cannot reach Pi Display Control at ${node.url}. Ensure app.py is running on ${hostShort}.`)}
            </div>
        `;

        return `
            <div class="card node-device-card ${isActive ? 'is-active-node' : ''} ${!node.online ? 'is-offline-node' : ''}">
                <div class="card-header node-card-header">
                    <div class="node-header-top flex-between">
                        <div class="node-identity">
                            <span class="node-dot ${statusClass}"></span>
                            <h3>${escapeHtml(node.name)}</h3>
                            <span class="node-role-badge ${isLocal ? 'role-main' : 'role-secondary'}">
                                ${isLocal ? 'Main / Local' : escapeHtml(node.role || 'Secondary')}
                            </span>
                            ${isActive ? '<span class="node-active-tag">Active in Dashboard</span>' : ''}
                        </div>
                        <div class="node-status-group">
                            ${latencyTag}
                            <span class="node-state-pill ${statusClass}">${escapeHtml(statusLabel)}</span>
                        </div>
                    </div>
                    <div class="node-url-row flex-between">
                        <a href="${escapeHtml(node.url || '#')}" target="_blank" rel="noopener" class="node-url-link">
                            ${getIcon('globe')}
                            <span>${escapeHtml(node.url || 'Local Server')}</span>
                            ${getIcon('externalLink')}
                        </a>
                        ${statsHtml}
                    </div>
                </div>

                <div class="card-body node-card-body">
                    <div class="node-section-label">Connected Displays &amp; Orientation</div>
                    <div class="node-monitors-list">
                        ${monitorsHtml}
                    </div>

                    <div class="node-section-label" style="margin-top: 14px;">Quick Display Content Push</div>
                    <div class="node-quick-push-bar">
                        <select id="nodePushContent_${escapeHtml(node.id)}" class="form-select node-push-select" ${!node.online ? 'disabled' : ''}>
                            ${pushOptionsHtml}
                        </select>
                        <select id="nodePushMonitor_${escapeHtml(node.id)}" class="form-select node-mon-target-select" ${!node.online ? 'disabled' : ''}>
                            <option value="both">Both Displays</option>
                            <option value="1">Monitor 1</option>
                            <option value="2">Monitor 2</option>
                        </select>
                        <button type="button" class="btn btn-sm btn-primary"
                                onclick="handleNodeQuickPush('${escapeHtml(node.id)}')"
                                ${!node.online ? 'disabled' : ''}>
                            ${getIcon('rocket')}
                            <span>Display</span>
                        </button>
                    </div>

                    <div class="node-card-actions-bar">
                        <button type="button" class="btn btn-xs ${isActive ? 'btn-primary' : 'btn-subtle-secondary'}"
                                onclick="switchActiveNode('${escapeHtml(node.id)}', true)">
                            ${getIcon('sliders')}
                            <span>${isActive ? 'Open in Mixer' : 'Control in Dashboard'}</span>
                        </button>
                        <button type="button" class="btn btn-xs btn-neutral"
                                onclick="handleNodePower('${escapeHtml(node.id)}', 'wake')"
                                ${!node.online ? 'disabled' : ''}>
                            ${getIcon('sun')} Wake
                        </button>
                        <button type="button" class="btn btn-xs btn-muted-danger"
                                onclick="handleNodePower('${escapeHtml(node.id)}', 'blank')"
                                ${!node.online ? 'disabled' : ''}>
                            ${getIcon('moon')} Blank
                        </button>
                        ${!isLocal ? `
                            <button type="button" class="btn btn-xs btn-subtle-secondary"
                                    onclick="handleSyncNode('${escapeHtml(node.id)}', false)"
                                    title="Copy saved websites &amp; slideshow settings from Main Pi to ${escapeHtml(node.name)}">
                                ${getIcon('sync')} Sync Websites
                            </button>
                            <button type="button" class="btn btn-xs btn-subtle-secondary"
                                    onclick="handleSyncNode('${escapeHtml(node.id)}', true)"
                                    title="Copy websites, slideshow settings, and uploaded images to ${escapeHtml(node.name)}">
                                ${getIcon('upload')} Sync Images
                            </button>
                            <button type="button" class="btn btn-xs btn-subtle-secondary"
                                    onclick="handleProbeExistingNode('${escapeHtml(node.id)}')"
                                    title="Test connection to ${escapeHtml(node.url)}">
                                ${getIcon('check')} Test
                            </button>
                            <button type="button" class="btn btn-xs btn-subtle-secondary"
                                    onclick="openEditNodeModal('${escapeHtml(node.id)}')"
                                    title="Edit ${escapeHtml(node.name)} connection settings">
                                ${getIcon('edit')} Edit
                            </button>
                            <button type="button" class="btn btn-xs btn-danger"
                                    onclick="handleDeleteNode('${escapeHtml(node.id)}')"
                                    title="Disconnect ${escapeHtml(node.name)}">
                                ${getIcon('trash')}
                            </button>
                        ` : `
                            <button type="button" class="btn btn-xs btn-subtle-secondary"
                                    onclick="openEditNodeModal('local')"
                                    title="Configure Main Pi name and public URL (e.g. https://pi.spear.ac)">
                                ${getIcon('edit')} Edit Host URL
                            </button>
                        `}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

export async function handleNodePower(nodeId, action) {
    const verb = action === 'blank' ? 'Blanking' : 'Waking';
    try {
        showToast(`${verb} displays...`, 'info');
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}/display`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Display power updated', 'success');
            refreshNodesOverview(false);
            if (nodeId === appState.activeNodeId) fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    }
}

export async function handleNodeQuickRotate(nodeId, monIdx) {
    const sel = document.getElementById(`nodeRot_${nodeId}_${monIdx}`);
    if (!sel) return;
    const rotation = sel.value;

    try {
        showToast(`Rotating Monitor ${monIdx} to ${rotation}...`, 'info');
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}/display`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'rotate',
                payload: {
                    monitor: String(monIdx),
                    rotation: rotation,
                    save_default: true,
                    restart_browser: true
                }
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || `Rotated Monitor ${monIdx}`, 'success');
            refreshNodesOverview(false);
        } else {
            showToast('Rotate error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Rotate error: ' + err.message, 'error');
    }
}

export async function handleNodeQuickPush(nodeId) {
    const contentSel = document.getElementById(`nodePushContent_${nodeId}`);
    const monSel = document.getElementById(`nodePushMonitor_${nodeId}`);
    if (!contentSel) return;

    const val = contentSel.value;
    const monitor = monSel ? monSel.value : 'both';
    const sites = (appState.mainWebsites && appState.mainWebsites.length > 0)
        ? appState.mainWebsites
        : appState.websites;

    let payload = { monitor };

    if (val === 'stream_slideshow') {
        payload.mode = 'slideshow';
        payload.slideshow_mode = appState.slideshowConfig.mode || 'random';
        payload.interval = appState.slideshowConfig.interval || 30;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = true;
    } else if (val === 'local_slideshow') {
        payload.mode = 'slideshow';
        payload.slideshow_mode = appState.slideshowConfig.mode || 'random';
        payload.interval = appState.slideshowConfig.interval || 30;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = false;
    } else if (val.startsWith('web:')) {
        const idx = parseInt(val.slice(4), 10);
        const site = sites[idx];
        const url = site ? (site.url || '') : '';
        payload.mode = 'website';
        if (monitor === '1') payload.url1 = url;
        else if (monitor === '2') payload.url2 = url;
        else {
            payload.url1 = url;
            payload.url2 = url;
        }
    } else if (val.startsWith('img:')) {
        const filename = val.slice(4);
        payload.mode = 'image';
        payload.image1 = filename;
        payload.image2 = filename;
        payload.fit = appState.slideshowConfig.fit || 'cover';
        payload.stream_from_main = true;
    }

    try {
        showToast(`Updating displays...`, 'info');
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}/display`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'display',
                payload: payload
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Displays updated!', 'success');
            refreshNodesOverview(false);
            if (nodeId === appState.activeNodeId) fetchLiveStatus();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error pushing display content: ' + err.message, 'error');
    }
}

export async function handleSyncNode(nodeId, includeImages = false) {
    try {
        showToast(includeImages ? 'Syncing websites, slideshow & images to remote Pi...' : 'Syncing websites & slideshow settings...', 'info');
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                websites: true,
                slideshow: true,
                images: includeImages
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'Sync completed!', 'success');
            refreshNodesOverview(false);
        } else {
            showToast('Sync error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Sync error: ' + err.message, 'error');
    }
}

export async function handleProbeExistingNode(nodeId) {
    try {
        showToast('Testing connection to Pi...', 'info');
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}/status`);
        const data = await res.json();
        if (data.success && data.node) {
            if (data.node.online) {
                showToast(`Connected to ${data.node.name}! (${data.node.monitor_count} displays, ${data.node.latency_ms}ms)`, 'success');
            } else {
                showToast(`${data.node.name} unreachable: ${data.node.error || 'Offline'}`, 'error');
            }
            refreshNodesOverview(false);
        } else {
            showToast('Error: ' + (data.error || 'Probe failed'), 'error');
        }
    } catch (err) {
        showToast('Probe error: ' + err.message, 'error');
    }
}

// -----------------------------------------------------------------------------
// Connect / Edit Pi Modal
// -----------------------------------------------------------------------------
export function openAddNodeModal() {
    const modal = document.getElementById('nodeModal');
    const title = document.getElementById('nodeModalTitle');
    const editId = document.getElementById('nodeEditId');
    const nameInput = document.getElementById('nodeNameInput');
    const urlInput = document.getElementById('nodeUrlInput');
    const roleInput = document.getElementById('nodeRoleInput');
    const sslCheck = document.getElementById('nodeVerifySslInput');
    const sslGroup = document.getElementById('nodeSslGroup');
    const testBtn = document.getElementById('testNodeConnBtn');
    const probeBox = document.getElementById('nodeProbeResult');

    if (title) title.textContent = 'Connect Another Raspberry Pi';
    if (editId) editId.value = '';
    if (nameInput) nameInput.value = '';
    if (urlInput) {
        urlInput.value = '';
        urlInput.placeholder = 'e.g., pi2.spear.ac or http://192.168.1.50:5000';
    }
    if (roleInput) roleInput.value = 'secondary';
    if (sslCheck) sslCheck.checked = true;
    if (sslGroup) sslGroup.style.display = 'flex';
    if (testBtn) testBtn.style.display = 'inline-flex';
    if (probeBox) {
        probeBox.style.display = 'none';
        probeBox.innerHTML = '';
    }
    if (modal) modal.style.display = 'flex';
}

export function openEditNodeModal(nodeId) {
    const modal = document.getElementById('nodeModal');
    const title = document.getElementById('nodeModalTitle');
    const editId = document.getElementById('nodeEditId');
    const nameInput = document.getElementById('nodeNameInput');
    const urlInput = document.getElementById('nodeUrlInput');
    const roleInput = document.getElementById('nodeRoleInput');
    const sslCheck = document.getElementById('nodeVerifySslInput');
    const sslGroup = document.getElementById('nodeSslGroup');
    const testBtn = document.getElementById('testNodeConnBtn');
    const probeBox = document.getElementById('nodeProbeResult');

    const node = nodeId === 'local'
        ? appState.localNode
        : (appState.allNodes.find(n => n.id === nodeId) || appState.nodesOverview.find(n => n.id === nodeId));
    if (!node) return;

    if (title) {
        title.textContent = nodeId === 'local'
            ? 'Configure This Pi (Public Host URL)'
            : `Edit Connected Pi: ${node.name}`;
    }
    if (editId) editId.value = nodeId;
    if (nameInput) nameInput.value = node.name || '';
    if (urlInput) urlInput.value = node.url || '';
    if (roleInput) roleInput.value = node.role || (nodeId === 'local' ? 'main' : 'secondary');
    if (sslCheck) sslCheck.checked = node.verify_ssl !== false;
    if (sslGroup) sslGroup.style.display = nodeId === 'local' ? 'none' : 'flex';
    if (testBtn) testBtn.style.display = nodeId === 'local' ? 'none' : 'inline-flex';
    if (probeBox) {
        probeBox.style.display = 'none';
        probeBox.innerHTML = '';
    }
    if (modal) modal.style.display = 'flex';
}

export function closeNodeModal() {
    const modal = document.getElementById('nodeModal');
    if (modal) modal.style.display = 'none';
}

export async function handleTestNodeConnection() {
    const urlInput = document.getElementById('nodeUrlInput');
    const sslCheck = document.getElementById('nodeVerifySslInput');
    const probeBox = document.getElementById('nodeProbeResult');
    const rawUrl = urlInput ? urlInput.value.trim() : '';

    if (!rawUrl) {
        showToast('Enter a hostname or URL to test (e.g., pi2.spear.ac)', 'error');
        return;
    }

    if (probeBox) {
        probeBox.style.display = 'block';
        probeBox.className = 'node-probe-box testing';
        probeBox.textContent = `Testing connection to ${rawUrl}...`;
    }

    try {
        const res = await fetch('/api/nodes/probe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: rawUrl,
                verify_ssl: sslCheck ? sslCheck.checked : true,
                auto_discover: true
            })
        });
        const data = await res.json();
        if (!data.success) {
            if (probeBox) {
                probeBox.className = 'node-probe-box error';
                probeBox.textContent = data.error || 'Connection test failed';
            }
            return;
        }

        const p = data.probe;
        if (p.online) {
            if (urlInput && p.resolved_url) {
                urlInput.value = p.resolved_url;
            }
            if (probeBox) {
                probeBox.className = 'node-probe-box success';
                probeBox.innerHTML = `
                    <strong>Connected to Pi Display Control!</strong><br>
                    URL: <code>${escapeHtml(p.resolved_url)}</code> &bull;
                    Displays: <strong>${p.monitor_count || 0}</strong> &bull;
                    Latency: <strong>${p.latency_ms}ms</strong>
                `;
            }
        } else {
            if (probeBox) {
                probeBox.className = 'node-probe-box error';
                probeBox.innerHTML = `
                    <strong>Unreachable:</strong> ${escapeHtml(p.error || 'No response')}<br>
                    <small>You can still save this Pi now and it will connect automatically once online.</small>
                `;
            }
        }
    } catch (err) {
        if (probeBox) {
            probeBox.className = 'node-probe-box error';
            probeBox.textContent = 'Test failed: ' + err.message;
        }
    }
}

export async function handleSaveNode(e) {
    e.preventDefault();
    const editId = document.getElementById('nodeEditId')?.value || '';
    const name = document.getElementById('nodeNameInput')?.value.trim() || '';
    const url = document.getElementById('nodeUrlInput')?.value.trim() || '';
    const role = document.getElementById('nodeRoleInput')?.value || 'secondary';
    const verifySsl = document.getElementById('nodeVerifySslInput')?.checked !== false;

    if (!name || !url) {
        showToast('Both Pi name and hostname/URL are required', 'error');
        return;
    }

    try {
        const isEdit = Boolean(editId);
        const endpoint = isEdit ? `/api/nodes/${encodeURIComponent(editId)}` : '/api/nodes';
        const method = isEdit ? 'PUT' : 'POST';

        const res = await fetch(endpoint, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                url,
                role,
                verify_ssl: verifySsl,
                auto_discover: !isEdit
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || `Saved ${name}!`, 'success');
            closeNodeModal();
            await loadNodesConfig();
            refreshNodesOverview(false);
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error saving Pi node: ' + err.message, 'error');
    }
}

export async function handleDeleteNode(nodeId) {
    const node = appState.allNodes.find(n => n.id === nodeId);
    const label = node ? `${node.name} (${formatHostShort(node.url)})` : nodeId;
    if (!confirm(`Disconnect ${label} from Pi Display Control?`)) return;

    try {
        const res = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(`Disconnected ${label}`, 'success');
            if (appState.activeNodeId === nodeId) {
                appState.activeNodeId = 'local';
                if (typeof window.refreshActiveNodeData === 'function') {
                    window.refreshActiveNodeData();
                }
            }
            await loadNodesConfig();
            refreshNodesOverview(false);
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error removing Pi node: ' + err.message, 'error');
    }
}

