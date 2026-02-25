/**
 * MIBSP - Municipal Integrity & Bribe-Free Service Portal
 * Main JavaScript File
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    initTooltips();
    
    // Initialize all popovers
    initPopovers();
    
    // Auto-hide alerts after 5 seconds
    autoHideAlerts();
    
    // Confirm dangerous actions
    confirmDangerousActions();
    
    // Initialize character counters
    initCharCounters();
});

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(function(tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap popovers
 */
function initPopovers() {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    popoverTriggerList.forEach(function(popoverTriggerEl) {
        new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Auto-hide alert messages after 5 seconds
 */
function autoHideAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * Add confirmation dialog to dangerous actions
 */
function confirmDangerousActions() {
    const dangerButtons = document.querySelectorAll('[data-confirm]');
    dangerButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize character counters for textareas
 */
function initCharCounters() {
    const textareas = document.querySelectorAll('textarea[maxlength]');
    textareas.forEach(function(textarea) {
        const maxLength = textarea.getAttribute('maxlength');
        const counterId = textarea.id + '_counter';
        
        // Create counter element if it doesn't exist
        let counter = document.getElementById(counterId);
        if (!counter) {
            counter = document.createElement('small');
            counter.id = counterId;
            counter.className = 'text-muted';
            textarea.parentNode.appendChild(counter);
        }
        
        // Update counter
        function updateCounter() {
            const current = textarea.value.length;
            counter.textContent = current + ' / ' + maxLength + ' characters';
            
            if (current > maxLength * 0.9) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-warning');
            }
        }
        
        textarea.addEventListener('input', updateCounter);
        updateCounter(); // Initial update
    });
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @param {HTMLElement} button - Button element for feedback
 */
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success feedback
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-primary');
        
        setTimeout(function() {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-primary');
        }, 2000);
    }).catch(function(err) {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard. Please copy manually.');
    });
}

/**
 * Format date for display
 * @param {Date} date - Date object
 * @param {string} format - Format string
 * @returns {string} Formatted date
 */
function formatDate(date, format = 'DD MMM YYYY') {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, '0');
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    
    return format
        .replace('DD', day)
        .replace('MMM', month)
        .replace('YYYY', year);
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Show loading spinner on form submit
 * @param {HTMLFormElement} form - Form element
 */
function showFormLoading(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.dataset.originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    }
}

/**
 * Hide loading spinner on form
 * @param {HTMLFormElement} form - Form element
 */
function hideFormLoading(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.dataset.originalText) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = submitBtn.dataset.originalText;
    }
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} Is valid
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate tracking ID format
 * @param {string} trackingId - Tracking ID to validate
 * @returns {boolean} Is valid
 */
function isValidTrackingId(trackingId) {
    if (!trackingId || trackingId.length !== 11) {
        return false;
    }
    if (!trackingId.startsWith('MIB')) {
        return false;
    }
    const randomPart = trackingId.substring(3);
    return /^[A-Z0-9]+$/.test(randomPart);
}

/**
 * AJAX helper function
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch promise
 */
async function ajax(url, options = {}) {
    const defaultOptions = {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    // Add CSRF token for non-GET requests
    if (options.method && options.method !== 'GET') {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrfToken) {
            defaultOptions.headers['X-CSRFToken'] = csrfToken;
        }
    }
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('AJAX Error:', error);
        throw error;
    }
}

// Export functions for global access
window.MIBSP = {
    copyToClipboard,
    formatDate,
    debounce,
    showFormLoading,
    hideFormLoading,
    isValidEmail,
    isValidTrackingId,
    ajax
};
