{% load i18n common_extras static %}
    const seedFormCategoryItemMap = JSON.parse(document.getElementById("seed-form-category-item-map")?.textContent || "{}");
    const seedFormManualGroup = document.getElementById('manual-name-group');
    const seedFormManualInput = document.getElementById('manual-name-input');
    const seedUnitSelect = document.getElementById('seed-unit-select');
    const seedPriceInput = document.querySelector('#seed-form input[name="price"]');
    const seedZeroPriceSourceGroup = document.getElementById('seed-zero-price-source-group');
    const seedZeroPriceSourceSelect = document.getElementById('seed-zero-price-source');
    const weightUnitSystem = "{% unit_system request.user %}";
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const otherLabels = new Set(["digər", "other", "другое"]);

    function translateDynamicLabel(value) {
        const text = String(value || "");
        if (!text) return text;
        return window.runtimeI18n?.translateInlineValue?.(text) || text;
    }

    function isOtherLabel(value) {
        return otherLabels.has(String(value || "").trim().toLowerCase());
    }

    function populateSeedFormItems(categoryId, selectedItemId = "") {
        const itemSelect = document.getElementById('item-select');
        if (!itemSelect) return;
        const items = seedFormCategoryItemMap[String(categoryId)] || [];
        itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Toxum seçin" %}</option>';
        items.forEach((item) => {
            const option = document.createElement('option');
            option.value = String(item.id);
            option.textContent = translateDynamicLabel(item.name);
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

        if (isOtherLabel(categoryText)) {
            itemGroup.style.display = 'none';
            itemSelect.required = false;
            itemSelect.disabled = true;

            seedFormManualGroup.style.display = 'block';
            seedFormManualInput.required = true;
        } else {
            seedFormManualGroup.style.display = 'none';
            seedFormManualInput.required = false;
            seedFormManualInput.value = '';

            itemGroup.style.display = 'block';
            itemSelect.style.display = 'block';
            itemSelect.required = true;
            populateSeedFormItems(categoryId);
            handleSeedItemSelection();
        }
    });

    function handleSeedItemSelection() {
        const selected = document.getElementById('item-select').options[document.getElementById('item-select').selectedIndex];
        const isOther = isOtherLabel(selected?.textContent || "");
        if (isOther) {
            seedFormManualGroup.style.display = 'block';
            seedFormManualInput.required = true;
        } else {
            seedFormManualGroup.style.display = 'none';
            seedFormManualInput.required = false;
            seedFormManualInput.value = '';
        }
    }

    function syncSeedZeroPriceSource() {
        if (!seedPriceInput || !seedZeroPriceSourceGroup || !seedZeroPriceSourceSelect) return;
        const raw = String(seedPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        seedZeroPriceSourceGroup.style.display = shouldShow ? 'block' : 'none';
        seedZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) seedZeroPriceSourceSelect.value = '';
    }

    document.getElementById('item-select').addEventListener('change', handleSeedItemSelection);
    seedPriceInput?.addEventListener('input', syncSeedZeroPriceSource);
    seedPriceInput?.addEventListener('change', syncSeedZeroPriceSource);

    (function initSelection() {
        const itemSelect = document.getElementById('item-select');
        if (itemSelect && itemSelect.value) {
            handleSeedItemSelection();
        }
        syncSeedZeroPriceSource();
    })();

    document.getElementById('seed-form')?.addEventListener('submit', function () {
        const quantityInput = document.querySelector('input[name="quantity"]');
        if (!quantityInput || !seedUnitSelect) return;
        const value = parseFloat(quantityInput.value || "");
        if (!Number.isFinite(value) || weightUnitSystem !== "lb") return;
        if (seedUnitSelect.value === "kg") {
            quantityInput.value = String(Number((value * KG_PER_POUND).toFixed(4)));
        } else if (seedUnitSelect.value === "qram") {
            quantityInput.value = String(Number((value * GRAMS_PER_OUNCE).toFixed(4)));
        }
    });
