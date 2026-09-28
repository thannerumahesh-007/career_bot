/* ======================================================
   CareerBot Global Client Application Utilities
   Theme Management, CSRF Headers, Saved Jobs, Lucide Icons
   ====================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Vector Icons
    initIcons();

    // 2. Theme Management (Midnight Aurora Dark Theme Default)
    const storedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(storedTheme);

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // 3. Flash Alert Auto-Dismiss
    const flashAlerts = document.querySelectorAll('.alert-dismissible');
    flashAlerts.forEach(alert => {
        setTimeout(() => {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {}
        }, 5000);
    });

    // 4. Initialize Data-Progress Bars
    initProgressBars();
});

function initProgressBars() {
    document.querySelectorAll('.progress-bar-custom[data-progress]').forEach(bar => {
        const val = bar.getAttribute('data-progress');
        if (val !== null && val !== '') {
            bar.style.width = val + '%';
        }
    });
}

function initIcons() {
    if (window.lucide) {
        lucide.createIcons();
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.setAttribute('data-lucide', 'sun');
        } else {
            themeIcon.setAttribute('data-lucide', 'moon');
        }
        initIcons();
    }
}

// Global CSRF Token Fetcher
function getCsrfToken() {
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    return metaToken ? metaToken.getAttribute('content') : '';
}

// Password Visibility Toggle
function togglePasswordVisibility(inputFieldId, toggleIconId) {
    const field = document.getElementById(inputFieldId);
    const icon = document.getElementById(toggleIconId);
    if (field && icon) {
        if (field.type === 'password') {
            field.type = 'text';
            icon.setAttribute('data-lucide', 'eye-off');
        } else {
            field.type = 'password';
            icon.setAttribute('data-lucide', 'eye');
        }
        initIcons();
    }
}

// Save Job Toggle Handler
async function toggleSaveJob(jobId, btnElement) {
    const isSaved = btnElement.getAttribute('data-saved') === 'true';
    const method = isSaved ? 'DELETE' : 'POST';

    try {
        const response = await fetch(`/api/jobs/save/${jobId}`, {
            method: method,
            headers: {
                'X-CSRF-Token': getCsrfToken()
            }
        });

        if (response.ok) {
            const data = await response.json();
            const newSaved = data.is_saved;
            btnElement.setAttribute('data-saved', newSaved ? 'true' : 'false');
            if (newSaved) {
                btnElement.className = 'btn btn-sm btn-primary-custom';
                btnElement.innerHTML = `<i data-lucide="bookmark-check" style="width: 14px; height: 14px;"></i> Saved`;
            } else {
                btnElement.className = 'btn btn-sm btn-outline-custom';
                btnElement.innerHTML = `<i data-lucide="bookmark" style="width: 14px; height: 14px;"></i> Save Job`;
            }
            initIcons();
        }
    } catch (err) {
        console.error('Error toggling saved job:', err);
    }
}
