{% load i18n common_extras static %}
      ;(function () {
        const container = document.getElementById('toast-container')
        const PENDING_TOAST_KEY = 'farm_pending_toast'

        function ensureContainer() {
          const existing = document.getElementById('toast-container')
          if (existing) return existing
          const next = document.createElement('div')
          next.id = 'toast-container'
          document.body.appendChild(next)
          return next
        }

        function mountToast(message, type = 'info') {
          const target = ensureContainer()
          const toast = document.createElement('div')
          toast.className = `toast-message toast-${type}`
          toast.innerHTML = `<span class="toast-text">${message}</span>`
          target.appendChild(toast)
          return toast
        }

        function scheduleToastRemoval(toast, index = 0) {
          const delay = index * 150
          setTimeout(() => {
            toast.style.opacity = '1'
          }, delay)

          setTimeout(() => {
            toast.style.transition = 'opacity 0.25s ease-out, transform 0.25s ease-out'
            toast.style.opacity = '0'
            toast.style.transform = 'translateY(8px)'
            setTimeout(() => {
              toast.remove()
              const target = document.getElementById('toast-container')
              if (target && !target.hasChildNodes()) {
                target.remove()
              }
            }, 300)
          }, TOAST_LIFETIME + delay)
        }

        const TOAST_LIFETIME = 1600 // 1.6 seconds
        let toasts = container ? Array.from(container.children) : []

        try {
          const pendingToast = JSON.parse(sessionStorage.getItem(PENDING_TOAST_KEY) || 'null')
          if (pendingToast?.message) {
            const toast = mountToast(pendingToast.message, pendingToast.type || 'info')
            toasts.push(toast)
            sessionStorage.removeItem(PENDING_TOAST_KEY)
          }
        } catch {
          sessionStorage.removeItem(PENDING_TOAST_KEY)
        }
      
        toasts.forEach((toast, index) => {
          scheduleToastRemoval(toast, index)
        })
      })()
