{% load i18n common_extras static %}
    const toolFormCategoryItemMap = JSON.parse(document.getElementById("tool-form-category-item-map")?.textContent || "{}");
    const toolFormManualGroup = document.getElementById('manual-name-group');
    const toolFormManualInput = document.getElementById('manual-name-input');
    const toolPriceInput = document.querySelector('#tool-form input[name="price"]');
    const toolZeroPriceSourceGroup = document.getElementById('tool-zero-price-source-group');
    const toolZeroPriceSourceSelect = document.getElementById('tool-zero-price-source');

    function populateToolFormItems(categoryId, selectedItemId = "") {
        const itemSelect = document.getElementById('item-select');
        if (!itemSelect) return;
        const items = toolFormCategoryItemMap[String(categoryId)] || [];
        itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Alət seçin" %}</option>';
        items.forEach((item) => {
            const option = document.createElement('option');
            option.value = String(item.id);
            option.textContent = item.name;
            if (String(item.id) === String(selectedItemId)) {
                option.selected = true;
            }
            itemSelect.appendChild(option);
        });
        itemSelect.disabled = false;
    }

    document.getElementById('category-select').addEventListener('change', function () {
        const categoryId = this.value;
        const categoryText = this.options[this.selectedIndex].text;
        const itemSelect = document.getElementById('item-select');
        const itemGroup = document.getElementById('item-field-group');
        const manualGroup = document.getElementById('manual-name-group');
        const manualInput = document.getElementById('manual-name-input');

        if (categoryText === "Digər") {
            itemGroup.style.display = 'none';
            itemSelect.required = false;
            itemSelect.disabled = true;

            toolFormManualGroup.style.display = 'block';
            toolFormManualInput.required = true;
        } else {
            toolFormManualGroup.style.display = 'none';
            toolFormManualInput.required = false;
            toolFormManualInput.value = '';

            itemGroup.style.display = 'block';
            itemSelect.style.display = 'block';
            itemSelect.required = true;
            populateToolFormItems(categoryId);
            handleToolItemSelection();
        }
    });

    function handleToolItemSelection() {
        const selected = document.getElementById('item-select').options[document.getElementById('item-select').selectedIndex];
        const isOther = (selected?.textContent || "").trim() === "Digər";
        if (isOther) {
            toolFormManualGroup.style.display = 'block';
            toolFormManualInput.required = true;
        } else {
            toolFormManualGroup.style.display = 'none';
            toolFormManualInput.required = false;
            toolFormManualInput.value = '';
        }
    }

    function syncToolZeroPriceSource() {
        if (!toolPriceInput || !toolZeroPriceSourceGroup || !toolZeroPriceSourceSelect) return;
        const raw = String(toolPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        toolZeroPriceSourceGroup.style.display = shouldShow ? 'block' : 'none';
        toolZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) toolZeroPriceSourceSelect.value = '';
    }

    document.getElementById('item-select').addEventListener('change', handleToolItemSelection);
    toolPriceInput?.addEventListener('input', syncToolZeroPriceSource);
    toolPriceInput?.addEventListener('change', syncToolZeroPriceSource);

    (function initSelection() {
        const itemSelect = document.getElementById('item-select');
        if (itemSelect && itemSelect.value) {
            handleToolItemSelection();
        }
        syncToolZeroPriceSource();
    })();
