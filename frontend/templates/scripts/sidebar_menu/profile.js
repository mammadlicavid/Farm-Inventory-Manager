{% load i18n common_extras static %}
  (function () {
    const form = document.getElementById('profile-form');
    const toggleBtn = document.getElementById('profile-edit-toggle');
    const saveActions = document.getElementById('profile-save-actions');
    const inputs = Array.from(document.querySelectorAll('.profile-editable'));

    if (!toggleBtn || !saveActions || inputs.length === 0) return;

    let editing = false;

    function syncState() {
      inputs.forEach(function (input) {
        input.readOnly = !editing;
      });
      saveActions.hidden = !editing;
      toggleBtn.innerHTML = editing
        ? '<i class="fa-solid fa-xmark"></i> {% trans "Ləğv et" %}'
        : '<i class="fa-solid fa-pen"></i> {% trans "Düzəliş et" %}';
      if (!editing) {
        form.reset();
      }
    }

    toggleBtn.addEventListener('click', function () {
      editing = !editing;
      syncState();
      if (editing) {
        inputs[0].focus();
      }
    });

    syncState();
  })();
