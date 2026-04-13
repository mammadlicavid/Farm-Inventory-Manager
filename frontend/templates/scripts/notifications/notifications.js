{% load i18n common_extras static %}
;(function () {
  const stockCatalog = {{ stock_rule_catalog_json|safe }};

  const reminderModal = document.getElementById('addModal');
  const reminderOpenBtn = document.getElementById('openAddModal');
  const reminderCloseBtn = document.getElementById('closeAddModal');
  const reminderEditButtons = document.querySelectorAll('[data-edit-notification]');
  const reminderModalTitle = document.getElementById('notificationModalTitle');
  const reminderModalId = document.getElementById('notificationModalId');
  const reminderTitleInput = document.getElementById('notificationModalTitleInput');
  const reminderCategoryInput = document.getElementById('notificationModalCategory');
  const reminderDateInput = document.getElementById('notificationModalDate');
  const reminderSubmitLabel = document.getElementById('notificationModalSubmitLabel');
  const reminderSubmitIcon = document.getElementById('notificationModalSubmitIcon');

  const ruleModal = document.getElementById('stockRuleEditModal');
  const ruleCloseBtn = document.getElementById('closeStockRuleModal');
  const ruleEditButtons = document.querySelectorAll('[data-edit-stock-rule]');
  const ruleModalTitle = document.getElementById('stockRuleModalTitle');
  const ruleModalId = document.getElementById('stockRuleModalId');
  const ruleModalSource = document.getElementById('stockRuleModalSource');
  const ruleModalCategory = document.getElementById('stockRuleModalCategory');
  const ruleModalItem = document.getElementById('stockRuleModalItem');
  const ruleModalThreshold = document.getElementById('stockRuleModalThreshold');

  const inlineRuleSource = document.getElementById('stockRuleSource');
  const inlineRuleCategory = document.getElementById('stockRuleCategory');
  const inlineRuleItem = document.getElementById('stockRuleItem');

  const toggleDetailsBtn = document.getElementById('toggleStockRuleDetails');
  const detailsPanel = document.getElementById('stockRuleDetails');

  const categoryPlaceholder = "{% trans 'Alt kateqoriya seçin' %}";
  const itemPlaceholder = "{% trans 'Məhsul növü seçin' %}";
  const notificationAddTitle = "{% trans 'Yeni xatırlatma' %}";
  const notificationEditTitle = "{% trans 'Xatırlatmanı düzəlt' %}";
  const notificationAddLabel = "{% trans 'Əlavə et' %}";
  const notificationEditLabel = "{% trans 'Yenilə' %}";
  const detailsShowText = "{% trans 'Limitləri göstər' %}";
  const detailsHideText = "{% trans 'Limitləri gizlət' %}";
  const detailsEmptyText = "{% trans 'Hələ əlavə edilmiş limit yoxdur.' %}";
  const stockRuleEditTitle = "{% trans 'Limiti düzəlt' %}";
  const itemIndex = {};

  stockCatalog.forEach((source) => {
    source.categories.forEach((category) => {
      category.items.forEach((item) => {
        itemIndex[item.item_key] = {
          sourceValue: source.value,
          categoryValue: category.value,
        };
      });
    });
  });

  function resetSelect(select, placeholder, disabled) {
    if (!select) return;
    select.innerHTML = '';
    const option = document.createElement('option');
    option.value = '';
    option.textContent = placeholder;
    select.appendChild(option);
    select.disabled = disabled;
  }

  function getSelectedSource(sourceValue) {
    return stockCatalog.find((entry) => entry.value === sourceValue);
  }

  function fillCategories(sourceSelect, categorySelect, itemSelect, selectedCategory) {
    if (!sourceSelect || !categorySelect || !itemSelect) return;
    resetSelect(categorySelect, categoryPlaceholder, true);
    resetSelect(itemSelect, itemPlaceholder, true);

    const selectedSource = getSelectedSource(sourceSelect.value);
    if (!selectedSource) return;

    selectedSource.categories.forEach((category) => {
      const option = document.createElement('option');
      option.value = category.value;
      option.textContent = category.label;
      categorySelect.appendChild(option);
    });
    categorySelect.disabled = false;

    if (selectedCategory) {
      categorySelect.value = selectedCategory;
    }
  }

  function fillItems(sourceSelect, categorySelect, itemSelect, selectedItem) {
    if (!sourceSelect || !categorySelect || !itemSelect) return;
    resetSelect(itemSelect, itemPlaceholder, true);

    const selectedSource = getSelectedSource(sourceSelect.value);
    if (!selectedSource) return;
    const selectedCategory = selectedSource.categories.find((entry) => entry.value === categorySelect.value);
    if (!selectedCategory) return;

    selectedCategory.items.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.item_key;
      option.textContent = `${item.label} • ${item.total_display} ${item.unit}`;
      itemSelect.appendChild(option);
    });
    itemSelect.disabled = false;

    if (selectedItem) {
      itemSelect.value = selectedItem;
    }
  }

  function bindRuleSelectors(sourceSelect, categorySelect, itemSelect) {
    if (!sourceSelect || !categorySelect || !itemSelect) return;
    sourceSelect.addEventListener('change', () => {
      fillCategories(sourceSelect, categorySelect, itemSelect);
    });
    categorySelect.addEventListener('change', () => {
      fillItems(sourceSelect, categorySelect, itemSelect);
    });
  }

  function showModal(modal) {
    if (!modal) return;
    modal.classList.add('active');
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.remove('active');
  }

  function resetReminderModal() {
    if (reminderModalId) reminderModalId.value = '';
    if (reminderTitleInput) reminderTitleInput.value = '';
    if (reminderCategoryInput) reminderCategoryInput.value = 'diger';
    if (reminderDateInput) reminderDateInput.value = '';
    if (reminderModalTitle) reminderModalTitle.textContent = notificationAddTitle;
    if (reminderSubmitLabel) reminderSubmitLabel.textContent = notificationAddLabel;
    if (reminderSubmitIcon) reminderSubmitIcon.className = 'fa-solid fa-plus';
  }

  function openReminderModalForAdd() {
    resetReminderModal();
    showModal(reminderModal);
  }

  function openReminderModalForEdit(button) {
    if (!button) return;
    resetReminderModal();
    if (reminderModalId) reminderModalId.value = button.dataset.notifId || '';
    if (reminderTitleInput) reminderTitleInput.value = button.dataset.notifTitle || '';
    if (reminderCategoryInput) reminderCategoryInput.value = button.dataset.notifCategory || 'diger';
    if (reminderDateInput) reminderDateInput.value = button.dataset.notifDate || '';
    if (reminderModalTitle) reminderModalTitle.textContent = notificationEditTitle;
    if (reminderSubmitLabel) reminderSubmitLabel.textContent = notificationEditLabel;
    if (reminderSubmitIcon) reminderSubmitIcon.className = 'fa-solid fa-pen';
    showModal(reminderModal);
  }

  function resetRuleModal() {
    if (ruleModalId) ruleModalId.value = '';
    if (ruleModalSource) ruleModalSource.value = '';
    resetSelect(ruleModalCategory, categoryPlaceholder, true);
    resetSelect(ruleModalItem, itemPlaceholder, true);
    if (ruleModalThreshold) ruleModalThreshold.value = '';
    if (ruleModalTitle) ruleModalTitle.textContent = stockRuleEditTitle;
  }

  function openRuleModal(button) {
    if (!button) return;
    resetRuleModal();

    const itemKey = button.dataset.ruleItem || '';
    const itemMeta = itemIndex[itemKey] || {};
    const sourceValue = button.dataset.ruleSource || itemMeta.sourceValue || '';
    const categoryValue = button.dataset.ruleCategory || itemMeta.categoryValue || '';
    const ruleName = button.dataset.ruleName || '';

    if (ruleModalId) {
      ruleModalId.value = button.dataset.ruleId || '';
    }
    if (ruleModalSource) {
      ruleModalSource.value = sourceValue;
      fillCategories(ruleModalSource, ruleModalCategory, ruleModalItem, categoryValue);
      fillItems(ruleModalSource, ruleModalCategory, ruleModalItem, itemKey);
    }
    if (ruleModalThreshold) {
      ruleModalThreshold.value = button.dataset.ruleThreshold || '';
    }
    if (ruleModalTitle) {
      ruleModalTitle.textContent = ruleName
        ? `${stockRuleEditTitle}: ${ruleName}`
        : stockRuleEditTitle;
    }
    showModal(ruleModal);
  }

  function setDetailsState(isOpen) {
    if (!detailsPanel || !toggleDetailsBtn) return;
    detailsPanel.hidden = !isOpen;
    toggleDetailsBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    toggleDetailsBtn.textContent = isOpen ? detailsHideText : detailsShowText;
  }

  bindRuleSelectors(inlineRuleSource, inlineRuleCategory, inlineRuleItem);
  bindRuleSelectors(ruleModalSource, ruleModalCategory, ruleModalItem);

  if (reminderOpenBtn) {
    reminderOpenBtn.addEventListener('click', openReminderModalForAdd);
  }
  if (reminderCloseBtn) {
    reminderCloseBtn.addEventListener('click', () => hideModal(reminderModal));
  }
  if (ruleCloseBtn) {
    ruleCloseBtn.addEventListener('click', () => hideModal(ruleModal));
  }

  if (reminderModal) {
    reminderModal.addEventListener('click', (event) => {
      if (event.target === reminderModal) {
        hideModal(reminderModal);
      }
    });
  }
  if (ruleModal) {
    ruleModal.addEventListener('click', (event) => {
      if (event.target === ruleModal) {
        hideModal(ruleModal);
      }
    });
  }

  reminderEditButtons.forEach((button) => {
    button.addEventListener('click', () => openReminderModalForEdit(button));
  });

  ruleEditButtons.forEach((button) => {
    button.addEventListener('click', () => openRuleModal(button));
  });

  if (toggleDetailsBtn) {
    setDetailsState(false);
    toggleDetailsBtn.disabled = !detailsPanel || detailsPanel.dataset.empty === 'true';
    if (toggleDetailsBtn.disabled) {
      toggleDetailsBtn.textContent = detailsEmptyText;
    }
    toggleDetailsBtn.addEventListener('click', () => {
      if (toggleDetailsBtn.disabled) return;
      setDetailsState(Boolean(detailsPanel?.hidden));
    });
  }
})();
