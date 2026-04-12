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
            }
        }
    });
