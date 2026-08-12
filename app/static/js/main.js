/**
 * SegmentIQ — Client Side Scripts
 * Handles Light/Dark Theme Switching and Real-time Catalog Filtering
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Light/Dark Theme Switcher Logic
    const themeToggleBtn = document.getElementById('themeToggle');
    const htmlElem = document.documentElement;

    // Load saved theme or system preference
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    htmlElem.setAttribute('data-theme', savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlElem.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlElem.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // 2. Real-time Product Catalog Search & Category Filter
    const searchInput = document.getElementById('productSearch');
    const categoryPills = document.querySelectorAll('.cat-pill');
    const productCards = document.querySelectorAll('.product-card');
    const visibleCountElem = document.getElementById('visibleCount');

    let activeCategory = 'all';
    let searchQuery = '';

    function filterProducts() {
        let count = 0;
        productCards.forEach(card => {
            const cat = card.getAttribute('data-category');
            const name = card.getAttribute('data-name') || '';
            const desc = card.getAttribute('data-desc') || '';

            const matchesCategory = (activeCategory === 'all' || cat === activeCategory);
            const matchesSearch = (!searchQuery || name.includes(searchQuery) || desc.includes(searchQuery) || cat.toLowerCase().includes(searchQuery));

            if (matchesCategory && matchesSearch) {
                card.style.display = 'flex';
                count++;
            } else {
                card.style.display = 'none';
            }
        });

        if (visibleCountElem) {
            visibleCountElem.textContent = count;
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.trim().toLowerCase();
            filterProducts();
        });
    }

    if (categoryPills) {
        categoryPills.forEach(pill => {
            pill.addEventListener('click', () => {
                categoryPills.forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                activeCategory = pill.getAttribute('data-category');
                filterProducts();
            });
        });
    }
});
