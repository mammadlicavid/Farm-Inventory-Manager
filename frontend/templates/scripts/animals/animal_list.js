{% load i18n common_extras static %}
    const animalFilterForm = document.getElementById("animal-filter-form");
    const animalFilterCategory = document.getElementById("animal-filter-category");
    const animalFilterSubcategory = document.getElementById("animal-filter-subcategory");
    const selectedAnimalFilterSubcategory = "{{ selected_subcategory|default:''|escapejs }}";
    const animalFilterSearch = animalFilterForm?.querySelector('input[name="q"]');
    const animalFilterReset = document.getElementById("animal-filter-reset");
    const animalCards = Array.from(document.querySelectorAll("#animal-list .expense-item-card"));
    const animalListController = window.createProgressiveListController({ items: animalCards, batchSize: 100 });
    const animalListEmpty = document.getElementById("animal-list-empty");
    const animalCrudWrapper = document.querySelector(".crud-desktop-wrapper");
    const animalListColumn = document.querySelector(".crud-list-column");
    const animalFilterPlaceholder = document.createComment("animal-filter-placeholder");
    let animalFilterTimer = null;

    animalFilterForm?.parentNode?.insertBefore(animalFilterPlaceholder, animalFilterForm);

    animalFilterForm?.addEventListener("submit", (event) => event.preventDefault());

    function normalizeAnimalText(value) {
        return String(value || "").trim().toLocaleLowerCase("az");
    }

    function applyAnimalFilters() {
        const category = animalFilterCategory?.value || "";
        const subcategory = animalFilterSubcategory?.value || "";
        const movement = animalFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = animalFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = animalFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        const term = normalizeAnimalText(animalFilterSearch?.value || "");
        let visibleCount = 0;

        animalCards.forEach((card) => {
            const matchCategory = !category || (card.dataset.category || "") === category;
            const matchSubcategory = !subcategory || (card.dataset.subcategory || "") === subcategory;
            const matchMovement = !movement || (card.dataset.movement || "") === movement;
            const cardDate = card.dataset.date || "";
            const matchDateFrom = !dateFrom || (cardDate && cardDate >= dateFrom);
            const matchDateTo = !dateTo || (cardDate && cardDate <= dateTo);
            const matchSearch = !term || normalizeAnimalText(card.dataset.search).includes(term);
            const show = matchCategory && matchSubcategory && matchMovement && matchDateFrom && matchDateTo && matchSearch;
            card.dataset.filterMatch = show ? "1" : "0";
            if (show) visibleCount += 1;
        });

        animalListController.refresh(true);

        if (animalListEmpty) {
            animalListEmpty.style.display = visibleCount === 0 ? "flex" : "none";
        }
    }

    function updateAnimalFilterSubcategories(categoryId, selectedSubId = "") {
        if (!animalFilterSubcategory) return;
        animalFilterSubcategory.innerHTML = '<option value="">{% trans "Bütün heyvan növləri" %}</option>';
        if (!categoryId) return;
        const filterData = JSON.parse(document.getElementById('animal-subcats-data').textContent);
        const subcats = filterData[categoryId] || [];
        subcats.forEach((sub) => {
            const option = document.createElement("option");
            option.value = String(sub.id);
            option.textContent = sub.name;
            if (String(sub.id) === String(selectedSubId)) {
                option.selected = true;
            }
            animalFilterSubcategory.appendChild(option);
        });
    }

    if (animalFilterCategory) {
        animalFilterCategory.addEventListener("change", () => {
            updateAnimalFilterSubcategories(animalFilterCategory.value);
            applyAnimalFilters();
        });
        if (animalFilterCategory.value) {
            updateAnimalFilterSubcategories(animalFilterCategory.value, selectedAnimalFilterSubcategory);
        }
    }

    animalFilterForm?.querySelectorAll('select[name="subcategory"], select[name="movement"], input[name="date_from"], input[name="date_to"]').forEach((control) => {
        control.addEventListener("change", applyAnimalFilters);
    });

    animalFilterSearch?.addEventListener("input", () => {
        clearTimeout(animalFilterTimer);
        animalFilterTimer = setTimeout(applyAnimalFilters, 300);
    });

    animalFilterReset?.addEventListener("click", () => {
        if (animalFilterCategory) animalFilterCategory.value = "";
        if (animalFilterSubcategory) {
            animalFilterSubcategory.innerHTML = '<option value="">{% trans "Bütün heyvan növləri" %}</option>';
            animalFilterSubcategory.value = "";
        }
        const movementInput = animalFilterForm?.querySelector('select[name="movement"]');
        const dateFromInput = animalFilterForm?.querySelector('input[name="date_from"]');
        const dateToInput = animalFilterForm?.querySelector('input[name="date_to"]');
        if (movementInput) movementInput.value = "";
        if (dateFromInput) dateFromInput.value = "";
        if (dateToInput) dateToInput.value = "";
        if (animalFilterSearch) animalFilterSearch.value = "";
        applyAnimalFilters();
    });

    function repositionAnimalFilter() {
        if (!animalFilterForm || !animalListColumn || !animalFilterPlaceholder) return;
        if (window.innerWidth < 1024) {
            animalCrudWrapper?.insertBefore(animalFilterForm, animalListColumn);
        } else if (animalFilterPlaceholder.parentNode) {
            animalFilterPlaceholder.parentNode.insertBefore(animalFilterForm, animalFilterPlaceholder.nextSibling);
        }
    }

    function hasActiveAnimalFilters() {
        const movement = animalFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = animalFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = animalFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        return Boolean(
            (animalFilterCategory?.value || "") ||
            (animalFilterSubcategory?.value || "") ||
            movement ||
            dateFrom ||
            dateTo ||
            normalizeAnimalText(animalFilterSearch?.value || "")
        );
    }

    function initializeAnimalList() {
        repositionAnimalFilter();
        if (hasActiveAnimalFilters()) {
            applyAnimalFilters();
            return;
        }
        if (animalCards.length > 120) {
            window.requestAnimationFrame(() => animalListController.refresh(true));
        }
    }

    window.addEventListener("resize", repositionAnimalFilter);
    if ("requestAnimationFrame" in window) {
        window.requestAnimationFrame(initializeAnimalList);
    } else {
        initializeAnimalList();
    }

    const ANIMAL_STATE_KEY = "animal_form_state_session_v1";
    const ANIMAL_KEEP_KEY = "animal_form_keep_v1";

    function saveAnimalState(categoryId, subcategoryId) {
        sessionStorage.setItem(ANIMAL_STATE_KEY, JSON.stringify({ categoryId, subcategoryId }));
    }

    function loadAnimalState() {
        try {
            return JSON.parse(sessionStorage.getItem(ANIMAL_STATE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function clearAnimalState() {
        sessionStorage.removeItem(ANIMAL_STATE_KEY);
        sessionStorage.removeItem(ANIMAL_KEEP_KEY);
    }

    function resetAnimalOtherFields() {
        const manualInput = document.getElementById("manual-name-input");
        if (manualInput) manualInput.value = "";
        const idNo = document.querySelector('input[name="identification_no"]');
        if (idNo) idNo.value = "";
        const qty = document.querySelector('input[name="quantity"]');
        if (qty) qty.value = "1";
        const weight = document.querySelector('input[name="weight"]');
        if (weight) weight.value = "";
        const price = document.querySelector('input[name="price"]');
        if (price) price.value = "";
        if (animalZeroPriceSourceSelect) animalZeroPriceSourceSelect.value = "";
        const info = document.querySelector('textarea[name="additional_info"]');
        if (info) info.value = "";
        const gender = document.querySelector('select[name="gender"]');
        if (gender) gender.value = "erkek";
        syncAnimalZeroPriceSource();
    }

    const subcategoryData = JSON.parse(document.getElementById('animal-subcats-data').textContent);

    const categorySelect = document.getElementById('category-select');
    const subcategorySelect = document.getElementById('subcategory-select');
    const qtyInput = document.querySelector('input[name="quantity"]');
    const idInput = document.querySelector('input[name="identification_no"]');
    const animalPriceInput = document.querySelector('#animal-form input[name="price"]');
    const animalZeroPriceSourceGroup = document.getElementById('animal-zero-price-source-group');
    const animalZeroPriceSourceSelect = document.getElementById('animal-zero-price-source');

    let pendingAnimalSubId = null;

    function syncIdByQty() {
        if (!qtyInput || !idInput) return;
        const qty = parseInt(qtyInput.value || "1", 10);
        if (Math.abs(qty) !== 1) {
            idInput.value = "";
            idInput.disabled = true;
            idInput.placeholder = "Miqdar ±1 olmadıqda ID yazılmır";
        } else {
            idInput.disabled = false;
            idInput.placeholder = "Məsələn: AZ12345";
        }
    }

    function syncAnimalZeroPriceSource() {
        if (!animalPriceInput || !animalZeroPriceSourceGroup || !animalZeroPriceSourceSelect) return;
        const raw = String(animalPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        animalZeroPriceSourceGroup.style.display = shouldShow ? "block" : "none";
        animalZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) animalZeroPriceSourceSelect.value = "";
    }

    if (qtyInput) {
        qtyInput.addEventListener('input', syncIdByQty);
        syncIdByQty();
    }
    animalPriceInput?.addEventListener('input', syncAnimalZeroPriceSource);
    animalPriceInput?.addEventListener('change', syncAnimalZeroPriceSource);

    categorySelect.addEventListener('change', function () {
        const categoryId = this.value;
        const categoryText = this.options[this.selectedIndex].text;
        const subcats = subcategoryData[categoryId] || [];
        const subcategoryGroup = document.getElementById('subcategory-field-group');
        const manualGroup = document.getElementById('manual-name-group');
        const manualInput = document.getElementById('manual-name-input');

        if (categoryText === "Digər") {
            subcategoryGroup.style.display = 'none';
            subcategorySelect.required = false;
            subcategorySelect.disabled = true;
            saveAnimalState(categoryId, "");
            resetAnimalOtherFields();
            sessionStorage.removeItem(ANIMAL_KEEP_KEY);

            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';

            subcategoryGroup.style.display = 'block';
            subcategorySelect.required = true;

            subcategorySelect.innerHTML = '<option value="" disabled selected>{% trans "Alt kateqoriya seçin" %}</option>';

            if (subcats.length === 0) {
                subcategorySelect.disabled = true;
                subcategorySelect.innerHTML = '<option value="" selected>{% trans "Alt kateqoriya yoxdur" %}</option>';
            } else {
                subcats.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub.id;
                    option.textContent = sub.name;
                    subcategorySelect.appendChild(option);
                });
                subcategorySelect.disabled = false;
                if (pendingAnimalSubId) {
                    subcategorySelect.value = pendingAnimalSubId;
                    pendingAnimalSubId = null;
                }
                handleAnimalSubcategorySelection();
            }
            resetAnimalOtherFields();
            saveAnimalState(categoryId, subcategorySelect.value || "");
        }
    });

    function handleAnimalSubcategorySelection() {
        const selected = subcategorySelect.options[subcategorySelect.selectedIndex];
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

    subcategorySelect.addEventListener('change', function () {
        const categoryId = categorySelect.value;
        saveAnimalState(categoryId, this.value);
        handleAnimalSubcategorySelection();
    });

    const animalForm = document.getElementById('animal-form');
    if (animalForm) {
        animalForm.addEventListener('submit', () => {
            sessionStorage.setItem(ANIMAL_KEEP_KEY, "1");
            const categoryId = categorySelect.value;
            const subcategoryId = subcategorySelect.value;
            saveAnimalState(categoryId, subcategoryId);
        });
    }

    (function restoreAnimalState() {
        const saved = loadAnimalState();
        if (sessionStorage.getItem(ANIMAL_KEEP_KEY) !== "1" || !saved.categoryId) {
            clearAnimalState();
            return;
        }
        pendingAnimalSubId = saved.subcategoryId || null;
        categorySelect.value = saved.categoryId;
        categorySelect.dispatchEvent(new Event('change'));
        sessionStorage.removeItem(ANIMAL_KEEP_KEY);
    })();

    window.addEventListener("pagehide", () => {
        if (sessionStorage.getItem(ANIMAL_KEEP_KEY) !== "1") {
            clearAnimalState();
        }
    });

    syncAnimalZeroPriceSource();
