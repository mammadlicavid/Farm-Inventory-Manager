{% load i18n common_extras static %}
    const weightDisplaySystem = "{{ weight_unit_system }}";
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const seedCategoryItemMap = JSON.parse(document.getElementById("seed-category-item-map")?.textContent || "{}");
    const seedFilterForm = document.getElementById("seed-filter-form");
    const seedFilterCategory = document.getElementById("seed-filter-category");
    const seedFilterItem = document.getElementById("seed-filter-item");
    const selectedSeedFilterItem = "{{ selected_item|default:''|escapejs }}";
    const seedFilterSearch = seedFilterForm?.querySelector('input[name="q"]');
    const seedFilterReset = document.getElementById("seed-filter-reset");
    const seedCards = Array.from(document.querySelectorAll("#seed-list .expense-item-card"));
    const seedListController = window.createProgressiveListController({ items: seedCards, batchSize: 100 });
    const seedListEmpty = document.getElementById("seed-list-empty");
    const seedCrudWrapper = document.querySelector(".crud-desktop-wrapper");
    const seedFormColumn = document.querySelector(".crud-form-column");
    const seedListColumn = document.querySelector(".crud-list-column");
    const seedFilterPlaceholder = document.createComment("seed-filter-placeholder");
    let seedFilterTimer = null;

    seedFilterForm?.parentNode?.insertBefore(seedFilterPlaceholder, seedFilterForm);

    seedFilterForm?.addEventListener("submit", (event) => event.preventDefault());

    function normalizeSeedText(value) {
        return String(value || "").trim().toLocaleLowerCase("az");
    }

    function applySeedFilters() {
        const category = seedFilterCategory?.value || "";
        const item = seedFilterItem?.value || "";
        const movement = seedFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = seedFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = seedFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        const term = normalizeSeedText(seedFilterSearch?.value || "");
        let visibleCount = 0;

        seedCards.forEach((card) => {
            const matchCategory = !category || (card.dataset.category || "") === category;
            const matchItem = !item || (card.dataset.item || "") === item;
            const matchMovement = !movement || (card.dataset.movement || "") === movement;
            const cardDate = card.dataset.date || "";
            const matchDateFrom = !dateFrom || (cardDate && cardDate >= dateFrom);
            const matchDateTo = !dateTo || (cardDate && cardDate <= dateTo);
            const matchSearch = !term || normalizeSeedText(card.dataset.search).includes(term);
            const show = matchCategory && matchItem && matchMovement && matchDateFrom && matchDateTo && matchSearch;
            card.dataset.filterMatch = show ? "1" : "0";
            if (show) visibleCount += 1;
        });

        seedListController.refresh(true);

        if (seedListEmpty) {
            seedListEmpty.style.display = visibleCount === 0 ? "block" : "none";
        }
    }

    function updateSeedFilterItems(categoryId, selectedItemId = "") {
        if (!seedFilterItem) return;
        seedFilterItem.innerHTML = '<option value="">{% trans "Bütün toxum növləri" %}</option>';
        if (!categoryId) return;
        const items = seedCategoryItemMap[String(categoryId)] || [];
        items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.id);
            option.textContent = item.name;
            if (String(item.id) === String(selectedItemId)) {
                option.selected = true;
            }
            seedFilterItem.appendChild(option);
        });
    }

    if (seedFilterCategory) {
        seedFilterCategory.addEventListener("change", () => {
            updateSeedFilterItems(seedFilterCategory.value);
            applySeedFilters();
        });
        if (seedFilterCategory.value) {
            updateSeedFilterItems(seedFilterCategory.value, selectedSeedFilterItem);
        }
    }

    seedFilterForm?.querySelectorAll('select[name="item"], select[name="movement"], input[name="date_from"], input[name="date_to"]').forEach((control) => {
        control.addEventListener("change", applySeedFilters);
    });

    seedFilterSearch?.addEventListener("input", () => {
        clearTimeout(seedFilterTimer);
        seedFilterTimer = setTimeout(applySeedFilters, 300);
    });

    seedFilterReset?.addEventListener("click", () => {
        if (seedFilterCategory) seedFilterCategory.value = "";
        if (seedFilterItem) {
            seedFilterItem.innerHTML = '<option value="">{% trans "Bütün toxum növləri" %}</option>';
            seedFilterItem.value = "";
        }
        const movementInput = seedFilterForm?.querySelector('select[name="movement"]');
        const dateFromInput = seedFilterForm?.querySelector('input[name="date_from"]');
        const dateToInput = seedFilterForm?.querySelector('input[name="date_to"]');
        if (movementInput) movementInput.value = "";
        if (dateFromInput) dateFromInput.value = "";
        if (dateToInput) dateToInput.value = "";
        if (seedFilterSearch) seedFilterSearch.value = "";
        applySeedFilters();
    });

    function repositionSeedFilter() {
        if (!seedFilterForm || !seedListColumn || !seedFilterPlaceholder) return;
        if (window.innerWidth < 1024) {
            seedCrudWrapper?.insertBefore(seedFilterForm, seedListColumn);
        } else if (seedFilterPlaceholder.parentNode) {
            seedFilterPlaceholder.parentNode.insertBefore(seedFilterForm, seedFilterPlaceholder.nextSibling);
        }
    }

    function hasActiveSeedFilters() {
        const movement = seedFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = seedFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = seedFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        return Boolean(
            (seedFilterCategory?.value || "") ||
            (seedFilterItem?.value || "") ||
            movement ||
            dateFrom ||
            dateTo ||
            normalizeSeedText(seedFilterSearch?.value || "")
        );
    }

    function initializeSeedList() {
        repositionSeedFilter();
        if (hasActiveSeedFilters()) {
            applySeedFilters();
            return;
        }
        if (seedCards.length > 120) {
            window.requestAnimationFrame(() => seedListController.refresh(true));
        }
    }

    window.addEventListener("resize", repositionSeedFilter);
    if ("requestAnimationFrame" in window) {
        window.requestAnimationFrame(initializeSeedList);
    } else {
        initializeSeedList();
    }

    const SEED_STATE_KEY = "seed_form_state_session_v1";
    const SEED_KEEP_KEY = "seed_form_keep_v1";
    const seedPriceInput = document.querySelector('#seed-form input[name="price"]');
    const seedZeroPriceSourceGroup = document.getElementById('seed-zero-price-source-group');
    const seedZeroPriceSourceSelect = document.getElementById('seed-zero-price-source');

    function saveSeedState(categoryId, itemId) {
        sessionStorage.setItem(SEED_STATE_KEY, JSON.stringify({ categoryId, itemId }));
    }

    function loadSeedState() {
        try {
            return JSON.parse(sessionStorage.getItem(SEED_STATE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function clearSeedState() {
        sessionStorage.removeItem(SEED_STATE_KEY);
        sessionStorage.removeItem(SEED_KEEP_KEY);
    }

    function syncSeedZeroPriceSource() {
        if (!seedPriceInput || !seedZeroPriceSourceGroup || !seedZeroPriceSourceSelect) return;
        const raw = String(seedPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        seedZeroPriceSourceGroup.style.display = shouldShow ? "block" : "none";
        seedZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) seedZeroPriceSourceSelect.value = "";
    }

    function resetSeedOtherFields() {
        document.querySelector('input[name="manual_name"]')?.setAttribute("value", "");
        const manualInput = document.getElementById("manual-name-input");
        if (manualInput) manualInput.value = "";
        const qty = document.querySelector('input[name="quantity"]');
        if (qty) qty.value = "";
        const price = document.querySelector('input[name="price"]');
        if (price) price.value = "";
        if (seedZeroPriceSourceSelect) seedZeroPriceSourceSelect.value = "";
        const info = document.querySelector('textarea[name="additional_info"]');
        if (info) info.value = "";
        const unit = document.querySelector('select[name="unit"]');
        if (unit) unit.value = "kg";
        syncSeedZeroPriceSource();
    }

    let pendingSeedItemId = null;

    function populateSeedItems(categoryId, selectedItemId = "") {
        const itemSelect = document.getElementById('item-select');
        if (!itemSelect) return;
        const items = seedCategoryItemMap[String(categoryId)] || [];
        itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Toxum seçin" %}</option>';
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
            saveSeedState(categoryId, "");
            resetSeedOtherFields();
            sessionStorage.removeItem(SEED_KEEP_KEY);

            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';

            itemGroup.style.display = 'block';
            itemSelect.style.display = 'block';
            itemSelect.required = true;
            populateSeedItems(categoryId, pendingSeedItemId);
            pendingSeedItemId = null;
            resetSeedOtherFields();
            saveSeedState(categoryId, itemSelect.value || "");
            handleSeedItemSelection();
        }
    });

    function handleSeedItemSelection() {
        const selected = document.getElementById('item-select').options[document.getElementById('item-select').selectedIndex];
        const isOther = (selected?.textContent || "").trim() === "Digər";
        const manualGroup = document.getElementById('manual-name-group');
        const manualInput = document.getElementById('manual-name-input');
        if (isOther) {
            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else if (manualGroup) {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';
        }
    }

    document.getElementById('item-select').addEventListener('change', function () {
        const categoryId = document.getElementById('category-select').value;
        saveSeedState(categoryId, this.value);
        handleSeedItemSelection();
    });
    seedPriceInput?.addEventListener('input', syncSeedZeroPriceSource);
    seedPriceInput?.addEventListener('change', syncSeedZeroPriceSource);

    const seedForm = document.getElementById('seed-form');
    if (seedForm) {
        seedForm.addEventListener('submit', () => {
            const quantityInput = document.querySelector('#seed-form input[name="quantity"]');
            const unitSelect = document.querySelector('#seed-form select[name="unit"]');
            if (quantityInput && unitSelect) {
                const value = parseFloat(quantityInput.value || "");
                if (Number.isFinite(value) && weightDisplaySystem === "lb") {
                    if (unitSelect.value === "kg") {
                        quantityInput.value = String(Number((value * KG_PER_POUND).toFixed(4)));
                    } else if (unitSelect.value === "qram") {
                        quantityInput.value = String(Number((value * GRAMS_PER_OUNCE).toFixed(4)));
                    }
                }
            }
            sessionStorage.setItem(SEED_KEEP_KEY, "1");
            const categoryId = document.getElementById('category-select').value;
            const itemId = document.getElementById('item-select')?.value || "";
            saveSeedState(categoryId, itemId);
        });
    }

    (function restoreSeedState() {
        const saved = loadSeedState();
        if (sessionStorage.getItem(SEED_KEEP_KEY) !== "1" || !saved.categoryId) {
            clearSeedState();
            return;
        }
        pendingSeedItemId = saved.itemId || null;
        const categorySelect = document.getElementById('category-select');
        categorySelect.value = saved.categoryId;
        categorySelect.dispatchEvent(new Event('change'));
        sessionStorage.removeItem(SEED_KEEP_KEY);
    })();

    window.addEventListener("pagehide", () => {
        if (sessionStorage.getItem(SEED_KEEP_KEY) !== "1") {
            clearSeedState();
        }
    });

    syncSeedZeroPriceSource();
