/**
 * SegmentIQ — Client-Side Scripts
 * - Light / Dark theme switching with localStorage persistence
 * - Real-time product catalog search & category filter
 * - Dynamic Two-Step Quick Checkout verification
 * - Auto-Dismiss Flash Alerts & Notifications after 4 seconds
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── 1. Theme Switcher ────────────────────────────────────────────────
    const themeToggleBtn = document.getElementById('themeToggle');
    const htmlElem = document.documentElement;

    // Restore saved preference or fall back to system preference
    const savedTheme = localStorage.getItem('theme')
        || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    htmlElem.setAttribute('data-theme', savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const current = htmlElem.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            htmlElem.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        });
    }

    // ── 2. Product Catalog — Search + Category Filter ────────────────────
    const searchInput   = document.getElementById('productSearch');
    const pills         = document.querySelectorAll('.pill[data-category]');
    const productCards  = document.querySelectorAll('.product-card');
    const visibleCount  = document.getElementById('visibleCount');
    const noResults     = document.getElementById('noResults');
    const productGrid   = document.getElementById('productGrid');

    let activeCategory = 'all';
    let searchQuery    = '';

    function filterProducts() {
        let visible = 0;

        productCards.forEach(card => {
            const cat  = card.getAttribute('data-category') || '';
            const name = card.getAttribute('data-name')     || '';
            const desc = card.getAttribute('data-desc')     || '';

            const matchesCat    = (activeCategory === 'all' || cat === activeCategory);
            const matchesSearch = (!searchQuery
                || name.includes(searchQuery)
                || desc.includes(searchQuery)
                || cat.toLowerCase().includes(searchQuery));

            if (matchesCat && matchesSearch) {
                card.style.display = 'flex';
                visible++;
            } else {
                card.style.display = 'none';
            }
        });

        if (visibleCount) visibleCount.textContent = visible;

        // Show "no results" message if nothing matches
        if (noResults) {
            noResults.style.display = (visible === 0 && productCards.length > 0) ? 'block' : 'none';
        }
        if (productGrid) {
            productGrid.style.display = (visible === 0) ? 'none' : 'grid';
        }
    }

    // Search input handler
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.trim().toLowerCase();
            filterProducts();
        });
    }

    // Category pill click handler
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            activeCategory = pill.getAttribute('data-category');
            filterProducts();
        });
    });

    // ── 3. Sort Direction Label Update ───────────────────────────────────
    const sortBySelect  = document.getElementById('sort-by-select');
    const sortDirSelect = document.getElementById('sort-dir-select');

    const textFields = ['name', 'status'];

    function updateSortDirLabels(field) {
        if (!sortDirSelect) return;
        const isText = textFields.includes(field);
        const isAge  = field === 'age';
        const opts   = sortDirSelect.options;

        if (isText) {
            opts[0].text = 'A → Z';
            opts[1].text = 'Z → A';
        } else if (isAge) {
            opts[0].text = 'Young → Old';
            opts[1].text = 'Old → Young';
        } else {
            opts[0].text = 'Low → High';
            opts[1].text = 'High → Low';
        }
    }

    if (sortBySelect) {
        sortBySelect.addEventListener('change', () => {
            updateSortDirLabels(sortBySelect.value);
        });
        updateSortDirLabels(sortBySelect.value);
    }

    // ── 4. Dynamic Two-Step Quick Checkout ──────────────────────────────
    const checkAccountBtn = document.getElementById('check-account-btn');
    const placeOrderBtn   = document.getElementById('place-order-btn');
    const phoneInput      = document.getElementById('checkout-phone');
    const nameInput       = document.getElementById('checkout-name');
    const ageInput        = document.getElementById('checkout-age');
    const genderInput     = document.getElementById('checkout-gender');
    const banner          = document.getElementById('customerCheckBanner');
    const extraFields     = document.getElementById('extraFields');
    const cityInput       = document.getElementById('checkout-city');
    const incomeInput     = document.getElementById('checkout-income');

    async function checkCustomerAccount() {
        if (!phoneInput) return;
        const phone = phoneInput.value.replace(/[^0-9]/g, '').trim();

        if (!phone || phone.length !== 10 || !/^[6-9]\d{9}$/.test(phone)) {
            if (banner) {
                banner.style.display = 'block';
                banner.innerHTML = `
                    <div class="checkout-status-alert alert-warning">
                        <span style="font-size:1.05rem; line-height:1; flex-shrink:0;">⚠️</span>
                        <div style="flex:1;">Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.</div>
                    </div>
                `;
            }
            phoneInput.focus();
            return;
        }

        try {
            const res = await fetch(`/customer/check-customer?phone=${encodeURIComponent(phone)}`);
            const data = await res.json();

            if (banner) {
                banner.style.display = 'block';
                if (data.exists) {
                    banner.innerHTML = `
                        <div class="checkout-status-alert alert-success">
                            <span style="font-size:1.1rem; line-height:1.2; font-weight:700; flex-shrink:0;">✓</span>
                            <div style="flex:1;">
                                <strong>Welcome back, ${data.name}!</strong> Account verified. Click confirm below to complete your order.
                            </div>
                        </div>
                    `;
                    if (extraFields) extraFields.style.display = 'none';
                    if (nameInput) { nameInput.value = data.name; nameInput.removeAttribute('required'); }
                    if (ageInput && data.age) { ageInput.value = data.age; ageInput.removeAttribute('required'); }
                    if (genderInput && data.gender) genderInput.value = data.gender;
                    if (cityInput && data.city) cityInput.value = data.city;
                    if (incomeInput && data.income) incomeInput.value = data.income;
                } else {
                    banner.innerHTML = `
                        <div class="checkout-status-alert alert-info">
                            <span style="font-size:1.05rem; line-height:1; flex-shrink:0;">ℹ️</span>
                            <div style="flex:1;">
                                <strong>New customer mobile number.</strong> Please fill out your account details below.
                            </div>
                        </div>
                    `;
                    if (extraFields) extraFields.style.display = 'block';
                    if (nameInput) nameInput.setAttribute('required', 'required');
                    if (ageInput) ageInput.setAttribute('required', 'required');
                }
            }

            if (checkAccountBtn) checkAccountBtn.style.display = 'none';
            if (placeOrderBtn) placeOrderBtn.style.display = 'block';

        } catch (err) {
            console.error("Customer check error:", err);
            if (extraFields) extraFields.style.display = 'block';
            if (checkAccountBtn) checkAccountBtn.style.display = 'none';
            if (placeOrderBtn) placeOrderBtn.style.display = 'block';
        }
    }

    if (checkAccountBtn) {
        checkAccountBtn.addEventListener('click', checkCustomerAccount);
    }

    // Reset check state if user modifies phone number
    if (phoneInput) {
        phoneInput.addEventListener('input', () => {
            if (banner && banner.style.display !== 'none') {
                banner.style.display = 'none';
                if (extraFields) extraFields.style.display = 'none';
                if (checkAccountBtn) checkAccountBtn.style.display = 'block';
                if (placeOrderBtn) placeOrderBtn.style.display = 'none';
            }
        });
    }

    // Intercept Enter / Shift+Enter / Ctrl+Enter keypresses & submission until verified
    const checkoutForm = document.getElementById('checkoutForm');
    if (checkoutForm) {
        checkoutForm.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const isVerified = placeOrderBtn && placeOrderBtn.style.display !== 'none';
                if (!isVerified) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (checkAccountBtn && checkAccountBtn.style.display !== 'none') {
                        checkAccountBtn.click();
                    }
                    return false;
                }
            }
        });

        checkoutForm.addEventListener('submit', (e) => {
            const isVerified = placeOrderBtn && placeOrderBtn.style.display !== 'none';
            if (!isVerified) {
                e.preventDefault();
                e.stopPropagation();
                if (checkAccountBtn && checkAccountBtn.style.display !== 'none') {
                    checkAccountBtn.click();
                }
                return false;
            }
        });
    }

    // ── 5. Auto-Dismiss Flash Alerts & Notifications after 4 seconds ─────
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease, margin 0.4s ease, padding 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(() => {
                if (alert.parentNode) alert.remove();
            }, 400);
        }, 4000);
    });

});
