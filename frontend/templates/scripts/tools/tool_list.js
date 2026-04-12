{% load i18n common_extras static %}
    const toolCategoryItemMap = JSON.parse(document.getElementById("tool-category-item-map")?.textContent || "{}");
    const toolFilterForm = document.getElementById("tool-filter-form");
    const toolFilterCategory = document.getElementById("tool-filter-category");
    const toolFilterItem = document.getElementById("tool-filter-item");
    const selectedToolFilterItem = "{{ selected_item|default:''|escapejs }}";
    const toolFilterSearch = toolFilterForm?.querySelector('input[name="q"]');
    const toolFilterReset = document.getElementById("tool-filter-reset");
    const toolCards = Array.from(document.querySelectorAll("#tool-list .expense-item-card"));
    const toolListController = window.createProgressiveListController({ items: toolCards, batchSize: 100 });
    const toolListEmpty = document.getElementById("tool-list-empty");
    const toolCrudWrapper = document.querySelector(".crud-desktop-wrapper");
    const toolListColumn = document.querySelector(".crud-list-column");
    const toolFilterPlaceholder = document.createComment("tool-filter-placeholder");
    let toolFilterTimer = null;

    toolFilterForm?.parentNode?.insertBefore(toolFilterPlaceholder, toolFilterForm);

    toolFilterForm?.addEventListener("submit", (event) => event.preventDefault());

    function normalizeToolText(value) {
        return String(value || "").trim().toLocaleLowerCase("az");
    }

    function applyToolFilters() {
        const category = toolFilterCategory?.value || "";
        const item = toolFilterItem?.value || "";
        const movement = toolFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = toolFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = toolFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        const term = normalizeToolText(toolFilterSearch?.value || "");
        let visibleCount = 0;

        toolCards.forEach((card) => {
            const matchCategory = !category || (card.dataset.category || "") === category;
            const matchItem = !item || (card.dataset.item || "") === item;
            const matchMovement = !movement || (card.dataset.movement || "") === movement;
            const cardDate = card.dataset.date || "";
            const matchDateFrom = !dateFrom || (cardDate && cardDate >= dateFrom);
            const matchDateTo = !dateTo || (cardDate && cardDate <= dateTo);
            const matchSearch = !term || normalizeToolText(card.dataset.search).includes(term);
            const show = matchCategory && matchItem && matchMovement && matchDateFrom && matchDateTo && matchSearch;
            card.dataset.filterMatch = show ? "1" : "0";
            if (show) visibleCount += 1;
        });

        toolListController.refresh(true);

        if (toolListEmpty) {
            toolListEmpty.style.display = visibleCount === 0 ? "flex" : "none";
        }
    }

    function updateToolFilterItems(categoryId, selectedItemId = "") {
        if (!toolFilterItem) return;
        toolFilterItem.innerHTML = '<option value="">{% trans "Bütün alət növləri" %}</option>';
        if (!categoryId) return;
        const items = toolCategoryItemMap[String(categoryId)] || [];
        items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.id);
            option.textContent = item.name;
            if (String(item.id) === String(selectedItemId)) {
                option.selected = true;
            }
            toolFilterItem.appendChild(option);
        });
    }

    if (toolFilterCategory) {
        toolFilterCategory.addEventListener("change", () => {
            updateToolFilterItems(toolFilterCategory.value);
            applyToolFilters();
        });
        if (toolFilterCategory.value) {
            updateToolFilterItems(toolFilterCategory.value, selectedToolFilterItem);
        }
    }

    toolFilterForm?.querySelectorAll('select[name="item"], select[name="movement"], input[name="date_from"], input[name="date_to"]').forEach((control) => {
        control.addEventListener("change", applyToolFilters);
    });

    toolFilterSearch?.addEventListener("input", () => {
        clearTimeout(toolFilterTimer);
        toolFilterTimer = setTimeout(applyToolFilters, 300);
    });

    toolFilterReset?.addEventListener("click", () => {
        if (toolFilterCategory) toolFilterCategory.value = "";
        if (toolFilterItem) {
            toolFilterItem.innerHTML = '<option value="">{% trans "Bütün alət növləri" %}</option>';
            toolFilterItem.value = "";
        }
        const movementInput = toolFilterForm?.querySelector('select[name="movement"]');
        const dateFromInput = toolFilterForm?.querySelector('input[name="date_from"]');
        const dateToInput = toolFilterForm?.querySelector('input[name="date_to"]');
        if (movementInput) movementInput.value = "";
        if (dateFromInput) dateFromInput.value = "";
        if (dateToInput) dateToInput.value = "";
        if (toolFilterSearch) toolFilterSearch.value = "";
        applyToolFilters();
    });

    function repositionToolFilter() {
        if (!toolFilterForm || !toolListColumn || !toolFilterPlaceholder) return;
        if (window.innerWidth < 1024) {
            toolCrudWrapper?.insertBefore(toolFilterForm, toolListColumn);
        } else if (toolFilterPlaceholder.parentNode) {
            toolFilterPlaceholder.parentNode.insertBefore(toolFilterForm, toolFilterPlaceholder.nextSibling);
        }
    }

    function hasActiveToolFilters() {
        const movement = toolFilterForm?.querySelector('select[name="movement"]')?.value || "";
        const dateFrom = toolFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = toolFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        return Boolean(
            (toolFilterCategory?.value || "") ||
            (toolFilterItem?.value || "") ||
            movement ||
            dateFrom ||
            dateTo ||
            normalizeToolText(toolFilterSearch?.value || "")
        );
    }

    function initializeToolList() {
        repositionToolFilter();
        if (hasActiveToolFilters()) {
            applyToolFilters();
            return;
        }
        if (toolCards.length > 120) {
            window.requestAnimationFrame(() => toolListController.refresh(true));
        }
    }

    window.addEventListener("resize", repositionToolFilter);
    if ("requestAnimationFrame" in window) {
        window.requestAnimationFrame(initializeToolList);
    } else {
        initializeToolList();
    }

    const TOOL_STATE_KEY = "tool_form_state_session_v1";
    const TOOL_KEEP_KEY = "tool_form_keep_v1";
    const toolPriceInput = document.querySelector('#tool-form input[name="price"]');
    const toolZeroPriceSourceGroup = document.getElementById('tool-zero-price-source-group');
    const toolZeroPriceSourceSelect = document.getElementById('tool-zero-price-source');

    function saveToolState(categoryId, itemId) {
        sessionStorage.setItem(TOOL_STATE_KEY, JSON.stringify({ categoryId, itemId }));
    }

    function loadToolState() {
        try {
            return JSON.parse(sessionStorage.getItem(TOOL_STATE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function clearToolState() {
        sessionStorage.removeItem(TOOL_STATE_KEY);
        sessionStorage.removeItem(TOOL_KEEP_KEY);
    }

    function syncToolZeroPriceSource() {
        if (!toolPriceInput || !toolZeroPriceSourceGroup || !toolZeroPriceSourceSelect) return;
        const raw = String(toolPriceInput.value || "").trim();
        const parsed = Number(raw.replace(",", "."));
        const shouldShow = !raw || (Number.isFinite(parsed) && parsed === 0);
        toolZeroPriceSourceGroup.style.display = shouldShow ? "block" : "none";
        toolZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) toolZeroPriceSourceSelect.value = "";
    }

    function resetToolOtherFields() {
        const manualInput = document.getElementById("manual-name-input");
        if (manualInput) manualInput.value = "";
        const qty = document.querySelector('input[name="quantity"]');
        if (qty) qty.value = "";
        const price = document.querySelector('input[name="price"]');
        if (price) price.value = "";
        if (toolZeroPriceSourceSelect) toolZeroPriceSourceSelect.value = "";
        const info = document.querySelector('textarea[name="additional_info"]');
        if (info) info.value = "";
        syncToolZeroPriceSource();
    }

    let pendingToolItemId = null;

    function populateToolItems(categoryId, selectedItemId = "") {
        const itemSelect = document.getElementById('id_item');
        if (!itemSelect) return;
        const items = toolCategoryItemMap[String(categoryId)] || [];
        let html = '<option value="">{% trans "Seçin..." %}</option>';
        items.forEach((item) => {
            const selectedAttr = String(item.id) === String(selectedItemId) ? ' selected' : '';
            html += `<option value="${item.id}"${selectedAttr}>${item.name}</option>`;
        });
        itemSelect.innerHTML = html;
        itemSelect.disabled = false;
    }

    document.getElementById('id_category').addEventListener('change', function () {
        const categoryId = this.value;
        const categoryText = this.options[this.selectedIndex].text;
        const itemSelect = document.getElementById('id_item');
        const itemGroup = document.getElementById('item-field-group');
        const manualGroup = document.getElementById('manual-name-group');
        const manualInput = document.getElementById('manual-name-input');

        if (categoryText === "Digər") {
            itemGroup.style.display = 'none';
            itemSelect.required = false;
            itemSelect.disabled = true;
            saveToolState(categoryId, "");
            resetToolOtherFields();
            sessionStorage.removeItem(TOOL_KEEP_KEY);

            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';

            itemGroup.style.display = 'block';
            itemSelect.required = true;

            if (!categoryId) {
                itemSelect.disabled = true;
                itemSelect.innerHTML = '<option value="">{% trans "Əvvəlcə kateqoriya seçin..." %}</option>';
                return;
            }
            populateToolItems(categoryId, pendingToolItemId);
            pendingToolItemId = null;
            resetToolOtherFields();
            saveToolState(categoryId, itemSelect.value || "");
            handleToolItemSelection();
        }
    });

    function handleToolItemSelection() {
        const selected = document.getElementById('id_item').options[document.getElementById('id_item').selectedIndex];
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

    document.getElementById('id_item').addEventListener('change', function () {
        const categoryId = document.getElementById('id_category').value;
        saveToolState(categoryId, this.value);
        handleToolItemSelection();
    });
    toolPriceInput?.addEventListener('input', syncToolZeroPriceSource);
    toolPriceInput?.addEventListener('change', syncToolZeroPriceSource);

    const toolForm = document.getElementById('tool-form');
    if (toolForm) {
        toolForm.addEventListener('submit', () => {
            sessionStorage.setItem(TOOL_KEEP_KEY, "1");
            const categoryId = document.getElementById('id_category').value;
            const itemId = document.getElementById('id_item')?.value || "";
            saveToolState(categoryId, itemId);
        });
    }

    (function restoreToolState() {
        const saved = loadToolState();
        if (sessionStorage.getItem(TOOL_KEEP_KEY) !== "1" || !saved.categoryId) {
            clearToolState();
            return;
        }
        pendingToolItemId = saved.itemId || null;
        const categorySelect = document.getElementById('id_category');
        categorySelect.value = saved.categoryId;
        categorySelect.dispatchEvent(new Event('change'));
        sessionStorage.removeItem(TOOL_KEEP_KEY);
    })();

    window.addEventListener("pagehide", () => {
        if (sessionStorage.getItem(TOOL_KEEP_KEY) !== "1") {
            clearToolState();
        }
    });

    syncToolZeroPriceSource();
