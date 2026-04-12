{% load i18n common_extras static %}
    const subcategoryData = JSON.parse(
        document.getElementById('expense-subcats-data').textContent
    );

    const categorySelect = document.getElementById('category-select');
    const subcategorySelect = document.getElementById('subcategory-select');

    categorySelect.addEventListener('change', function () {
        const categoryId = this.value;
        const categoryText = this.options[this.selectedIndex].text;
        const subcats = subcategoryData[categoryId] || [];
        const subcategoryGroup = document.getElementById('subcategory-field-group');
        const manualGroup = document.getElementById('manual-name-group');
        const manualInput = document.getElementById('manual-name-input');

        if (categoryText === "Digər" || categoryText.includes("Digər")) {
            subcategoryGroup.style.display = 'none';
            subcategorySelect.required = false;
            subcategorySelect.disabled = true;

            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';

            subcategoryGroup.style.display = 'block';
            subcategorySelect.required = true;

            subcategorySelect.innerHTML = '<option value="" disabled selected>{% trans "Alt kateqoriya seçin" %}</option>';

            subcats.forEach(sub => {
                const option = document.createElement('option');
                option.value = sub.id;
                option.textContent = sub.name;
                subcategorySelect.appendChild(option);
            });

            subcategorySelect.disabled = false;
        }
    });

    const expenseFilterForm = document.getElementById("expense-filter-form");
    const expenseFilterCategory = document.getElementById("expense-filter-category");
    const expenseFilterSubcategory = document.getElementById("expense-filter-subcategory");
    const expenseFilterSearch = expenseFilterForm?.querySelector('input[name="q"]');
    const expenseFilterReset = document.getElementById("expense-filter-reset");
    const expenseCards = Array.from(document.querySelectorAll("#expense-list .expense-item-card"));
    const expenseListController = window.createProgressiveListController({ items: expenseCards, batchSize: 100 });
    const expenseListEmpty = document.getElementById("expense-list-empty");
    const expenseFilterEmpty = document.getElementById("expense-filter-empty");
    const expenseCrudWrapper = document.querySelector(".crud-desktop-wrapper");
    const expenseListColumn = document.querySelector(".crud-list-column");
    const expenseFilterPlaceholder = document.createComment("expense-filter-placeholder");
    let expenseFilterTimer = null;

    expenseFilterForm?.parentNode?.insertBefore(expenseFilterPlaceholder, expenseFilterForm);
    expenseFilterForm?.addEventListener("submit", (event) => event.preventDefault());

    function normalizeExpenseText(value) {
        return String(value || "").trim().toLocaleLowerCase("az");
    }

    function updateExpenseFilterSubcategories(categoryName, selectedValue = "") {
        if (!expenseFilterSubcategory) return;
        expenseFilterSubcategory.innerHTML = '<option value="">{% trans "Bütün alt kateqoriyalar" %}</option>';
        if (!categoryName) return;

        if (categoryName === "Digər") {
            const option = document.createElement("option");
            option.value = "Digər";
            option.textContent = "Digər";
            if (selectedValue === "Digər") option.selected = true;
            expenseFilterSubcategory.appendChild(option);
            return;
        }

        const categoryEntry = Object.entries(subcategoryData).find(([, items]) =>
            items.length && items[0] && items.some(() => true)
        );

        Object.entries(subcategoryData).forEach(([, items]) => {
            items.forEach((sub) => {
                if (!sub || !sub.name) return;
            });
        });

        const matchedCategory = Array.from(categorySelect.options).find((opt) => opt.text === categoryName);
        if (!matchedCategory) return;
        const subcats = subcategoryData[matchedCategory.value] || [];
        subcats.forEach((sub) => {
            const option = document.createElement("option");
            option.value = sub.name;
            option.textContent = sub.name;
            if (sub.name === selectedValue) option.selected = true;
            expenseFilterSubcategory.appendChild(option);
        });
    }

    function applyExpenseFilters() {
        const category = expenseFilterCategory?.value || "";
        const subcategory = expenseFilterSubcategory?.value || "";
        const dateFrom = expenseFilterForm?.querySelector('input[name="date_from"]')?.value || "";
        const dateTo = expenseFilterForm?.querySelector('input[name="date_to"]')?.value || "";
        const term = normalizeExpenseText(expenseFilterSearch?.value || "");
        let visibleCount = 0;

        expenseCards.forEach((card) => {
            const matchCategory = !category || (card.dataset.category || "") === category;
            const matchSubcategory = !subcategory || normalizeExpenseText(card.dataset.subcategory) === normalizeExpenseText(subcategory);
            const cardDate = card.dataset.date || "";
            const matchDateFrom = !dateFrom || (cardDate && cardDate >= dateFrom);
            const matchDateTo = !dateTo || (cardDate && cardDate <= dateTo);
            const matchSearch = !term || normalizeExpenseText(card.dataset.search).includes(term);
            const show = matchCategory && matchSubcategory && matchDateFrom && matchDateTo && matchSearch;
            card.dataset.filterMatch = show ? "1" : "0";
            if (show) visibleCount += 1;
        });

        expenseListController.refresh(true);

        if (expenseListEmpty) expenseListEmpty.style.display = "none";
        if (expenseFilterEmpty) expenseFilterEmpty.style.display = visibleCount === 0 ? "block" : "none";
    }

    expenseFilterCategory?.addEventListener("change", () => {
        updateExpenseFilterSubcategories(expenseFilterCategory.value);
        applyExpenseFilters();
    });

    expenseFilterForm?.querySelectorAll('select[id="expense-filter-subcategory"], input[name="date_from"], input[name="date_to"]').forEach((control) => {
        control.addEventListener("change", applyExpenseFilters);
    });

    expenseFilterSearch?.addEventListener("input", () => {
        clearTimeout(expenseFilterTimer);
        expenseFilterTimer = setTimeout(applyExpenseFilters, 300);
    });

    expenseFilterReset?.addEventListener("click", () => {
        if (expenseFilterCategory) expenseFilterCategory.value = "";
        if (expenseFilterSubcategory) {
            expenseFilterSubcategory.innerHTML = '<option value="">{% trans "Bütün alt kateqoriyalar" %}</option>';
            expenseFilterSubcategory.value = "";
        }
        const dateFromInput = expenseFilterForm?.querySelector('input[name="date_from"]');
        const dateToInput = expenseFilterForm?.querySelector('input[name="date_to"]');
        if (dateFromInput) dateFromInput.value = "";
        if (dateToInput) dateToInput.value = "";
        if (expenseFilterSearch) expenseFilterSearch.value = "";
        applyExpenseFilters();
    });

    function repositionExpenseFilter() {
        if (!expenseFilterForm || !expenseListColumn || !expenseFilterPlaceholder) return;
        if (window.innerWidth < 1024) {
            expenseCrudWrapper?.insertBefore(expenseFilterForm, expenseListColumn);
        } else if (expenseFilterPlaceholder.parentNode) {
            expenseFilterPlaceholder.parentNode.insertBefore(expenseFilterForm, expenseFilterPlaceholder.nextSibling);
        }
    }

    window.addEventListener("resize", repositionExpenseFilter);
    repositionExpenseFilter();
    applyExpenseFilters();
