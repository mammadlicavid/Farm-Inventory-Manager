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

    const initialCategory = "{{ income.category|escapejs }}";
    const initialItem = "{{ income.item_name|escapejs }}";
    const initialUnit = "{{ income.unit|escapejs }}";

    const weightUnitSystem = "{% unit_system request.user %}";
    const volumeUnitSystem = "{% volume_system request.user %}";
    const weightUnits = weightUnitSystem === "lb" ? ["kq", "qram"] : ["kq", "qram", "ton"];
    const volumeUnits = volumeUnitSystem === "gallon" ? ["litr"] : ["litr", "ml"];
    const allUnits = [...weightUnits, ...volumeUnits, "ədəd", "dəstə", "bağlama"];
    const seedUnits = [...weightUnits];
    const animalUnits = ["ədəd"];
    const forageItems = new Set(["yonca", "koronilla", "seradella"]);
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const LITERS_PER_GALLON = 3.785411784;

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

    function setUnits(units, currentValue) {
        unitSelect.disabled = false;
        unitSelect.innerHTML = '';
        units.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit;
            option.textContent = displayUnitLabel(unit);
            if (currentValue && currentValue === unit) {
                option.selected = true;
            }
            unitSelect.appendChild(option);
        });
        if (!currentValue && units.length) {
            unitSelect.value = units[0];
        }
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
        const value = parseFloat(quantityInput.value || "");
        if (!Number.isFinite(value)) return;
        if (weightUnitSystem === "lb") {
            if (unitSelect.value === "kq") {
                quantityInput.value = String(Number((value * KG_PER_POUND).toFixed(4)));
            } else if (unitSelect.value === "qram") {
                quantityInput.value = String(Number((value * GRAMS_PER_OUNCE).toFixed(4)));
            }
        }
        if (volumeUnitSystem === "gallon" && unitSelect.value === "litr") {
            quantityInput.value = String(Number((parseFloat(quantityInput.value || "0") * LITERS_PER_GALLON).toFixed(4)));
        }
    }

    function updateManualState(showManual, manualValue) {
        if (showManual) {
            manualGroup.style.display = 'block';
            manualInput.required = true;
            if (manualValue) {
                manualInput.value = manualValue;
            }
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

    function populateItems(category, selectedItem) {
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
            updateManualState(true, selectedItem || initialItem);
            setUnits(allUnits, initialUnit);
            return;
        }

        itemGroup.style.display = 'block';
        itemSelect.required = true;
        itemSelect.disabled = false;
        itemSelect.innerHTML = '';

        let matched = false;
        data.items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            option.dataset.unit = item.unit || '';
            if (selectedItem && item.name === selectedItem) {
                option.selected = true;
                matched = true;
            }
            itemSelect.appendChild(option);
        });

        if (!matched) {
            const digerOption = Array.from(itemSelect.options).find(opt => opt.value === "Digər");
            if (digerOption) {
                digerOption.selected = true;
            }
            updateManualState(true, selectedItem || initialItem);
        } else {
            updateManualState(false);
        }

        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        const itemName = selectedOption ? selectedOption.value : '';
        const itemUnit = selectedOption ? selectedOption.dataset.unit : '';

        if (!itemName) {
            resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
        } else if (data.type === "seed") {
            setUnits(seedUnits, initialUnit);
        } else if (data.type === "animal") {
            setUnits(animalUnits, initialUnit);
        } else if (data.type === "farm") {
            if (itemName === "Digər") {
                setUnits(allUnits, initialUnit);
            } else {
                setUnits(resolveFarmUnits(itemName, itemUnit), initialUnit);
            }
        } else {
            setUnits(allUnits, initialUnit);
        }
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
            updateManualState(true, initialItem);
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
    }

    categorySelect.addEventListener('change', function () {
        populateItems(this.value, null);
        syncAnimalIdVisibility();
    });

    itemSelect.addEventListener('change', function () {
        handleItemChange();
        syncAnimalIdVisibility();
    });

    if (initialCategory) {
        populateItems(initialCategory, initialItem);
    }
    if (qtyInput) {
        qtyInput.addEventListener('input', syncAnimalIdVisibility);
        syncAnimalIdVisibility();
    }
    document.getElementById('income-form')?.addEventListener('submit', normalizeUnitForSubmit);
