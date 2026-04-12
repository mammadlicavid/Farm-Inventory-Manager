{% load i18n common_extras static %}
      ;(function () {
        document.addEventListener('click', (event) => {
          const wrapper = event.target.closest('.click-focus')
          if (!wrapper) return
          const field = wrapper.querySelector('input, select, textarea')
          if (!field || field.disabled) return
          field.focus()
        })
      })()
