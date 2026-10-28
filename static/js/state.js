/**
 * Application State, Node Routing Helpers & Shared Utilities
 */

// Global State
export const appState = {
    activeNodeId: 'local',
    localNode: {
        id: 'local',
        name: 'Main Pi',
        url: 'https://pi.spear.ac',
        role: 'main',
        is_local: true
    },
    remoteNodes: [],
    allNodes: [],
    nodesOverview: [],
    mainBaseUrl: 'https://pi.spear.ac',
    mainWebsites: [],
    mainImages: [],
    websites: [],
    images: [],
    schedules: [],
    monitors: [],
    monitorDefaults: { "1": "left", "2": "right" },
    availableRotations: [],
    slideshowConfig: {
        mode: 'random',
        interval: 30,
        transition: 'fade',
        fit: 'cover',
        selected_images: []
    }
};

export function isRemoteActive() {
    return appState.activeNodeId && appState.activeNodeId !== 'local';
}

export function getActiveNode() {
    if (!isRemoteActive()) {
        return appState.localNode;
    }
    return (
        appState.allNodes.find(n => n.id === appState.activeNodeId) ||
        appState.nodesOverview.find(n => n.id === appState.activeNodeId) ||
        appState.localNode
    );
}

/**
 * Build API URL routed to either local Pi or active connected remote Pi via backend proxy.
 */
export function apiUrl(path, nodeId = appState.activeNodeId) {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    if (!nodeId || nodeId === 'local') {
        return cleanPath;
    }
    return `/api/nodes/${encodeURIComponent(nodeId)}/proxy${cleanPath}`;
}

/**
 * Fetch wrapper automatically targeting the currently selected Pi node.
 */
export function apiFetch(path, options = {}, nodeId = appState.activeNodeId) {
    return fetch(apiUrl(path, nodeId), options);
}

/**
 * Extract compact display hostname from full URL (e.g. 'https://pi2.spear.ac' -> 'pi2.spear.ac')
 */
export function formatHostShort(url) {
    if (!url) return 'local';
    return String(url).replace(/^https?:\/\//i, '').replace(/\/+$/, '');
}

// Toast Notifications
let toastTimeout;
export function showToast(message, type = 'info') {
    const toast = document.getElementById('statusMessage');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast-notification ${type} show`;

    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// HTML Escaping Helper
export function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}
