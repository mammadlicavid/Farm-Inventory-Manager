{% load i18n common_extras static %}
    (function () {
        const form = document.getElementById('supplier-filter-form');
        const searchInput = document.getElementById('supplier-search-input');
        const categorySelect = document.getElementById('supplier-category-filter');
        const cards = Array.from(document.querySelectorAll('#suppliers-list .supplier-card:not(.supplier-empty-card)'));
        const serverEmpty = document.getElementById('suppliers-empty-server');
        const clientEmpty = document.getElementById('suppliers-empty-client');
        const resetButton = document.getElementById('supplier-filter-reset');

        if (!form || !searchInput || !categorySelect || cards.length === 0) return;

        form.addEventListener('submit', function (event) {
            event.preventDefault();
        });

        const normalize = (value) =>
            (value || '')
                .toLocaleLowerCase('az')
                .replace(/\s+/g, ' ')
                .trim();

        function applyFilter() {
            const query = normalize(searchInput.value);
            const category = categorySelect.value;
            let visibleCount = 0;

            cards.forEach((card) => {
                const searchText = normalize(card.dataset.search);
                const matchesSearch = !query || searchText.includes(query);
                const matchesCategory = !category || card.dataset.category === category;
                const visible = matchesSearch && matchesCategory;
                card.style.display = visible ? '' : 'none';
                if (visible) visibleCount += 1;
            });

            if (serverEmpty) {
                serverEmpty.style.display = visibleCount === 0 ? 'none' : '';
            }
            if (clientEmpty) {
                clientEmpty.style.display = visibleCount === 0 ? '' : 'none';
            }
        }

        searchInput.addEventListener('input', applyFilter);
        categorySelect.addEventListener('change', applyFilter);

        if (resetButton) {
            resetButton.addEventListener('click', function () {
                searchInput.value = '';
                categorySelect.value = '';
                applyFilter();
                searchInput.focus();
            });
        }

        applyFilter();
    })();
