{% load i18n common_extras static %}
      ;(function () {
        document.addEventListener(
          'wheel',
          (event) => {
            const field = event.target
            if (!(field instanceof HTMLInputElement)) return
            if (field.type !== 'number') return
            event.preventDefault()
          },
          { passive: false }
        )
      })()
