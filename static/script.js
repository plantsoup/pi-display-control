/**
 * Pi Display Control & Slideshow Studio
 * Frontend Application Orchestrator
 */

import { appState, showToast, escapeHtml } from './js/state.js';
import { fetchLiveStatus, handleBlankDisplay, handleWakeDisplay } from './js/display.js';
import {
    onMixerTypeChange,
    populateMixerOptions,
    updateMixerPreview,
    getMonitorTargetObject,
    applyDualMixer,
    applyDualMixerAllPis,
    applySingleMonitor
} from './js/mixer.js';
import {
    loadSlideshowConfig,
    renderSlideshowControls,
    updateSlideshowSummaryText,
    setSlideshowMode,
    updateSlideshowSetting,
    saveSlideshowConfigChanges,
    launchSlideshow,
    broadcastSlideshow
} from './js/slideshow.js';
import {
    loadImages,
    renderImagesGrid,
    handleUploadImage,
    displaySingleImage,
    broadcastSingleImage,
    deleteImage,
    selectAllImages
} from './js/images.js';
import {
    loadWebsites,
    renderWebsitesGrid,
    handleAddWebsite,
    launchWebsite,
    broadcastWebsite,
    deleteWebsite,
    populateWebsiteOptions
} from './js/websites.js';
import {
    loadSchedules,
    renderSchedulesList,
    openAddScheduleModal,
    closeScheduleModal,
    onScheduleActionChange,
    handleCreateSchedule,
    toggleSchedule,
    deleteSchedule
} from './js/schedules.js';
import {
    loadMonitorsData,
    handleApplyMonitorRotation,
    handleSetDefaultRotation,
    handleSaveAllCurrentAsDefault,
    handleResetToDefaults
} from './js/monitors.js';
import {
    loadNodesConfig,
    refreshNodesOverview,
    switchActiveNode,
    renderNodeSwitcherBar,
    renderNodesGrid,
    populateBroadcastOptions,
    onBroadcastTypeChange,
    handleBroadcastSubmit,
    handleFleetPower,
    handleNodePower,
    handleNodeQuickRotate,
    handleNodeQuickPush,
    handleSyncNode,
    handleProbeExistingNode,
    openAddNodeModal,
    openEditNodeModal,
    closeNodeModal,
    handleTestNodeConnection,
    handleSaveNode,
    handleDeleteNode
} from './js/nodes.js';

// Expose handlers to window for inline HTML onclick/onchange attributes
Object.assign(window, {
    appState,
    showToast,
    escapeHtml,
    fetchLiveStatus,
    handleBlankDisplay,
    handleWakeDisplay,
    onMixerTypeChange,
    populateMixerOptions,
    updateMixerPreview,
    getMonitorTargetObject,
    applyDualMixer,
    applyDualMixerAllPis,
    applySingleMonitor,
    loadSlideshowConfig,
    renderSlideshowControls,
    updateSlideshowSummaryText,
    setSlideshowMode,
    updateSlideshowSetting,
    saveSlideshowConfigChanges,
    launchSlideshow,
    broadcastSlideshow,
    loadImages,
    renderImagesGrid,
    handleUploadImage,
    displaySingleImage,
    broadcastSingleImage,
    deleteImage,
    selectAllImages,
    loadWebsites,
    renderWebsitesGrid,
    handleAddWebsite,
    launchWebsite,
    broadcastWebsite,
    deleteWebsite,
    populateWebsiteOptions,
    loadSchedules,
    renderSchedulesList,
    openAddScheduleModal,
    closeScheduleModal,
    onScheduleActionChange,
    handleCreateSchedule,
    toggleSchedule,
    deleteSchedule,
    loadMonitorsData,
    handleApplyMonitorRotation,
    handleSetDefaultRotation,
    handleSaveAllCurrentAsDefault,
    handleResetToDefaults,
    loadNodesConfig,
    refreshNodesOverview,
    switchActiveNode,
    renderNodeSwitcherBar,
    renderNodesGrid,
    populateBroadcastOptions,
    onBroadcastTypeChange,
    handleBroadcastSubmit,
    handleFleetPower,
    handleNodePower,
    handleNodeQuickRotate,
    handleNodeQuickPush,
    handleSyncNode,
    handleProbeExistingNode,
    openAddNodeModal,
    openEditNodeModal,
    closeNodeModal,
    handleTestNodeConnection,
    handleSaveNode,
    handleDeleteNode,
    refreshActiveNodeData
});

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    setupEventListeners();
    refreshAllData();

    // Poll active Pi live status every 10 seconds and connected Pis overview every 20 seconds
    setInterval(fetchLiveStatus, 10000);
    setInterval(() => refreshNodesOverview(false), 20000);
});

// -----------------------------------------------------------------------------
// Tab Navigation
// -----------------------------------------------------------------------------
function setupTabNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetContentId = tab.getAttribute('data-tab');
            const targetContent = document.getElementById(targetContentId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
            if (targetContentId === 'nodesTab') {
                refreshNodesOverview(false);
            }
        });
    });
}

// -----------------------------------------------------------------------------
// Global Event Listeners
// -----------------------------------------------------------------------------
function setupEventListeners() {
    const addWebsiteForm = document.getElementById('addWebsiteForm');
    if (addWebsiteForm) addWebsiteForm.addEventListener('submit', handleAddWebsite);

    const uploadImageForm = document.getElementById('uploadImageForm');
    if (uploadImageForm) uploadImageForm.addEventListener('submit', handleUploadImage);

    const createScheduleForm = document.getElementById('createScheduleForm');
    if (createScheduleForm) createScheduleForm.addEventListener('submit', handleCreateSchedule);

    const saveNodeForm = document.getElementById('saveNodeForm');
    if (saveNodeForm) saveNodeForm.addEventListener('submit', handleSaveNode);

    const stopDisplayBtn = document.getElementById('stopDisplay');
    if (stopDisplayBtn) stopDisplayBtn.addEventListener('click', handleBlankDisplay);

    const wakeDisplayBtn = document.getElementById('wakeDisplay');
    if (wakeDisplayBtn) wakeDisplayBtn.addEventListener('click', handleWakeDisplay);
}

// -----------------------------------------------------------------------------
// Data Fetching & Sync
// -----------------------------------------------------------------------------
async function refreshActiveNodeData() {
    await Promise.all([
        loadWebsites(),
        loadImages(),
        loadSlideshowConfig(),
        loadSchedules(),
        loadMonitorsData(),
        fetchLiveStatus()
    ]);
    populateMixerOptions();
    populateBroadcastOptions();
}

async function refreshAllData() {
    await loadNodesConfig();
    await refreshActiveNodeData();
    // Kick off non-blocking live probe across all connected Pis
    refreshNodesOverview(false);
}
