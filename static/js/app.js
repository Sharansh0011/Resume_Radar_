/* =======================================
   Resume Radar — Shared JavaScript
   ======================================= */

// === DARK MODE TOGGLE ===
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('rr_theme', newTheme);
    
    // Update toggle button icon
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    
    // Sync with server (fire & forget)
    fetch('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dark_mode: newTheme === 'dark' })
    }).catch(() => {});
}

// Set toggle icon on load
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('.theme-toggle');
    if (btn) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        btn.textContent = isDark ? '☀️' : '🌙';
    }
});

// === MOBILE HAMBURGER MENU ===
function toggleMenu() {
    const menu = document.querySelector('.nav-links');
    const hamburger = document.querySelector('.hamburger');
    if (menu && hamburger) {
        menu.classList.toggle('active');
        hamburger.classList.toggle('active');
    }
}

// Close menu when clicking outside
document.addEventListener('click', (e) => {
    const menu = document.querySelector('.nav-links');
    const hamburger = document.querySelector('.hamburger');
    if (menu && hamburger && !menu.contains(e.target) && !hamburger.contains(e.target)) {
        menu.classList.remove('active');
        hamburger.classList.remove('active');
    }
});

// === TOAST NOTIFICATION SYSTEM ===
function showToast(message, type = 'success', duration = 3000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// === AUTO-DISMISS FLASH ALERTS ===
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// =======================================
//  PHASE 3 — UI POLISH UTILITIES
// =======================================

// === LOADING SPINNER ON FORM SUBMIT ===
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const btn = form.querySelector('button[type="submit"], .btn-submit');
            if (btn && !btn.classList.contains('btn-loading')) {
                btn.classList.add('btn-loading');
                btn.dataset.originalText = btn.textContent;
            }
        });
    });
});

// === PASSWORD SHOW/HIDE ===
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const btn = input.parentElement.querySelector('.password-toggle');
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
}

// === DRAG AND DROP UPLOAD ===
function initDragDrop(uploadBoxSelector, fileInputSelector) {
    const box = document.querySelector(uploadBoxSelector);
    const fileInput = document.querySelector(fileInputSelector);
    if (!box || !fileInput) return;

    ['dragenter', 'dragover'].forEach(evt => {
        box.addEventListener(evt, (e) => { e.preventDefault(); box.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(evt => {
        box.addEventListener(evt, (e) => { e.preventDefault(); box.classList.remove('drag-over'); });
    });
    box.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            showFileName(box, files[0].name);
        }
    });
    box.addEventListener('click', (e) => {
        if (e.target === box || e.target.classList.contains('upload-icon') || e.target.classList.contains('upload-text')) {
            fileInput.click();
        }
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) showFileName(box, fileInput.files[0].name);
    });
}

function showFileName(box, name) {
    let el = box.querySelector('.file-name');
    if (!el) {
        el = document.createElement('div');
        el.className = 'file-name';
        box.appendChild(el);
    }
    el.textContent = '📎 ' + name;
    el.style.display = 'inline-block';
}

// === SKILL TAGS INPUT ===
function initTagsInput(containerSelector, hiddenInputSelector) {
    const container = document.querySelector(containerSelector);
    const hidden = document.querySelector(hiddenInputSelector);
    if (!container || !hidden) return;

    const input = container.querySelector('.tag-input');
    const tags = [];

    // Load existing tags from hidden input
    if (hidden.value) {
        hidden.value.split(',').map(t => t.trim()).filter(Boolean).forEach(t => addTag(t));
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const val = input.value.trim().replace(/,/g, '');
            if (val && !tags.includes(val.toLowerCase())) addTag(val);
            input.value = '';
        }
        if (e.key === 'Backspace' && !input.value && tags.length) {
            removeTag(tags[tags.length - 1]);
        }
    });

    container.addEventListener('click', () => input.focus());

    function addTag(text) {
        tags.push(text.toLowerCase());
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = text + '<span class="remove-tag" data-tag="' + text.toLowerCase() + '">&times;</span>';
        tag.querySelector('.remove-tag').addEventListener('click', () => removeTag(text.toLowerCase()));
        container.insertBefore(tag, input);
        updateHidden();
    }

    function removeTag(text) {
        const idx = tags.indexOf(text);
        if (idx > -1) tags.splice(idx, 1);
        container.querySelectorAll('.tag').forEach(el => {
            if (el.querySelector('.remove-tag').dataset.tag === text) el.remove();
        });
        updateHidden();
    }

    function updateHidden() {
        hidden.value = tags.join(', ');
    }
}

// === TABLE SEARCH/FILTER ===
function initTableSearch(inputSelector, tableSelector) {
    const input = document.querySelector(inputSelector);
    const table = document.querySelector(tableSelector);
    if (!input || !table) return;

    input.addEventListener('input', () => {
        const query = input.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(query) ? '' : 'none';
        });
    });
}

// === WEIGHT VALIDATION ===
function initWeightValidation(inputSelectors, barSelector, statusSelector) {
    const inputs = document.querySelectorAll(inputSelectors);
    const bar = document.querySelector(barSelector);
    const status = document.querySelector(statusSelector);
    if (!inputs.length || !bar || !status) return;

    function update() {
        let total = 0;
        inputs.forEach(i => { total += parseInt(i.value) || 0; });
        const pct = Math.min(total, 100);
        bar.style.width = pct + '%';
        bar.className = 'weight-bar-fill ' + (total === 100 ? 'ok' : total > 100 ? 'danger' : 'warning');
        status.textContent = total + '/100%' + (total === 100 ? ' ✓' : total > 100 ? ' (too high!)' : ' (add ' + (100 - total) + ' more)');
        status.style.color = total === 100 ? '#28a745' : total > 100 ? '#dc3545' : '#ffc107';
    }

    inputs.forEach(i => i.addEventListener('input', update));
    update();
}
