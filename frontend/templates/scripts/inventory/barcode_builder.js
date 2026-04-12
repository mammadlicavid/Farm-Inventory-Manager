{% load i18n common_extras static %}
document.addEventListener("DOMContentLoaded", function () {
    const expenseData = JSON.parse(document.getElementById("inventory-expense-data").textContent);
    const animalData = JSON.parse(document.getElementById("inventory-animal-data").textContent);
    const seedData = JSON.parse(document.getElementById("inventory-seed-data").textContent);
    const toolData = JSON.parse(document.getElementById("inventory-tool-data").textContent);
    const farmData = JSON.parse(document.getElementById("inventory-farm-data").textContent);
    const incomeCategories = JSON.parse(document.getElementById("inventory-income-categories").textContent);
    const incomeData = JSON.parse(document.getElementById("inventory-income-data").textContent);

    const formTypeSelect = document.getElementById("builder-form-type");
    const urlParams = new URLSearchParams(window.location.search);
    const addPageMode = ["income", "expense"].includes(urlParams.get("form")) ? urlParams.get("form") : "stock";
    const initialForm = "{{ initial_form|escapejs }}" || urlParams.get("form") || "";
    const formShell = document.getElementById("builder-form-shell");
    const activeTitle = document.getElementById("builder-active-form-title");
    const previewSection = document.getElementById("barcode-preview");
    const previewTitle = document.getElementById("barcode-preview-title");
    const previewText = document.getElementById("barcode-preview-text");
    const barcodeSvg = document.getElementById("barcode-svg");
    const barcodeCodeText = document.getElementById("barcode-code-text");
    const copyBtn = document.getElementById("barcode-copy-btn");
    const downloadBtn = document.getElementById("barcode-download-btn");
    const weightUnitSystem = "{% unit_system request.user %}";
    const volumeUnitSystem = "{% volume_system request.user %}";
    const weightUnits = weightUnitSystem === "lb" ? ["kq", "qram"] : ["kq", "qram", "ton"];
    const volumeUnits = volumeUnitSystem === "gallon" ? ["litr"] : ["litr", "ml"];
    const allUnits = [...weightUnits, ...volumeUnits, "ədəd", "dəstə", "bağlama"];
    let barcodeDownloadName = "barcode";

    const panelTitles = { expense: "Xərc formu", income: "Gəlir formu", animal: "Heyvan formu", seed: "Toxum formu", tool: "Alət formu", farm: "Təsərrüfat formu" };

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    function slugify(value) {
        return (value || "barcode").toString().trim().toLowerCase().replace(/[^a-z0-9əöğıçşü\s-]/gi, "").replace(/\s+/g, "-");
    }

    function fillOptions(select, rows, placeholder, mapFn) {
        select.innerHTML = "";
        const first = document.createElement("option");
        first.value = "";
        first.textContent = placeholder;
        select.appendChild(first);
        rows.forEach((row) => {
            const option = document.createElement("option");
            const mapped = mapFn(row);
            option.value = mapped.value;
            option.textContent = mapped.label;
            if (mapped.dataset) Object.entries(mapped.dataset).forEach(([key, val]) => { option.dataset[key] = val; });
            select.appendChild(option);
        });
    }

    function syncRequiredStar(control) {
        const group = control ? control.closest(".input-group") : null;
        const label = group ? group.querySelector("label") : null;
        if (!label) return;
        const existing = label.querySelector(".required-star");
        if (control.required) {
            if (!existing) {
                const star = document.createElement("span");
                star.className = "required-star";
                star.textContent = "*";
                label.appendChild(star);
            }
            return;
        }
        if (existing) existing.remove();
    }

    function setControlRequired(control, isRequired) {
        if (!control) return;
        control.required = Boolean(isRequired);
        syncRequiredStar(control);
    }

    function syncAllRequiredStars() {
        document.querySelectorAll(".input-group input, .input-group select, .input-group textarea").forEach(syncRequiredStar);
    }

    function syncAnimalIdentificationState() {
        const quantityInput = document.getElementById("animal-quantity");
        const idInput = document.getElementById("animal-id");
        const parsedQuantity = parseInt(quantityInput.value || "1", 10);
        if (Math.abs(parsedQuantity) !== 1) {
            idInput.value = "";
            idInput.disabled = true;
            idInput.placeholder = "Miqdar ±1 olmadıqda ID yazılmır";
            return;
        }
        idInput.disabled = false;
        idInput.placeholder = "Məsələn: AZ12345";
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

    function setIncomeUnits(units, preferred) {
        const unitSelect = document.getElementById("income-unit");
        fillOptions(unitSelect, units, "Vahid seçin", (value) => ({ value, label: displayUnitLabel(value) }));
        unitSelect.value = preferred && units.includes(preferred) ? preferred : (units[0] || "");
    }

    function setUnitSelectOptions(selectId, units, preferred) {
        const unitSelect = document.getElementById(selectId);
        if (!unitSelect) return;
        fillOptions(unitSelect, units, "Vahid seçin", (value) => ({ value, label: displayUnitLabel(value) }));
        unitSelect.value = preferred && units.includes(preferred) ? preferred : (units[0] || "");
    }

    function updateExpenseSubcategories(selectedSubcategoryId) {
        const categorySelect = document.getElementById("expense-category");
        const subcategorySelect = document.getElementById("expense-subcategory");
        const manualWrap = document.getElementById("expense-manual-wrap");
        const manualInput = document.getElementById("expense-manual-name");
        const selectedCategory = expenseData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        if (selectedCategory.name.includes("Digər")) {
            manualWrap.hidden = false;
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            subcategorySelect.value = "";
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, true);
            return;
        }
        manualWrap.hidden = true;
        fillOptions(subcategorySelect, selectedCategory.subcategories || [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedSubcategoryId) subcategorySelect.value = String(selectedSubcategoryId);
        setControlRequired(subcategorySelect, true);
        setControlRequired(manualInput, false);
    }

    function updateAnimalSubcategories(selectedSubcategoryId) {
        const categorySelect = document.getElementById("animal-category");
        const subcategorySelect = document.getElementById("animal-subcategory");
        const manualWrap = document.getElementById("animal-manual-wrap");
        const manualInput = document.getElementById("animal-manual-name");
        const selectedCategory = animalData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        if (selectedCategory.name.includes("Digər")) {
            manualWrap.hidden = false;
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            subcategorySelect.value = "";
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, true);
            return;
        }
        manualWrap.hidden = true;
        fillOptions(subcategorySelect, selectedCategory.subcategories || [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedSubcategoryId) subcategorySelect.value = String(selectedSubcategoryId);
        setControlRequired(subcategorySelect, true);
        setControlRequired(manualInput, false);
    }

    function updateSeedItems(selectedItemId) {
        const categorySelect = document.getElementById("seed-category");
        const itemSelect = document.getElementById("seed-item");
        const manualWrap = document.getElementById("seed-manual-wrap");
        const manualInput = document.getElementById("seed-manual-name");
        const selectedCategory = seedData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Toxum seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Toxum seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const isOther = selectedCategory.name.includes("Digər") || itemSelect.options[itemSelect.selectedIndex]?.text === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        setUnitSelectOptions("seed-unit", weightUnits, document.getElementById("seed-unit")?.value || weightUnits[0]);
    }

    function updateToolItems(selectedItemId) {
        const categorySelect = document.getElementById("tool-category");
        const itemSelect = document.getElementById("tool-item");
        const manualWrap = document.getElementById("tool-manual-wrap");
        const manualInput = document.getElementById("tool-manual-name");
        const selectedCategory = toolData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Alət seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Alət seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const isOther = selectedCategory.name.includes("Digər") || itemSelect.options[itemSelect.selectedIndex]?.text === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
    }

    function updateFarmItems(selectedItemId) {
        const categorySelect = document.getElementById("farm-category");
        const itemSelect = document.getElementById("farm-item");
        const unitSelect = document.getElementById("farm-unit");
        const manualWrap = document.getElementById("farm-manual-wrap");
        const manualInput = document.getElementById("farm-manual-name");
        const selectedCategory = farmData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Məhsul seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Məhsul seçin", (row) => ({ value: row.id, label: row.name, dataset: { unit: row.unit || "" } }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        const isOther = selectedCategory.name.includes("Digər") || selectedOption?.text === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        let units = allUnits.slice();
        const itemUnit = selectedOption?.dataset.unit || "";
        if (itemUnit === "kq") units = weightUnits.slice();
        else if (itemUnit === "litr") units = volumeUnits.slice();
        else if (itemUnit) units = [itemUnit];
        setUnitSelectOptions("farm-unit", units, itemUnit || unitSelect.value || units[0]);
    }

    function updateIncomeItems(selectedItemName) {
        const categorySelect = document.getElementById("income-category");
        const itemSelect = document.getElementById("income-item");
        const manualWrap = document.getElementById("income-manual-wrap");
        const manualInput = document.getElementById("income-manual-name");
        const genderWrap = document.getElementById("income-gender-wrap");
        const animalIdWrap = document.getElementById("income-animal-id-wrap");
        const genderSelect = document.getElementById("income-gender");
        const selectedCategory = categorySelect.value;
        const row = incomeData[selectedCategory];
        const type = row ? row.type : "other";
        genderWrap.hidden = type !== "animal";
        animalIdWrap.hidden = type !== "animal";
        if (!row) {
            fillOptions(itemSelect, [], "Məhsul seçin", (entry) => ({ value: entry.name, label: entry.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            setControlRequired(genderSelect, false);
            setIncomeUnits(allUnits, "kq");
            return;
        }
        fillOptions(itemSelect, row.items || [], "Məhsul seçin", (entry) => ({ value: entry.name, label: entry.name, dataset: { unit: entry.unit || "" } }));
        if (selectedItemName) itemSelect.value = selectedItemName;
        const isOther = selectedCategory === "Digər" || itemSelect.options[itemSelect.selectedIndex]?.text === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        setControlRequired(genderSelect, type === "animal");
        let units = allUnits.slice();
        const itemUnit = itemSelect.options[itemSelect.selectedIndex]?.dataset.unit || "";
        if (type === "animal") units = ["ədəd"];
        else if (type === "seed") units = weightUnits.slice();
        else if (itemUnit === "kq") units = weightUnits.slice();
        else if (itemUnit === "litr") units = volumeUnits.slice();
        else if (itemUnit) units = [itemUnit];
        setIncomeUnits(units, units[0]);
    }

    function initFormOptions() {
        fillOptions(document.getElementById("expense-category"), expenseData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("animal-category"), animalData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("seed-category"), seedData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("tool-category"), toolData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("farm-category"), farmData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("income-category"), incomeCategories, "Kateqoriya seçin", (row) => ({ value: row, label: row }));
        setIncomeUnits(allUnits, "kq");
        setUnitSelectOptions("seed-unit", weightUnits, document.getElementById("seed-unit")?.value || weightUnits[0]);
        setUnitSelectOptions("farm-unit", allUnits, document.getElementById("farm-unit")?.value || allUnits[0]);
    }

    function showPanel(formType) {
        formShell.hidden = !formType;
        document.querySelectorAll("[data-form-panel]").forEach((panel) => { panel.hidden = panel.dataset.formPanel !== formType; });
        activeTitle.textContent = panelTitles[formType] || "Form";
        previewSection.hidden = true;
    }

    function validateBuilderForm(formType) {
        const panel = document.querySelector(`[data-form-panel="${formType}"]`);
        if (!panel) return false;
        const controls = panel.querySelectorAll("input, select, textarea");
        for (const control of controls) {
            if (control.required && !control.disabled && !control.closest("[hidden]")) {
                if (!control.reportValidity()) return false;
            }
        }
        return true;
    }

    function currentPayload(formType) {
        if (formType === "expense") {
            const categorySelect = document.getElementById("expense-category");
            const subcategorySelect = document.getElementById("expense-subcategory");
            const manualName = document.getElementById("expense-manual-name").value.trim();
            const label = manualName || subcategorySelect.options[subcategorySelect.selectedIndex]?.text || "";
            return {
                form_type: "expense",
                target_type: manualName ? "manual" : "subcategory",
                label,
                metadata: {
                    category_id: categorySelect.value,
                    category_name: categorySelect.options[categorySelect.selectedIndex]?.text || "",
                    subcategory_id: subcategorySelect.value,
                    subcategory_name: subcategorySelect.options[subcategorySelect.selectedIndex]?.text || "",
                    manual_name: manualName,
                    amount: document.getElementById("expense-amount").value
                }
            };
        }
        if (formType === "income") {
            const categorySelect = document.getElementById("income-category");
            const itemSelect = document.getElementById("income-item");
            const manualName = document.getElementById("income-manual-name").value.trim();
            const label = manualName || itemSelect.options[itemSelect.selectedIndex]?.text || "";
            return {
                form_type: "income",
                target_type: manualName ? "manual" : "item",
                label,
                metadata: {
                    category_name: categorySelect.value,
                    item_name: itemSelect.value,
                    manual_name: manualName,
                    quantity: document.getElementById("income-quantity").value,
                    unit: document.getElementById("income-unit").value,
                    gender: document.getElementById("income-gender").value,
                    identification_no: document.getElementById("income-animal-id").value.trim(),
                    amount: document.getElementById("income-amount").value
                }
            };
        }
        if (formType === "animal") {
            const categorySelect = document.getElementById("animal-category");
            const subcategorySelect = document.getElementById("animal-subcategory");
            const manualName = document.getElementById("animal-manual-name").value.trim();
            const label = manualName || subcategorySelect.options[subcategorySelect.selectedIndex]?.text || "";
            return {
                form_type: "animal",
                target_type: manualName ? "manual" : "subcategory",
                label,
                metadata: {
                    category_id: categorySelect.value,
                    category_name: categorySelect.options[categorySelect.selectedIndex]?.text || "",
                    subcategory_id: subcategorySelect.value,
                    subcategory_name: subcategorySelect.options[subcategorySelect.selectedIndex]?.text || "",
                    manual_name: manualName,
                    quantity: document.getElementById("animal-quantity").value,
                    identification_no: document.getElementById("animal-id").value.trim(),
                    gender: document.getElementById("animal-gender").value,
                    weight: document.getElementById("animal-weight").value,
                    price: document.getElementById("animal-price").value
                }
            };
        }
        if (formType === "seed") {
            const categorySelect = document.getElementById("seed-category");
            const itemSelect = document.getElementById("seed-item");
            const manualName = document.getElementById("seed-manual-name").value.trim();
            const label = manualName || itemSelect.options[itemSelect.selectedIndex]?.text || "";
            return {
                form_type: "seed",
                target_type: manualName ? "manual" : "item",
                label,
                metadata: {
                    category_id: categorySelect.value,
                    category_name: categorySelect.options[categorySelect.selectedIndex]?.text || "",
                    item_id: itemSelect.value,
                    item_name: itemSelect.options[itemSelect.selectedIndex]?.text || "",
                    manual_name: manualName,
                    quantity: document.getElementById("seed-quantity").value,
                    unit: document.getElementById("seed-unit").value,
                    price: document.getElementById("seed-price").value
                }
            };
        }
        if (formType === "tool") {
            const categorySelect = document.getElementById("tool-category");
            const itemSelect = document.getElementById("tool-item");
            const manualName = document.getElementById("tool-manual-name").value.trim();
            const label = manualName || itemSelect.options[itemSelect.selectedIndex]?.text || "";
            return {
                form_type: "tool",
                target_type: manualName ? "manual" : "item",
                label,
                metadata: {
                    category_id: categorySelect.value,
                    category_name: categorySelect.options[categorySelect.selectedIndex]?.text || "",
                    item_id: itemSelect.value,
                    item_name: itemSelect.options[itemSelect.selectedIndex]?.text || "",
                    manual_name: manualName,
                    quantity: document.getElementById("tool-quantity").value,
                    price: document.getElementById("tool-price").value
                }
            };
        }
        const categorySelect = document.getElementById("farm-category");
        const itemSelect = document.getElementById("farm-item");
        const manualName = document.getElementById("farm-manual-name").value.trim();
        const label = manualName || itemSelect.options[itemSelect.selectedIndex]?.text || "";
        return {
            form_type: "farm",
            target_type: manualName ? "manual" : "item",
            label,
            metadata: {
                category_id: categorySelect.value,
                category_name: categorySelect.options[categorySelect.selectedIndex]?.text || "",
                item_id: itemSelect.value,
                item_name: itemSelect.options[itemSelect.selectedIndex]?.text || "",
                manual_name: manualName,
                quantity: document.getElementById("farm-quantity").value,
                unit: document.getElementById("farm-unit").value,
                price: document.getElementById("farm-price").value
            }
        };
    }

    async function showBarcode(formType) {
        if (!validateBuilderForm(formType)) return;
        const payload = currentPayload(formType);
        if (!payload.label) return;
        const response = await fetch("{% url 'inventory:barcode' %}", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!data.success) return;
        previewSection.hidden = false;
        previewTitle.textContent = data.barcode.label;
        previewText.textContent = `${panelTitles[data.barcode.form_type] || data.barcode.form_type} üçün barkod`;
        barcodeCodeText.textContent = data.barcode.code;
        barcodeDownloadName = `${slugify(data.barcode.label)}-${data.barcode.code}`;
        JsBarcode("#barcode-svg", data.barcode.code, { format: "CODE128", displayValue: true, fontSize: 16, margin: 12, height: 68 });
        window.scrollTo({ top: previewSection.offsetTop - 20, behavior: "smooth" });
    }

    if (formTypeSelect) {
        formTypeSelect.addEventListener("change", function () { showPanel(this.value); });
    }
    document.getElementById("expense-category").addEventListener("change", () => updateExpenseSubcategories());
    document.getElementById("animal-category").addEventListener("change", () => updateAnimalSubcategories());
    document.getElementById("animal-quantity").addEventListener("input", syncAnimalIdentificationState);
    document.getElementById("seed-category").addEventListener("change", () => updateSeedItems());
    document.getElementById("seed-item").addEventListener("change", () => updateSeedItems(document.getElementById("seed-item").value));
    document.getElementById("tool-category").addEventListener("change", () => updateToolItems());
    document.getElementById("tool-item").addEventListener("change", () => updateToolItems(document.getElementById("tool-item").value));
    document.getElementById("farm-category").addEventListener("change", () => updateFarmItems());
    document.getElementById("farm-item").addEventListener("change", () => updateFarmItems(document.getElementById("farm-item").value));
    document.getElementById("income-category").addEventListener("change", () => updateIncomeItems());
    document.getElementById("income-item").addEventListener("change", () => updateIncomeItems(document.getElementById("income-item").value));

    document.querySelectorAll("[data-show-barcode]").forEach((btn) => {
        btn.addEventListener("click", async () => { await showBarcode(btn.dataset.showBarcode); });
    });

    downloadBtn.addEventListener("click", function () {
        const svgMarkup = new XMLSerializer().serializeToString(barcodeSvg);
        const svgBlob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
        const svgUrl = URL.createObjectURL(svgBlob);
        const image = new Image();
        image.onload = function () {
            const canvas = document.createElement("canvas");
            const width = image.width || 900;
            const height = image.height || 260;
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext("2d");
            context.fillStyle = "#ffffff";
            context.fillRect(0, 0, width, height);
            context.drawImage(image, 0, 0, width, height);
            URL.revokeObjectURL(svgUrl);
            const link = document.createElement("a");
            link.href = canvas.toDataURL("image/jpeg", 0.96);
            link.download = `${barcodeDownloadName}.jpg`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
        image.src = svgUrl;
    });

    copyBtn.addEventListener("click", async function () {
        const code = barcodeCodeText.textContent.trim();
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            copyBtn.textContent = "Kopyalandı";
            window.setTimeout(() => { copyBtn.textContent = "Kopyala"; }, 1400);
        } catch (error) {
            copyBtn.textContent = "Olmadı";
            window.setTimeout(() => { copyBtn.textContent = "Kopyala"; }, 1400);
        }
    });

    initFormOptions();
    syncAllRequiredStars();
    updateExpenseSubcategories();
    updateAnimalSubcategories();
    updateSeedItems();
    updateToolItems();
    updateFarmItems();
    updateIncomeItems();
    syncAnimalIdentificationState();

    if (initialForm) {
        if (formTypeSelect) formTypeSelect.value = initialForm;
        showPanel(initialForm);
    }
});
