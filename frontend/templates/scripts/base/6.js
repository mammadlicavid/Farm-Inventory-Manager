{% load i18n common_extras static %}
      ;(function () {
        const menuToggle = document.getElementById('menuToggle')
        const sideDrawer = document.getElementById('sideDrawer')
        const body = document.body
      
        if (menuToggle && sideDrawer) {
          menuToggle.addEventListener('click', (e) => {
            e.preventDefault()
            body.classList.toggle('drawer-open')
          })
      
          // Close drawer when clicking outside (optional but good practice)
          document.addEventListener('click', (e) => {
            if (body.classList.contains('drawer-open') && !sideDrawer.contains(e.target) && !menuToggle.contains(e.target)) {
              body.classList.remove('drawer-open')
            }
          })
        }
      })()
