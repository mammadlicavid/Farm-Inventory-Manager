{% load i18n common_extras static %}
  ;(function () {
    const form = document.getElementById('settings-form')
    if (!form) return

    let submitting = false
    let submitTimer = null

    function submitSettings() {
      if (submitting) return
      submitting = true
      form.requestSubmit()
    }

    form.querySelectorAll('select, input[type="checkbox"]').forEach((control) => {
      control.addEventListener('change', () => {
        if (submitTimer) window.clearTimeout(submitTimer)
        submitTimer = window.setTimeout(submitSettings, 120)
      })
    })
  })()
