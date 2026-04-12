{% load i18n common_extras static %}
    const farmFormCategoryItemMap = JSON.parse(document.getElementById("farm-form-category-item-map")?.textContent || "{}");
    const manualGroup = document.getElementById("manual-name-group");
    const manualInput = document.getElementById("manual-name-input");
    const unitSelect = document.getElementById("unit-select");
    const unitHidden = document.getElementById("unit-hidden");
    const farmPriceInput = document.querySelector('#farm-product-form input[name="price"]');
    const farmZeroPriceSourceGroup = document.getElementById('farm-zero-price-source-group');
    const farmZeroPriceSourceSelect = document.getElementById('farm-zero-price-source');

    const weightUnitSystem = "{% unit_system request.user %}";
    const volumeUnitSystem = "{% volume_system request.user %}";
    const WEIGHT_UNITS = weightUnitSystem === "lb" ? ["kq", "qram"] : ["kq", "qram", "ton"];
    const VOLUME_UNITS = volumeUnitSystem === "gallon" ? ["litr"] : ["litr", "ml"];
    const ALL_UNITS = [...WEIGHT_UNITS, ...VOLUME_UNITS, "ədəd", "dəstə", "bağlama"];
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const LITERS_PER_GALLON = 3.785411784;
    const UNIT_LABELS = {
        kq: weightUnitSystem === "lb" ? "pound" : "kq",
        ton: "ton",
        qram: weightUnitSystem === "lb" ? "ounce" : "qram",
        litr: volumeUnitSystem === "gallon" ? "gallon" : "litr",
        ml: "millilitr",
        "ədəd": "ədəd",
        "dəstə": "dəstə",
        "bağlama": "bağlama",
    };

    function applyUnitOptions(allowed, defaultValue) {
        if (!unitSelect) return;
        unitSelect.innerHTML = "";
        allowed.forEach(value => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = UNIT_LABELS[value] || value;
            unitSelect.appendChild(option);
        });
        if (defaultValue && allowed.includes(defaultValue)) {
            unitSelect.value = defaultValue;
        } else if (allowed.length) {
            unitSelect.value = allowed[0];
        }
    }

    function resetUnitSelect(message) {
        if (!unitSelect) return;
        unitSelect.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = message;
        option.selected = true;
        unitSelect.appendChild(option);
        unitSelect.disabled = true;
        unitSelect.name = "unit_disabled";
        if (unitHidden) {
            unitHidden.name = "unit_disabled";
            unitHidden.value = "";
        }
    }

    function setUnitForItem(unitValue, isLocked, allowedUnits) {
        if (!unitSelect) return;
        if (allowedUnits && allowedUnits.length) {
            applyUnitOptions(allowedUnits, unitValue);
        } else if (unitValue) {
            unitSelect.value = unitValue;
        }
        unitSelect.disabled = isLocked;
        if (unitHidden) {
            if (isLocked) {
                unitSelect.name = "unit_disabled";
                unitHidden.name = "unit";
                unitHidden.value = unitSelect.value || unitValue || "";
            } else {
                unitSelect.name = "unit";
                unitHidden.name = "unit_disabled";
                unitHidden.value = "";
            }
        }
        if (!unitSelect.options.length && allowedUnits && allowedUnits.length) {
            applyUnitOptions(allowedUnits, unitValue);
        }
    }

    function handleItemSelection(option) {
        const itemName = option?.dataset?.name || "";
        const itemUnit = option?.dataset?.unit || "";
        const isOther = itemName === "Digər" || !itemUnit;
        let allowed = ALL_UNITS;
        let lockUnit = false;

        const isForage = ["yonca", "koronilla", "seradella"].includes(itemName.toLowerCase());
        if (isForage) {
            allowed = ["kq", "bağlama"];
        } else if (itemUnit === "kq") {
            allowed = [...WEIGHT_UNITS];
        } else if (itemUnit === "litr") {
            allowed = [...VOLUME_UNITS];
        } else if (itemUnit) {
            allowed = [itemUnit];
            lockUnit = true;
        }

        if (isOther) {
            manualGroup.style.display = "block";
            manualInput.required = true;
            if (!unitSelect.value) unitSelect.value = "kq";
            setUnitForItem(unitSelect.value, false, ALL_UNITS);
        } else {
            manualGroup.style.display = "none";
            manualInput.required = false;
            manualInput.value = "";
            setUnitForItem(itemUnit, lockUnit, allowed);
        }
    }

    function syncFarmZeroPriceSource() {
        if (!farmPriceInput || !farmZeroPriceSourceGroup || !farmZeroPriceSourceSelect) return;
        const raw = String(farmPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        farmZeroPriceSourceGroup.style.display = shouldShow ? "block" : "none";
        farmZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) farmZeroPriceSourceSelect.value = "";
    }

    function populateFarmFormItems(categoryId, selectedItemId = "") {
        const itemSelect = document.getElementById("item-select");
        if (!itemSelect) return;
        const items = farmFormCategoryItemMap[String(categoryId)] || [];
        itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Məhsul seçin" %}</option>';
        items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.id);
            option.textContent = item.name;
            option.dataset.name = item.name;
            option.dataset.unit = item.unit || "";
            if (String(item.id) === String(selectedItemId)) {
                option.selected = true;
            }
            itemSelect.appendChild(option);
        });
        itemSelect.disabled = false;
    }

    document.getElementById("category-select").addEventListener("change", function () {
        const categoryId = this.value;
        const categoryText = this.options[this.selectedIndex]?.text || "";
        const itemSelect = document.getElementById("item-select");
        const itemGroup = document.getElementById("item-field-group");

        if (categoryText.startsWith("Digər")) {
            itemGroup.style.display = "none";
            itemSelect.required = false;
            itemSelect.disabled = true;
            itemSelect.innerHTML = '<option value="" disabled selected>{% trans "Alt kateqoriya yoxdur" %}</option>';
            manualGroup.style.display = "block";
            manualInput.required = true;
            setUnitForItem("kq", false, ALL_UNITS);
            return;
        }

        itemGroup.style.display = "block";
        itemSelect.required = true;
        populateFarmFormItems(categoryId);
        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        if (selectedOption && selectedOption.value) {
            handleItemSelection(selectedOption);
        } else {
            manualGroup.style.display = "none";
            manualInput.required = false;
            resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
        }
    });

    document.getElementById("item-select").addEventListener("change", function () {
        const selectedOption = this.options[this.selectedIndex];
        handleItemSelection(selectedOption);
    });
    farmPriceInput?.addEventListener("input", syncFarmZeroPriceSource);
    farmPriceInput?.addEventListener("change", syncFarmZeroPriceSource);

    document.getElementById("farm-product-form")?.addEventListener("submit", function () {
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
    });

    (function initSelection() {
        const itemSelect = document.getElementById("item-select");
        const categorySelect = document.getElementById("category-select");
        const categoryText = categorySelect?.options[categorySelect.selectedIndex]?.text || "";
        if (categoryText.startsWith("Digər")) {
            const itemGroup = document.getElementById("item-field-group");
            itemGroup.style.display = "none";
            itemSelect.required = false;
            itemSelect.disabled = true;
            manualGroup.style.display = "block";
            manualInput.required = true;
            setUnitForItem("kq", false, ALL_UNITS);
            return;
        }
        if (itemSelect && itemSelect.value) {
            handleItemSelection(itemSelect.options[itemSelect.selectedIndex]);
        } else if (!manualInput.value) {
            resetUnitSelect('{% trans "Əvvəlcə məhsul seçin" %}');
        }
        syncFarmZeroPriceSource();
    })();
