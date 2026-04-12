{% load i18n common_extras static %}
        ;(function () {
          const headerTop = document.querySelector('.header-top')
          if (!headerTop) return

          let rightActions = headerTop.querySelector('.header-right-actions')
          if (!rightActions) {
            rightActions = document.createElement('div')
            rightActions.className = 'header-right-actions'
            headerTop.appendChild(rightActions)
          }

          let indicator = headerTop.querySelector('[data-sync-indicator]')
          if (indicator) {
            indicator.textContent = "{% trans 'Yoxlanır' %}"
          } else {
            indicator = document.createElement('a')
            indicator.href = "{% url 'sync:page' %}"
            indicator.className = 'status-badge sync-header-link'
            indicator.setAttribute('data-sync-indicator', '')
            indicator.textContent = "{% trans 'Yoxlanır' %}"

            const legacyBadge = headerTop.querySelector('.status-badge')
            if (legacyBadge) {
              legacyBadge.replaceWith(indicator)
            } else {
              rightActions.prepend(indicator)
            }
          }

          if (!rightActions.contains(indicator)) {
            rightActions.prepend(indicator)
          }

          const notificationsPath = "{% url 'notifications:list' %}"
          const notificationCount = parseInt("{{ pending_notification_count|default:0 }}", 10) || 0
          let notificationLink = headerTop.querySelector(`[data-header-notifications], a[href="${notificationsPath}"]`)
          if (!notificationLink) {
            notificationLink = document.createElement('a')
            notificationLink.href = notificationsPath
            notificationLink.className = 'header-icon-btn header-notification-link'
            notificationLink.setAttribute('data-header-notifications', '')
            notificationLink.setAttribute('title', "{% trans 'Xatırlatmalar' %}")
            notificationLink.setAttribute('aria-label', "{% trans 'Xatırlatmalar' %}")
            notificationLink.innerHTML = '<i class="fa-solid fa-bell"></i>'
          } else {
            notificationLink.classList.add('header-icon-btn', 'header-notification-link')
            notificationLink.setAttribute('data-header-notifications', '')
            notificationLink.setAttribute('title', "{% trans 'Xatırlatmalar' %}")
            notificationLink.setAttribute('aria-label', "{% trans 'Xatırlatmalar' %}")
          }

          const isNotificationsPage = window.location.pathname.indexOf(notificationsPath) === 0
          notificationLink.classList.toggle('is-current', isNotificationsPage)

          let notificationBadge = notificationLink.querySelector('.header-icon-badge')
          if (notificationCount > 0) {
            notificationLink.classList.add('header-icon-btn--with-badge')
            if (!notificationBadge) {
              notificationBadge = document.createElement('span')
              notificationBadge.className = 'header-icon-badge'
              notificationLink.appendChild(notificationBadge)
            }
            notificationBadge.textContent = notificationCount > 99 ? '99+' : String(notificationCount)
          } else if (notificationBadge) {
            notificationBadge.remove()
          }

          if (!rightActions.contains(notificationLink)) {
            const addTrigger = rightActions.querySelector('[data-notif-add-trigger]')
            if (addTrigger) {
              rightActions.insertBefore(notificationLink, addTrigger)
            } else {
              rightActions.appendChild(notificationLink)
            }
          }
        })()
