/**
 * Application State & Shared Utilities
 */

// Global State
export const appState = {
    websites: [],
    images: [],
    schedules: [],
    slideshowConfig: {
        mode: 'random',
        interval: 30,
        transition: 'fade',
        fit: 'cover',
        selected_images: []
    }
};

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
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
