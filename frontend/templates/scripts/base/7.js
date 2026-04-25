;(function () {
  const STORAGE_PREFIX = 'farm_scroll_restore_v1:'
  const MAX_AGE_MS = 2 * 60 * 1000
  const RESTORE_DELAYS = [0, 30, 80, 200, 450]
  let userInterruptedRestore = false

  function now() {
    return Date.now()
  }

  function storageKey(pathname, search) {
    return `${STORAGE_PREFIX}${pathname}${search || ''}`
  }

  function pathStorageKey(pathname) {
    return `${STORAGE_PREFIX}${pathname}`
  }

  function currentPayload(reason) {
    return {
      x: window.scrollX || document.documentElement.scrollLeft || 0,
      y: window.scrollY || document.documentElement.scrollTop || 0,
      reason,
      createdAt: now(),
    }
  }

  function writePayloadForUrl(url, payload) {
    try {
      if (url.origin !== window.location.origin) return
      sessionStorage.setItem(storageKey(url.pathname, url.search), JSON.stringify(payload))
      sessionStorage.setItem(pathStorageKey(url.pathname), JSON.stringify(payload))
    } catch {
      // Storage can be unavailable in private or restricted browser modes.
    }
  }

  function saveScroll(reason, targetUrl) {
    const payload = currentPayload(reason)
    writePayloadForUrl(new URL(window.location.href), payload)

    if (!targetUrl) return
    try {
      writePayloadForUrl(new URL(targetUrl, window.location.href), payload)
    } catch {
      // Ignore invalid action/redirect URLs.
    }
  }

  function readPayload() {
    const keys = [
      storageKey(window.location.pathname, window.location.search),
      pathStorageKey(window.location.pathname),
    ]
    const uniqueKeys = Array.from(new Set(keys))

    for (const key of uniqueKeys) {
      try {
        const raw = sessionStorage.getItem(key)
        if (!raw) continue

        const payload = JSON.parse(raw)
        if (!payload || typeof payload.y !== 'number') {
          sessionStorage.removeItem(key)
          continue
        }
        if (!payload.createdAt || now() - payload.createdAt > MAX_AGE_MS) {
          sessionStorage.removeItem(key)
          continue
        }
        uniqueKeys.forEach((storedKey) => sessionStorage.removeItem(storedKey))
        return payload
      } catch {
        sessionStorage.removeItem(key)
      }
    }

    return null
  }

  function maxScrollTop() {
    const root = document.documentElement
    const body = document.body
    return Math.max(0, Math.max(root.scrollHeight, body ? body.scrollHeight : 0) - window.innerHeight)
  }

  function restoreScroll(payload) {
    if (!payload) return
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }

    const targetX = Math.max(0, payload.x || 0)
    const targetY = Math.max(0, payload.y || 0)

    RESTORE_DELAYS.forEach((delay, index) => {
      window.setTimeout(() => {
        if (userInterruptedRestore) return
        const top = Math.min(targetY, maxScrollTop())
        window.scrollTo({ left: targetX, top, behavior: 'auto' })

        if (index === RESTORE_DELAYS.length - 1 && 'scrollRestoration' in window.history) {
          window.history.scrollRestoration = 'auto'
        }
      }, delay)
    })
  }

  function isReloadNavigation() {
    const navigation = window.performance && window.performance.getEntriesByType
      ? window.performance.getEntriesByType('navigation')[0]
      : null
    return navigation && navigation.type === 'reload'
  }

  function resetScrollAfterPlainReload() {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }

    ;[0, 50, 150].forEach((delay, index, delays) => {
      window.setTimeout(() => {
        if (userInterruptedRestore) return
        window.scrollTo({ left: 0, top: 0, behavior: 'auto' })

        if (index === delays.length - 1 && 'scrollRestoration' in window.history) {
          window.history.scrollRestoration = 'auto'
        }
      }, delay)
    })
  }

  window.__farmPreserveScrollForNextNavigation = function (targetUrl, reason) {
    saveScroll(reason || 'operation-navigation', targetUrl)
  }

  document.addEventListener(
    'submit',
    (event) => {
      const form = event.target
      if (!(form instanceof HTMLFormElement)) return
      if (form.dataset.preserveScroll === 'false') return
      if (event.defaultPrevented) return

      if (form.dataset.syncEntity && form.dataset.syncDirectOnline !== 'true') return
      if (form.dataset.syncEntity && !navigator.onLine) return
      saveScroll('form-submit', form.dataset.syncSuccessRedirect || form.dataset.syncRedirectAfterQueue || form.action)
    }
  )

  ;['wheel', 'touchstart', 'pointerdown', 'keydown'].forEach((eventName) => {
    window.addEventListener(
      eventName,
      () => {
        userInterruptedRestore = true
      },
      { once: true, passive: true }
    )
  })

  const payload = readPayload()
  if (payload) {
    restoreScroll(payload)
  } else if (isReloadNavigation()) {
    resetScrollAfterPlainReload()
  }
})()
