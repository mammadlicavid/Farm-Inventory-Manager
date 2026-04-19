{% load i18n common_extras static %}
    const subcategoriesByMain = {
        all: [
            { value: "all", label: "Hamısı" },
        ],
        toxumlar: [
            { value: "all", label: "Hamısı" },
            {% for cat in seed_categories %}
    { value: "seedcat-{{ cat.id }}", label: "{{ cat.name }}" },
    {% endfor %}
        ],
    aletler: [
        { value: "all", label: "Hamısı" },
        {% for cat in tool_categories %}
    { value: "toolcat-{{ cat.id }}", label: "{{ cat.name }}" },
    {% endfor %}
        ],
    heyvanlar: [
        { value: "all", label: "Hamısı" },
        {% for cat in animal_categories %}
    { value: "animalcat-{{ cat.id }}", label: "{{ cat.name }}" },
    {% endfor %}
        ],
    teserrufat: [
        { value: "all", label: "Hamısı" },
        {% for cat in farm_product_categories %}
    { value: "farmcat-{{ cat.id }}", label: "{{ cat.name }}" },
    {% endfor %}
        ],
    };

    const mainSelect = document.getElementById("main-category-select");
    const subSelect = document.getElementById("subcategory-select");
    const sortSelect = document.getElementById("stocks-sort");
    const searchInput = document.getElementById("stocks-search");
    const resetButton = document.getElementById("stocks-reset");
    const grid = document.getElementById("stocks-grid");
    const cards = Array.from(document.querySelectorAll(".product-card"));
    const emptyState = document.getElementById("stocks-empty");
    const modalBackdrop = document.getElementById("product-modal");
    const modalForm = document.getElementById("product-modal-form");
    const modalTitle = document.getElementById("modal-title");
    const modalSubtitle = document.getElementById("modal-subtitle");
    const modalQty = document.getElementById("modal-quantity");
    const modalUnit = document.getElementById("modal-unit");
    const modalUpdateType = document.getElementById("modal-update-type");
    const modalUpdateId = document.getElementById("modal-update-id");
    const modalQuantityRow = document.getElementById("modal-quantity-row");
    const modalGenderRow = document.getElementById("modal-gender-row");
    const modalMale = document.getElementById("modal-male");
    const modalFemale = document.getElementById("modal-female");
    const modalTotal = document.getElementById("modal-total");
    const modalSave = document.getElementById("modal-save");

    const FILTER_KEY = "stocks_filters_session_v1";
    const KEEP_KEY = "stocks_filters_keep_v1";

    function saveFilters() {
        const payload = {
            main: mainSelect.value,
            sub: subSelect.value,
            sort: sortSelect.value,
            search: searchInput.value || "",
        };
        sessionStorage.setItem(FILTER_KEY, JSON.stringify(payload));
    }

    function loadFilters() {
        try {
            return JSON.parse(sessionStorage.getItem(FILTER_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function resetFilters() {
        mainSelect.value = "all";
        buildSubOptions();
        subSelect.value = "all";
        sortSelect.value = "default";
        searchInput.value = "";
        applyFilters();
    }

    function buildSubOptions() {
        const main = mainSelect.value;
        const options = subcategoriesByMain[main] || [{ value: "all", label: "Hamısı" }];
        subSelect.innerHTML = "";
        options.forEach(opt => {
            const option = document.createElement("option");
            option.value = opt.value;
            option.textContent = opt.label;
            subSelect.appendChild(option);
        });
        subSelect.disabled = main === "all";
    }

    function normalizeSearch(value) {
        return String(value || "").trim().toLocaleLowerCase("az");
    }

    function parseQuantity(card) {
        const value = Number.parseFloat(card.dataset.quantity || "0");
        return Number.isFinite(value) ? value : 0;
    }

    function sortCards() {
        const mode = sortSelect.value;
        const sortedCards = [...cards].sort((left, right) => {
            const leftTitle = normalizeSearch(left.dataset.title || "");
            const rightTitle = normalizeSearch(right.dataset.title || "");
            const leftSubtitle = normalizeSearch(left.dataset.subtitle || "");
            const rightSubtitle = normalizeSearch(right.dataset.subtitle || "");
            const leftQty = parseQuantity(left);
            const rightQty = parseQuantity(right);
            const leftDefaultOrder = Number.parseInt(left.dataset.defaultOrder || "0", 10);
            const rightDefaultOrder = Number.parseInt(right.dataset.defaultOrder || "0", 10);

            if (mode === "default") {
                return leftDefaultOrder - rightDefaultOrder;
            }

            if (mode === "title_desc") {
                return rightTitle.localeCompare(leftTitle, "az");
            }
            if (mode === "qty_desc") {
                return (rightQty - leftQty)
                    || leftSubtitle.localeCompare(rightSubtitle, "az")
                    || leftTitle.localeCompare(rightTitle, "az");
            }
            if (mode === "qty_asc") {
                return (leftQty - rightQty)
                    || leftSubtitle.localeCompare(rightSubtitle, "az")
                    || leftTitle.localeCompare(rightTitle, "az");
            }
            return leftTitle.localeCompare(rightTitle, "az")
                || leftSubtitle.localeCompare(rightSubtitle, "az");
        });

        sortedCards.forEach(card => grid.appendChild(card));
    }

    function applyFilters() {
        sortCards();
        const main = mainSelect.value;
        const sub = subSelect.value;
        const term = normalizeSearch(searchInput.value || "");
        let visible = 0;
        cards.forEach(card => {
            const matchMain = main === "all" || card.dataset.main === main;
            const matchSub = sub === "all" || card.dataset.sub === sub;
            const title = normalizeSearch(card.querySelector(".product-title")?.textContent || "");
            const subtitle = normalizeSearch(card.querySelector(".product-subtitle")?.textContent || "");
            const matchSearch = !term || title.includes(term) || subtitle.includes(term);
            const show = matchMain && matchSub && matchSearch;
            card.style.display = show ? "" : "none";
            if (show) {
                visible += 1;
            }
        });
        emptyState.style.display = visible === 0 ? "block" : "none";
    }

    mainSelect.addEventListener("change", () => {
        buildSubOptions();
        applyFilters();
        saveFilters();
    });
    subSelect.addEventListener("change", () => {
        applyFilters();
        saveFilters();
    });
    sortSelect.addEventListener("change", () => {
        applyFilters();
        saveFilters();
    });
    searchInput.addEventListener("input", () => {
        applyFilters();
        saveFilters();
    });
    resetButton.addEventListener("click", () => {
        resetFilters();
        saveFilters();
    });

    const saved = loadFilters();
    const keep = sessionStorage.getItem(KEEP_KEY) === "1";
    if (keep && saved.main) {
        mainSelect.value = saved.main;
    }
    buildSubOptions();
    if (keep && saved.sub) {
        subSelect.value = saved.sub;
    }
    if (keep && saved.sort) {
        sortSelect.value = saved.sort;
    }
    if (keep && typeof saved.search === "string") {
        searchInput.value = saved.search;
    }
    if (!keep) {
        resetFilters();
    } else {
        applyFilters();
    }
    sessionStorage.removeItem(KEEP_KEY);

    function openModal(button) {
        modalTitle.textContent = button.dataset.title || "Məhsul";
        const guideText = "{% trans 'Sayım etdinizsə, hazırkı qalan miqdarı yazın.' %}";
        modalSubtitle.textContent = button.dataset.subtitle ? `${button.dataset.subtitle} • ${guideText}` : guideText;
        modalQty.value = button.dataset.qty || "";
        modalQty.step = button.dataset.step || "0.01";
        modalUnit.textContent = button.dataset.displayUnit || "";
        modalUpdateType.value = button.dataset.updateType || "";
        modalUpdateId.value = button.dataset.updateId || "";
        const updateType = button.dataset.updateType || "";
        if (updateType === "animal_sub" || updateType === "animal_other") {
            modalQuantityRow.style.display = "none";
            modalGenderRow.style.display = "block";
            modalMale.value = button.dataset.male || "0";
            modalFemale.value = button.dataset.female || "0";
            updateAnimalTotal();
        } else {
            modalQuantityRow.style.display = "block";
            modalGenderRow.style.display = "none";
        }
        modalBackdrop.style.display = "flex";
        if (updateType === "animal_sub" || updateType === "animal_other") {
            modalMale.focus();
        } else {
            modalQty.focus();
        }
    }

    function closeModal() {
        modalBackdrop.style.display = "none";
        modalForm.reset();
    }

    function showToast(message, type = "success") {
        if (!message) return;
        if (window.farmSync?.showToast) {
            window.farmSync.showToast(message, type);
            return;
        }
        window.alert(message);
    }

    function parseToastMessagesFromHtml(htmlText) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(String(htmlText || ""), "text/html");
        return Array.from(doc.querySelectorAll("#toast-container .toast-message")).map((node) => ({
            text: (node.textContent || "").trim(),
            isError: node.classList.contains("toast-error"),
            type: node.classList.contains("toast-error")
                ? "error"
                : node.classList.contains("toast-warning")
                    ? "warning"
                    : node.classList.contains("toast-info")
                        ? "info"
                        : "success",
        })).filter((entry) => entry.text);
    }

    function formatDisplayNumber(value) {
        const numberValue = Number.parseFloat(String(value || "0").replace(",", "."));
        if (!Number.isFinite(numberValue)) return String(value || "0");
        if (Number.isInteger(numberValue)) return String(numberValue);
        return numberValue.toFixed(2).replace(/\.?0+$/, "");
    }

    function updateCardQuantityDisplay(card, quantityValue) {
        card.dataset.quantity = String(quantityValue);
        const qtyButton = card.querySelector(".product-update-btn");
        const qtyValueNode = card.querySelector(".product-qty-value");
        if (qtyButton) qtyButton.dataset.qty = String(quantityValue);
        if (qtyValueNode) qtyValueNode.textContent = formatDisplayNumber(quantityValue);
    }

    function updateAnimalCardDisplay(card, maleValue, femaleValue) {
        const safeMale = Number.parseInt(maleValue || "0", 10) || 0;
        const safeFemale = Number.parseInt(femaleValue || "0", 10) || 0;
        const totalValue = safeMale + safeFemale;
        const qtyButton = card.querySelector(".product-update-btn");
        if (qtyButton) {
            qtyButton.dataset.male = String(safeMale);
            qtyButton.dataset.female = String(safeFemale);
            qtyButton.dataset.qty = String(totalValue);
        }
        updateCardQuantityDisplay(card, totalValue);
        const infoLines = card.querySelectorAll(".product-subtitle");
        const genderInfo = infoLines[1];
        if (genderInfo) {
            genderInfo.innerHTML = `{% trans 'Erkək' %}: ${safeMale}<br>{% trans 'Dişi' %}: ${safeFemale}`;
        }
    }

    async function submitStockUpdateForm() {
        const response = await fetch(modalForm.action, {
            method: "POST",
            body: new FormData(modalForm),
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const htmlText = await response.text();
        const responseMessages = parseToastMessagesFromHtml(htmlText);
        const errorMessage = responseMessages.find((entry) => entry.isError);
        if (!response.ok || errorMessage) {
            throw new Error(errorMessage?.text || "{% trans 'Stok yenilənmədi.' %}");
        }
        const firstMessage = responseMessages[0];
        if (firstMessage) showToast(firstMessage.text, firstMessage.type);
        return responseMessages;
    }

    document.querySelectorAll(".product-update-btn").forEach(btn => {
        btn.addEventListener("click", () => openModal(btn));
    });

    modalBackdrop.addEventListener("click", (event) => {
        if (event.target === modalBackdrop) {
            closeModal();
        }
    });

    document.getElementById("modal-cancel").addEventListener("click", closeModal);

    function updateAnimalTotal() {
        const male = parseInt(modalMale.value || "0", 10);
        const female = parseInt(modalFemale.value || "0", 10);
        const total = (isNaN(male) ? 0 : male) + (isNaN(female) ? 0 : female);
        modalTotal.textContent = total.toString();
    }

    modalMale.addEventListener("input", updateAnimalTotal);
    modalFemale.addEventListener("input", updateAnimalTotal);

    function applyModalUpdateToCard() {
        const updateType = modalUpdateType.value || "";
        const updateId = modalUpdateId.value || "";
        const card = cards.find((entry) => {
            const button = entry.querySelector(".product-update-btn");
            return button && button.dataset.updateType === updateType && button.dataset.updateId === updateId;
        });

        if (!card) return;

        if (updateType === "animal_sub" || updateType === "animal_other") {
            updateAnimalCardDisplay(card, modalMale.value, modalFemale.value);
        } else {
            updateCardQuantityDisplay(card, modalQty.value);
        }
        applyFilters();
    }

    if (modalForm) {
        modalForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();
            saveFilters();

            if (modalSave) modalSave.disabled = true;

            try {
                if (navigator.onLine) {
                    await submitStockUpdateForm();
                } else if (window.farmSync?.queueFormOperation) {
                    await window.farmSync.queueFormOperation(modalForm, {
                        reloadOnSuccess: false,
                        resetForm: false,
                        offlineMessage: "{% trans 'Offline saxlanıldı. İnternet gələndə göndəriləcək.' %}",
                        networkFallbackMessage: "{% trans 'Şəbəkə problemi var. Məlumat lokal saxlanıldı.' %}",
                    });
                } else {
                    throw new Error("{% trans 'Stok yenilənmədi.' %}");
                }

                applyModalUpdateToCard();
                closeModal();
            } catch (error) {
                showToast(error?.message || "{% trans 'Stok yenilənmədi.' %}", "error");
            } finally {
                if (modalSave) modalSave.disabled = false;
            }
        });
    }

    window.addEventListener("pagehide", () => {
        if (sessionStorage.getItem(KEEP_KEY) !== "1") {
            sessionStorage.removeItem(FILTER_KEY);
        }
    });
