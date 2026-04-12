{% load i18n common_extras static %}
    const subcategoryData = JSON.parse(
        document.getElementById('animal-subcats-data').textContent
    );

    const categorySelect = document.getElementById('category-select');
    const subcategorySelect = document.getElementById('subcategory-select');
    const qtyInput = document.querySelector('input[name="quantity"]');
    const idInput = document.querySelector('input[name="identification_no"]');
    const animalPriceInput = document.querySelector('#animal-form input[name="price"]');
    const animalZeroPriceSourceGroup = document.getElementById('animal-zero-price-source-group');
    const animalZeroPriceSourceSelect = document.getElementById('animal-zero-price-source');

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

            manualGroup.style.display = 'block';
            manualInput.required = true;
        } else {
            manualGroup.style.display = 'none';
            manualInput.required = false;
            manualInput.value = '';

            subcategoryGroup.style.display = 'block';
            subcategorySelect.required = true;

            subcategorySelect.innerHTML = '<option value="" disabled selected>{% trans "Heyvan növünü seçin" %}</option>';

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
                handleAnimalSubcategorySelection();
            }
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

    subcategorySelect.addEventListener('change', handleAnimalSubcategorySelection);

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
        animalZeroPriceSourceGroup.style.display = shouldShow ? 'block' : 'none';
        animalZeroPriceSourceSelect.required = shouldShow;
        if (!shouldShow) animalZeroPriceSourceSelect.value = '';
    }

    if (qtyInput) {
        qtyInput.addEventListener('input', syncIdByQty);
        syncIdByQty();
    }
    animalPriceInput?.addEventListener('input', syncAnimalZeroPriceSource);
    animalPriceInput?.addEventListener('change', syncAnimalZeroPriceSource);

    (function initSelection() {
        const initialCategoryId = "{{ animal.subcategory.category_id|default:'' }}";
        const initialSubcategoryId = "{{ animal.subcategory_id|default:'' }}";

        if (initialCategoryId) {
            categorySelect.value = initialCategoryId;
            categorySelect.dispatchEvent(new Event('change'));
        }
        if (initialSubcategoryId) {
            subcategorySelect.value = initialSubcategoryId;
        }
        if (subcategorySelect && subcategorySelect.value) {
            handleAnimalSubcategorySelection();
        }
        syncAnimalZeroPriceSource();
    })();
