/**
 * Pi Display Control & Slideshow Studio
 * Frontend Application Orchestrator
 */

import { appState, showToast, escapeHtml } from './js/state.js';
import { fetchLiveStatus, handleBlankDisplay, handleWakeDisplay } from './js/display.js';
import { onMixerTypeChange, populateMixerOptions, getMonitorTargetObject, applyDualMixer, applySingleMonitor } from './js/mixer.js';
import { loadSlideshowConfig, renderSlideshowControls, updateSlideshowSummaryText, setSlideshowMode, updateSlideshowSetting, saveSlideshowConfigChanges, launchSlideshow } from './js/slideshow.js';
import { loadImages, renderImagesGrid, handleUploadImage, displaySingleImage, deleteImage, selectAllImages } from './js/images.js';
import { loadWebsites, renderWebsitesGrid, handleAddWebsite, launchWebsite, deleteWebsite, populateWebsiteOptions } from './js/websites.js';
import { loadSchedules, renderSchedulesList, openAddScheduleModal, closeScheduleModal, onScheduleActionChange, handleCreateSchedule, toggleSchedule, deleteSchedule } from './js/schedules.js';

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
    getMonitorTargetObject,
    applyDualMixer,
    applySingleMonitor,
    loadSlideshowConfig,
    renderSlideshowControls,
    updateSlideshowSummaryText,
    setSlideshowMode,
    updateSlideshowSetting,
    saveSlideshowConfigChanges,
    launchSlideshow,
    loadImages,
    renderImagesGrid,
    handleUploadImage,
    displaySingleImage,
    deleteImage,
    selectAllImages,
    loadWebsites,
    renderWebsitesGrid,
    handleAddWebsite,
    launchWebsite,
    deleteWebsite,
    populateWebsiteOptions,
    loadSchedules,
    renderSchedulesList,
    openAddScheduleModal,
    closeScheduleModal,
    onScheduleActionChange,
    handleCreateSchedule,
    toggleSchedule,
    deleteSchedule
});

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    setupEventListeners();
    refreshAllData();

    // Poll live status every 10 seconds
    setInterval(fetchLiveStatus, 10000);
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
        });
    });
}

// -----------------------------------------------------------------------------
// Global Event Listeners
// -----------------------------------------------------------------------------
function setupEventListeners() {
    // Forms
    const addWebsiteForm = document.getElementById('addWebsiteForm');
    if (addWebsiteForm) addWebsiteForm.addEventListener('submit', handleAddWebsite);

    const uploadImageForm = document.getElementById('uploadImageForm');
    if (uploadImageForm) uploadImageForm.addEventListener('submit', handleUploadImage);

    const createScheduleForm = document.getElementById('createScheduleForm');
    if (createScheduleForm) createScheduleForm.addEventListener('submit', handleCreateSchedule);

    // Screen power buttons
    const stopDisplayBtn = document.getElementById('stopDisplay');
    if (stopDisplayBtn) stopDisplayBtn.addEventListener('click', handleBlankDisplay);

    const wakeDisplayBtn = document.getElementById('wakeDisplay');
    if (wakeDisplayBtn) wakeDisplayBtn.addEventListener('click', handleWakeDisplay);
}

// -----------------------------------------------------------------------------
// Data Fetching & Sync
// -----------------------------------------------------------------------------
async function refreshAllData() {
    await Promise.all([
        loadWebsites(),
        loadImages(),
        loadSlideshowConfig(),
        loadSchedules(),
        fetchLiveStatus()
    ]);
    populateMixerOptions();
}
