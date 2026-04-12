{% load i18n common_extras static %}
    (function () {
        const categorySelect = document.getElementById('supplier-category-select');
        const manualGroup = document.getElementById('supplier-manual-category-group');
        const manualInput = document.getElementById('supplier-manual-category-input');
        if (!categorySelect || !manualGroup || !manualInput) return;

        function syncManualCategory() {
            const isOther = categorySelect.value === 'Digər';
            manualGroup.style.display = isOther ? 'block' : 'none';
            manualInput.required = isOther;
            if (!isOther) {
                manualInput.value = '';
            }
        }

        categorySelect.addEventListener('change', syncManualCategory);
        syncManualCategory();
    })();
