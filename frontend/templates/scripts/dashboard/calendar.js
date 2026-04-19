(function () {
  function initCalendar() {
    const layout = document.getElementById('calendarLayout')
    const panel = document.getElementById('calendarDayPanel')
    const days = document.querySelectorAll('.calendar-day-card')
    const picker = document.getElementById('calendar-month-picker')
    const input = document.getElementById('calendar-month-input')
    const navLinks = document.querySelectorAll('.calendar-nav-btn, .calendar-toolbar-link')
    const requestCache = window.__calendarRequestCache || (window.__calendarRequestCache = new Map())
    const pendingControllers = window.__calendarPendingControllers || (window.__calendarPendingControllers = {})
    let selectedDayHref = window.__calendarSelectedDayHref || ''

    function cancelPending(key) {
      const controller = pendingControllers[key]
      if (controller) {
        controller.abort()
        delete pendingControllers[key]
      }
    }

    function fetchHtml(url, headers, key) {
      const cacheKey = `${key}:${url}`
      if (requestCache.has(cacheKey)) {
        return Promise.resolve(requestCache.get(cacheKey))
      }

      cancelPending(key)
      const controller = new AbortController()
      pendingControllers[key] = controller

      return fetch(url, {
        headers,
        signal: controller.signal,
      })
        .then(response => response.text())
        .then(html => {
          requestCache.set(cacheKey, html)
          if (pendingControllers[key] === controller) {
            delete pendingControllers[key]
          }
          return html
        })
    }

    // Day Selection AJAX
    if (panel && days.length > 0) {
      days.forEach(dayBtn => {
        dayBtn.addEventListener('click', (e) => {
          const dayUrl = new URL(dayBtn.href, window.location.origin)
          const currentUrl = new URL(window.location.href)
          
          if (dayUrl.searchParams.get('month') === (currentUrl.searchParams.get('month') || new Date().toISOString().slice(0, 7))) {
            e.preventDefault()
            if (selectedDayHref === dayBtn.href) {
              return
            }
            selectedDayHref = dayBtn.href
            window.__calendarSelectedDayHref = selectedDayHref
            
            days.forEach(d => d.classList.remove('calendar-day-card--selected'))
            dayBtn.classList.add('calendar-day-card--selected')
            
            if (window.innerWidth < 1024) {
              panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }

            panel.style.opacity = '0.5'
            
            fetchHtml(dayBtn.href, { 'X-Requested-With': 'XMLHttpRequest' }, 'day-panel')
            .then(html => {
              panel.innerHTML = html
              panel.style.opacity = '1'
              window.history.pushState({}, '', dayBtn.href)
            })
            .catch(err => {
              if (err && err.name === 'AbortError') return
              window.location.href = dayBtn.href
            })
          }
        })
      })
    }

    // Month Picker AJAX
    if (picker && input && layout) {
      input.addEventListener('change', () => {
        if (!input.value) return
        const url = new URL(window.location.href)
        url.searchParams.set('month', input.value)
        url.searchParams.delete('day') // Reset day when changing month
        
        loadFullLayout(url.toString())
      })
    }

    // Navigation Links AJAX (Prev/Next Month)
    navLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        const url = new URL(link.href, window.location.origin)
        if (url.pathname === window.location.pathname) {
          e.preventDefault()
          loadFullLayout(link.href)
        }
      })
    })

    function loadFullLayout(url) {
      if (!layout) return
      
      layout.style.opacity = '0.5'
      selectedDayHref = ''
      window.__calendarSelectedDayHref = ''
      
      fetchHtml(url, { 'X-Requested-With': 'XMLHttpRequest', 'X-Full-Layout': 'true' }, 'full-layout')
      .then(html => {
        layout.innerHTML = html
        layout.style.opacity = '1'
        window.history.pushState({}, '', url)
        initCalendar() // Re-attach events
      })
      .catch(err => {
        if (err && err.name === 'AbortError') return
        window.location.href = url
      })
    }
  }

  initCalendar()
})()
