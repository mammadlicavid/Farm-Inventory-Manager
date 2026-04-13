{% load i18n common_extras static %}
    (function () {
        const amountInput = document.getElementById('custom-amount-input');
        if (!amountInput) return;

        function applyCustomAmount(form) {
            const hidden = form.querySelector('input[name="custom_amount"]');
            if (!hidden) return;
            hidden.value = amountInput.value || "";
        }

        document.querySelectorAll('.quick-tap-form, .template-item-form').forEach(form => {
            form.addEventListener('submit', () => applyCustomAmount(form));
        });
    })();

    (function () {
        const searchInput = document.getElementById('template-search');
        const items = Array.from(document.querySelectorAll('.template-item-form'));
        if (!searchInput || items.length === 0) return;

        function normalize(value) {
            return (value || "").toLowerCase();
        }

        function matches(item, query) {
            if (!query) return true;
            const title = item.querySelector('.template-item-title')?.textContent || "";
            const tags = Array.from(item.querySelectorAll('.template-tag')).map(tag => tag.textContent).join(" ");
            return normalize(title + " " + tags).includes(query);
        }

        function applyFilter() {
            const query = normalize(searchInput.value);
            items.forEach(item => {
                item.style.display = matches(item, query) ? "" : "none";
            });
        }

        searchInput.addEventListener('input', applyFilter);
    })();
