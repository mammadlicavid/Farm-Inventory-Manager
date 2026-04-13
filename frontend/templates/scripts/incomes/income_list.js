{% load i18n common_extras static %}
    const incomeData = JSON.parse(
        document.getElementById('income-categories-data').textContent
    );

    const categorySelect = document.getElementById('category-select');
    const itemSelect = document.getElementById('item-select');
    const manualGroup = document.getElementById('manual-name-group');
    const manualInput = document.getElementById('manual-name-input');
    const unitSelect = document.getElementById('unit-select');
    const genderGroup = document.getElementById('gender-group');
    const genderSelect = document.getElementById('gender-select');
    const itemGroup = document.getElementById('item-field-group');
    const animalIdGroup = document.getElementById('animal-id-group');
    const animalIdInput = document.getElementById('animal-id-input');
    const qtyInput = document.querySelector('input[name="quantity"]');
    const incomeFilterForm = document.getElementById('income-filter-form');
    const incomeFilterCategory = document.getElementById('income-filter-category');
    const incomeFilterItem = document.getElementById('income-filter-item');
    const incomeFilterSearch = incomeFilterForm?.querySelector('input[name="q"]');
    const incomeFilterReset = document.getElementById('income-filter-reset');
    const incomeCards = Array.from(document.querySelectorAll('#income-list .expense-item-card'));
    const incomeListController = window.createProgressiveListController({ items: incomeCards, batchSize: 100 });
    const incomeListEmpty = document.getElementById('income-list-empty');
    const incomeFilterEmpty = document.getElementById('income-filter-empty');
    const incomeCrudWrapper = document.querySelector('.crud-desktop-wrapper');
    const incomeListColumn = document.querySelector('.crud-list-column');
    const incomeFilterPlaceholder = document.createComment('income-filter-placeholder');
    let incomeFilterTimer = null;

    const weightUnitSystem = "{% unit_system request.user %}";
    const volumeUnitSystem = "{% volume_system request.user %}";
    const weightUnits = weightUnitSystem === "lb" ? ["kq", "qram"] : ["kq", "qram", "ton"];
    const volumeUnits = volumeUnitSystem === "gallon" ? ["litr"] : ["litr", "ml"];
    const allUnits = [...weightUnits, ...volumeUnits, "ədəd", "dəstə", "bağlama"];
    const seedUnits = [...weightUnits];
    const animalUnits = ["ədəd"];
    const forageItems = new Set(["yonca", "koronilla", "seradella"]);
    const INCOME_STATE_KEY = "income_form_state_session_v1";
    const INCOME_KEEP_KEY = "income_form_keep_v1";
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const LITERS_PER_GALLON = 3.785411784;

    incomeFilterForm?.parentNode?.insertBefore(incomeFilterPlaceholder, incomeFilterForm);
    incomeFilterForm?.addEventListener('submit', (event) => event.preventDefault());

    function saveIncomeState(category, itemName) {
        sessionStorage.setItem(INCOME_STATE_KEY, JSON.stringify({ category, itemName }));
    }

    function loadIncomeState() {
        try {
            return JSON.parse(sessionStorage.getItem(INCOME_STATE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function clearIncomeState() {
        sessionStorage.removeItem(INCOME_STATE_KEY);
        sessionStorage.removeItem(INCOME_KEEP_KEY);
    }

    function displayUnitLabel(unit) {
        if (weightUnitSystem === "lb") {
            if (unit === "kg" || unit === "kq") return "pound";
            if (unit === "qram") return "ounce";
        }
        if (volumeUnitSystem === "gallon") {
            if (unit === "litr") return "gallon";
        }
        return unit === "kg" ? "kq" : (unit === "ml" ? "millilitr" : unit);
    }

    function setUnits(units) {
        unitSelect.disabled = false;
        unitSelect.innerHTML = '';
        units.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit;
            option.textContent = displayUnitLabel(unit);
            unitSelect.appendChild(option);
        });
    }

    function resetUnitSelect(message) {
        unitSelect.disabled = true;
        unitSelect.innerHTML = '';
        const option = document.createElement('option');
        option.value = '';
        option.textContent = message;
        option.selected = true;
        unitSelect.appendChild(option);
    }

    function resolveFarmUnits(itemName, itemUnit) {
        if (!itemName) {
            return [];
        }
        const key = itemName.trim().toLowerCase();
        if (forageItems.has(key)) {
            return ["kq", "bağlama"];
        }
        if (!itemUnit) {
            return [];
        }
        if (itemUnit === "kq") {
            return [...weightUnits];
        }
        if (itemUnit === "litr") {
            return [...volumeUnits];
        }
        return [itemUnit];
    }

    function normalizeUnitForSubmit() {
        const quantityInput = document.querySelector('input[name="quantity"]');
        if (!quantityInput || !unitSelect || unitSelect.disabled) return;
        const value = parseFloat(quantityInput.value || '');
        if (!Number.isFinite(value)) return;
        if (weightUnitSystem === "lb") {
            if (unitSelect.value === "kq") {
                quantityInput.value = String(Number((value * KG_PER_POUND).toFixed(4)));
            } else if (unitSelect.value === "qram") {
                quantityInput.value = String(Number((value * GRAMS_PER_OUNCE).toFixed(4)));
            }
        }
        if (volumeUnitSystem === "gallon" && unitSelect.value === "litr") {
            quantityInput.value = String(Number((parseFloat(quantityInput.value || '0') * LITERS_PER_GALLON).toFixed(4)));
        }
    }

    function updateManualState(showManual) {
        if (showManual) {
            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';
        }
    }

    function updateGenderState(type) {
        if (type === "animal") {
            genderGroup.style.display = 'block';
            genderSelect.required = true;
        } else {
            genderGroup.style.display = 'none';
            genderSelect.required = false;
            genderSelect.value = '';
        }
        syncAnimalIdVisibility();
    }

    function syncAnimalIdVisibility() {
        if (!animalIdGroup || !qtyInput) return;
        const category = categorySelect.value;
        const data = incomeData[category];
        const isAnimal = data && data.type === "animal";
        const qtyVal = parseFloat(qtyInput.value || "0");
        if (isAnimal && Math.abs(qtyVal) === 1) {
            animalIdGroup.style.display = 'block';
        } else {
            animalIdGroup.style.display = 'none';
            if (animalIdInput) animalIdInput.value = '';
        }
    }

    function populateItems(category) {
        const data = incomeData[category];
        if (!data) {
            itemSelect.disabled = true;
            itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Əvvəlcə kateqoriya seçin" %}</option>';
            updateManualState(false);
            updateGenderState('');
            resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
            return;
        }

        updateGenderState(data.type);

        if (category === "Digər") {
            itemGroup.style.display = 'none';
            itemSelect.required = false;
            itemSelect.disabled = true;
            updateManualState(true);
            setUnits(allUnits);
            return;
        }

        itemGroup.style.display = 'block';
        itemSelect.required = true;
        itemSelect.disabled = false;
        itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Alt məhsul seçin" %}</option>';

        data.items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            option.dataset.unit = item.unit || '';
            itemSelect.appendChild(option);
        });

        updateManualState(false);
        resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
    }

    function populateIncomeFilterItems(category, selectedItem = "") {
        if (!incomeFilterItem) return;
        incomeFilterItem.innerHTML = '<option value="">{% trans "Bütün məhsullar" %}</option>';
        const data = incomeData[category];
        if (!data) return;
        data.items.forEach((item) => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            if (item.name === selectedItem) option.selected = true;
            incomeFilterItem.appendChild(option);
        });
    }

    function normalizeIncomeFilterText(value) {
        return String(value || '').trim().toLocaleLowerCase('az');
    }

    function applyIncomeFilters() {
        const category = incomeFilterCategory?.value || '';
        const item = incomeFilterItem?.value || '';
        const dateFrom = incomeFilterForm?.querySelector('input[name="date_from"]')?.value || '';
        const dateTo = incomeFilterForm?.querySelector('input[name="date_to"]')?.value || '';
        const term = normalizeIncomeFilterText(incomeFilterSearch?.value || '');
        let visibleCount = 0;

        incomeCards.forEach((card) => {
            const matchCategory = !category || (card.dataset.category || '') === category;
            const matchItem = !item || (card.dataset.item || '') === item;
            const cardDate = card.dataset.date || '';
            const matchDateFrom = !dateFrom || (cardDate && cardDate >= dateFrom);
            const matchDateTo = !dateTo || (cardDate && cardDate <= dateTo);
            const matchSearch = !term || normalizeIncomeFilterText(card.dataset.search).includes(term);
            const show = matchCategory && matchItem && matchDateFrom && matchDateTo && matchSearch;
            card.dataset.filterMatch = show ? '1' : '0';
            if (show) visibleCount += 1;
        });

        incomeListController.refresh(true);

        if (incomeListEmpty) incomeListEmpty.style.display = 'none';
        if (incomeFilterEmpty) incomeFilterEmpty.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    function handleItemChange() {
        const category = categorySelect.value;
        const data = incomeData[category];
        if (!data) return;

        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        const itemName = selectedOption ? selectedOption.value : '';
        const itemUnit = selectedOption ? selectedOption.dataset.unit : '';

        if (!itemName) {
            updateManualState(false);
            resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
            return;
        }

        if (itemName === "Digər") {
            updateManualState(true);
        } else {
            updateManualState(false);
        }

        if (data.type === "seed") {
            setUnits(seedUnits);
        } else if (data.type === "animal") {
            setUnits(animalUnits);
        } else if (data.type === "farm") {
            if (itemName === "Digər") {
                setUnits(allUnits);
            } else {
                setUnits(resolveFarmUnits(itemName, itemUnit));
            }
        } else {
            setUnits(allUnits);
        }

        saveIncomeState(category, itemName);
    }

    categorySelect.addEventListener('change', function () {
        populateItems(this.value);
        saveIncomeState(this.value, "");
        syncAnimalIdVisibility();
    });

    itemSelect.addEventListener('change', function () {
        handleItemChange();
        syncAnimalIdVisibility();
    });

    incomeFilterCategory?.addEventListener('change', function () {
        populateIncomeFilterItems(this.value);
        applyIncomeFilters();
    });

    incomeFilterForm?.querySelectorAll('select[id="income-filter-item"], input[name="date_from"], input[name="date_to"]').forEach((control) => {
        control.addEventListener('change', applyIncomeFilters);
    });

    incomeFilterSearch?.addEventListener('input', () => {
        clearTimeout(incomeFilterTimer);
        incomeFilterTimer = setTimeout(applyIncomeFilters, 300);
    });

    incomeFilterReset?.addEventListener('click', () => {
        if (incomeFilterCategory) incomeFilterCategory.value = '';
        if (incomeFilterItem) {
            incomeFilterItem.innerHTML = '<option value="">{% trans "Bütün məhsullar" %}</option>';
            incomeFilterItem.value = '';
        }
        const dateFromInput = incomeFilterForm?.querySelector('input[name="date_from"]');
        const dateToInput = incomeFilterForm?.querySelector('input[name="date_to"]');
        if (dateFromInput) dateFromInput.value = '';
        if (dateToInput) dateToInput.value = '';
        if (incomeFilterSearch) incomeFilterSearch.value = '';
        applyIncomeFilters();
    });

    function repositionIncomeFilter() {
        if (!incomeFilterForm || !incomeListColumn || !incomeFilterPlaceholder) return;
        if (window.innerWidth < 1024) {
            incomeCrudWrapper?.insertBefore(incomeFilterForm, incomeListColumn);
        } else if (incomeFilterPlaceholder.parentNode) {
            incomeFilterPlaceholder.parentNode.insertBefore(incomeFilterForm, incomeFilterPlaceholder.nextSibling);
        }
    }

    const savedState = loadIncomeState();
    if (savedState.category) {
        categorySelect.value = savedState.category;
        populateItems(savedState.category);
        if (savedState.itemName) {
            itemSelect.value = savedState.itemName;
            handleItemChange();
        }
    }
    if (qtyInput) {
        qtyInput.addEventListener('input', syncAnimalIdVisibility);
        syncAnimalIdVisibility();
    }

    const form = document.getElementById('income-form');
    if (form) {
        form.addEventListener('submit', () => {
            normalizeUnitForSubmit();
            sessionStorage.setItem(INCOME_KEEP_KEY, '1');
        });
    }

    function maybeClearState() {
        const keep = sessionStorage.getItem(INCOME_KEEP_KEY);
        if (keep === '1') {
            sessionStorage.removeItem(INCOME_KEEP_KEY);
            return;
        }
        clearIncomeState();
    }

    window.addEventListener('pagehide', maybeClearState);
    window.addEventListener('beforeunload', maybeClearState);
    window.addEventListener('resize', repositionIncomeFilter);
    repositionIncomeFilter();
    applyIncomeFilters();
