(function () {
  const DB_NAME = 'farm_inventory_sync'
  const DB_VERSION = 2
  const STORE_NAME = 'operations'
  const DEVICE_ID_KEY = 'farm_sync_device_id'
  const LAST_SYNC_KEY = 'farm_sync_last_sync'
  const LAST_REMOTE_CURSOR_KEY = 'farm_sync_last_remote_cursor'
  const LAST_NOTIFIED_REMOTE_CURSOR_KEY = 'farm_sync_last_notified_remote_cursor'
  const STATUS_EVENT = 'farm-sync:update'
  const SYNC_URL = '/sync/push/'
  const STATUS_URL = '/sync/status/'
  const PULL_STATUS_URL = '/sync/pull-status/'
  const RETRY_INTERVAL_MS = 30000
  const HISTORY_LIMIT = 20
  const PENDING_TOAST_KEY = 'farm_pending_toast'

  let dbPromise = null
  let syncInProgress = false

  function generateId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID()
    }
    return `sync-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  function getDeviceId() {
    let deviceId = localStorage.getItem(DEVICE_ID_KEY)
    if (!deviceId) {
      deviceId = generateId()
      localStorage.setItem(DEVICE_ID_KEY, deviceId)
    }
    return deviceId
  }

  function getLastSync() {
    return localStorage.getItem(LAST_SYNC_KEY) || null
  }

  function setLastSync(value) {
    if (value) {
      localStorage.setItem(LAST_SYNC_KEY, value)
    }
  }

  function getLastRemoteCursor() {
    return localStorage.getItem(LAST_REMOTE_CURSOR_KEY) || null
  }

  function isNewerTimestamp(nextValue, currentValue) {
    if (!nextValue) return false
    if (!currentValue) return true

    const nextTime = new Date(nextValue).getTime()
    const currentTime = new Date(currentValue).getTime()

    if (Number.isNaN(nextTime) || Number.isNaN(currentTime)) {
      return nextValue > currentValue
    }

    return nextTime >= currentTime
  }

  function setLastRemoteCursor(value) {
    if (isNewerTimestamp(value, getLastRemoteCursor())) {
      localStorage.setItem(LAST_REMOTE_CURSOR_KEY, value)
    }
  }

  function getLastNotifiedRemoteCursor() {
    return localStorage.getItem(LAST_NOTIFIED_REMOTE_CURSOR_KEY) || null
  }

  function setLastNotifiedRemoteCursor(value) {
    if (isNewerTimestamp(value, getLastNotifiedRemoteCursor())) {
      localStorage.setItem(LAST_NOTIFIED_REMOTE_CURSOR_KEY, value)
    }
  }

  function getCookie(name) {
    const cookie = document.cookie
      .split(';')
      .map((part) => part.trim())
      .find((part) => part.startsWith(`${name}=`))

    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
  }

  function openDb() {
    if (dbPromise) return dbPromise

    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
      request.onupgradeneeded = () => {
        const db = request.result
        let store

        if (!db.objectStoreNames.contains(STORE_NAME)) {
          store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        } else {
          store = request.transaction.objectStore(STORE_NAME)
        }

        if (!store.indexNames.contains('status')) {
          store.createIndex('status', 'status', { unique: false })
        }
        if (!store.indexNames.contains('updatedAt')) {
          store.createIndex('updatedAt', 'updatedAt', { unique: false })
        }
      }
    })

    return dbPromise
  }

  async function withStore(mode, callback) {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, mode)
      const store = transaction.objectStore(STORE_NAME)
      const request = callback(store)

      transaction.oncomplete = () => resolve(request?.result)
      transaction.onerror = () => reject(transaction.error)
      transaction.onabort = () => reject(transaction.error)
    })
  }

  async function addOperation(operation) {
    const now = new Date().toISOString()
    return withStore('readwrite', (store) =>
      store.put({
        ...operation,
        status: 'pending',
        createdAt: operation.createdAt || now,
        updatedAt: now,
        error: '',
      })
    )
  }

  async function updateOperation(id, updates) {
    return withStore('readwrite', (store) => {
      const request = store.get(id)
      request.onsuccess = () => {
        const current = request.result
        if (!current) return
        store.put({
          ...current,
          ...updates,
          updatedAt: new Date().toISOString(),
        })
      }
      return request
    })
  }

  async function getAllOperations() {
    const items = await withStore('readonly', (store) => store.getAll())
    return Array.isArray(items) ? items : []
  }

  async function pruneHistory() {
    const items = await getAllOperations()
    const history = items
      .filter((item) => item.status !== 'pending')
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))

    const overflow = history.slice(HISTORY_LIMIT)
    for (const item of overflow) {
      await withStore('readwrite', (store) => store.delete(item.id))
    }
  }

  async function getPendingOperations() {
    const items = await getAllOperations()
    return items
      .filter((item) => item.status === 'pending')
      .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
  }

  async function getRecentHistory() {
    const items = await getAllOperations()
    return items
      .filter((item) => item.status !== 'pending')
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      .slice(0, HISTORY_LIMIT)
  }

  async function getPendingCount() {
    const items = await getPendingOperations()
    return items.length
  }

  function relativeTimeLabel(isoString) {
    if (!isoString) return 'Heç vaxt'

    const diff = Date.now() - new Date(isoString).getTime()
    const seconds = Math.max(0, Math.floor(diff / 1000))
    if (seconds < 60) return 'İndi'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} dəq əvvəl`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} saat əvvəl`
    const days = Math.floor(hours / 24)
    return `${days} gün əvvəl`
  }

  function labelForOperation(item) {
    const entityMap = {
      seed: 'Toxum',
      tool: 'Alət',
      animal: 'Heyvan',
      expense: 'Xərc',
      income: 'Gəlir',
      supplier: 'Təchizatçı',
      farm_product: 'Məhsul',
      quick_expense: 'Tez xərc',
      quick_income: 'Tez gəlir',
      stock: 'Stok',
    }
    const actionMap = {
      create: 'əlavə',
      update: 'düzəliş',
      delete: 'silmə',
      quick_add: 'əlavə',
      custom_amount: 'əlavə',
      template_add: 'əlavə',
    }
    return `${entityMap[item.entity] || item.entity} ${actionMap[item.action] || item.action}`
  }

  async function emitStatus(extra = {}) {
    const pendingOperations = await getPendingOperations()
    const history = await getRecentHistory()
    const detail = {
      online: navigator.onLine,
      pendingCount: pendingOperations.length,
      pendingOperations,
      history,
      lastSync: getLastSync(),
      remoteChanges: null,
      ...extra,
    }

    window.dispatchEvent(new CustomEvent(STATUS_EVENT, { detail }))
    updateIndicatorElements(detail)
    return detail
  }

  function updateIndicatorElements(detail) {
    document.querySelectorAll('[data-sync-indicator]').forEach((element) => {
      element.dataset.state = detail.online ? 'online' : 'offline'

      if (!detail.online) {
        element.textContent = detail.pendingCount > 0 ? `Oflayn, ${detail.pendingCount} gözləyir` : 'Oflayn'
        return
      }

      if (detail.pendingCount > 0) {
        element.textContent = `${detail.pendingCount} sinxronizasiya gözləyir`
        return
      }

      if (detail.remoteChanges && detail.remoteChanges.total_changes > 0) {
        element.textContent = `${detail.remoteChanges.total_changes} uzaq dəyişiklik var`
        return
      }

      element.textContent = detail.lastSync ? `Sinx: ${relativeTimeLabel(detail.lastSync)}` : 'Sinx hazırdır'
    })

    document.querySelectorAll('[data-sync-last]').forEach((element) => {
      element.textContent = detail.lastSync ? relativeTimeLabel(detail.lastSync) : 'Heç vaxt'
    })

    document.querySelectorAll('[data-sync-pending]').forEach((element) => {
      element.textContent = String(detail.pendingCount)
    })

    document.querySelectorAll('[data-sync-online]').forEach((element) => {
      element.textContent = detail.online ? 'Onlayn' : 'Oflayn'
      element.dataset.state = detail.online ? 'online' : 'offline'
    })

    document.querySelectorAll('[data-sync-error]').forEach((element) => {
      element.textContent = detail.lastError || '-'
    })

    document.querySelectorAll('[data-sync-remote]').forEach((element) => {
      if (!detail.online) {
        element.textContent = 'Oflayn'
      } else if (!detail.remoteChanges) {
        element.textContent = 'Yoxlanır'
      } else if (detail.remoteChanges.total_changes > 0) {
        element.textContent = `${detail.remoteChanges.total_changes} dəyişiklik, səhifəni yeniləyin`
      } else {
        element.textContent = 'Yeni uzaq dəyişiklik yoxdur'
      }
    })

    document.querySelectorAll('[data-sync-pending-list]').forEach((element) => {
      if (!detail.pendingOperations.length) {
        element.innerHTML = 'Gözləyən əməliyyat yoxdur.'
        return
      }

      element.innerHTML = detail.pendingOperations
        .slice(0, 10)
        .map((item) => `<div>${labelForOperation(item)} - ${relativeTimeLabel(item.createdAt)}</div>`)
        .join('')
    })

    document.querySelectorAll('[data-sync-history-list]').forEach((element) => {
      if (!detail.history.length) {
        element.innerHTML = 'Hələ sinxronizasiya tarixçəsi yoxdur.'
        return
      }

      element.innerHTML = detail.history
        .map((item) => {
          const suffix = item.status === 'failed' && item.error ? ` - ${item.error}` : ''
          return `<div>${labelForOperation(item)} - ${item.status} - ${relativeTimeLabel(item.updatedAt)}${suffix}</div>`
        })
        .join('')
    })
  }

  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer()
    const toast = document.createElement('div')
    toast.className = `toast-message toast-${type}`
    toast.innerHTML = `<span class="toast-text">${message}</span>`
    container.appendChild(toast)

    setTimeout(() => {
      toast.style.transition = 'opacity 0.25s ease-out, transform 0.25s ease-out'
      toast.style.opacity = '0'
      toast.style.transform = 'translateY(8px)'
      setTimeout(() => {
        toast.remove()
        if (!container.hasChildNodes()) {
          container.remove()
        }
      }, 300)
    }, 2200)
  }

  function queueToast(message, type = 'info') {
    try {
      sessionStorage.setItem(PENDING_TOAST_KEY, JSON.stringify({ message, type }))
    } catch (error) {}
  }

  function successMessageForAction(action) {
    if (action === 'update') return 'Uğurla yeniləndi.'
    if (action === 'delete') return 'Uğurla silindi.'
    return 'Uğurla əlavə edildi.'
  }

  function createToastContainer() {
    const container = document.createElement('div')
    container.id = 'toast-container'
    document.body.appendChild(container)
    return container
  }

  function scheduleBackgroundTask(callback, timeout = 150) {
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(() => callback(), { timeout })
      return
    }
    window.setTimeout(callback, timeout)
  }

  function serializeForm(form) {
    const formData = new FormData(form)
    const data = {}

    formData.forEach((value, key) => {
      if (key === 'csrfmiddlewaretoken') return
      data[key] = typeof value === 'string' ? value : value.name
    })

    return data
  }

  function resetOfflineForm(form) {
    form.reset()
    form.querySelectorAll('select').forEach((select) => {
      select.dispatchEvent(new Event('change', { bubbles: true }))
    })
  }

  async function fetchServerStatus() {
    if (!navigator.onLine) {
      return emitStatus()
    }

    try {
      const response = await fetch(`${STATUS_URL}?device_id=${encodeURIComponent(getDeviceId())}`, {
        credentials: 'same-origin',
      })
      if (!response.ok) {
        return emitStatus()
      }

      const payload = await response.json()
      if (payload.last_sync) {
        setLastSync(payload.last_sync)
      }
      if (payload.latest_cursor) {
        setLastRemoteCursor(payload.latest_cursor)
      }
      return emitStatus({ lastError: payload.last_error || '' })
    } catch (error) {
      return emitStatus()
    }
  }

  async function fetchPullStatus() {
    if (!navigator.onLine) {
      return null
    }

    let sinceValue = getLastRemoteCursor() || getLastSync() || ''
    if (!sinceValue) {
      await fetchServerStatus()
      sinceValue = getLastRemoteCursor() || getLastSync() || ''
      if (!sinceValue) {
        return {
          has_changes: false,
          total_changes: 0,
          changes: {},
          latest_cursor: null,
        }
      }
      setLastNotifiedRemoteCursor(sinceValue)
    }

    const since = encodeURIComponent(sinceValue)
    const deviceId = encodeURIComponent(getDeviceId())
    try {
      const response = await fetch(`${PULL_STATUS_URL}?since=${since}&device_id=${deviceId}`, {
        credentials: 'same-origin',
      })
      if (!response.ok) {
        return null
      }

      const payload = await response.json()
      if (payload.latest_cursor) {
        setLastRemoteCursor(payload.latest_cursor)
      }

      if (
        payload.has_changes &&
        payload.latest_cursor &&
        payload.latest_cursor !== getLastNotifiedRemoteCursor()
      ) {
        setLastNotifiedRemoteCursor(payload.latest_cursor)
        showToast('Başqa cihazdan yeni dəyişiklik var. Səhifəni yeniləyin.', 'info')
      }

      return payload
    } catch (error) {
      return null
    }
  }

  async function refreshSyncState(options = {}) {
    if (!navigator.onLine) {
      return emitStatus()
    }

    if (!options.skipPendingSync) {
      const operations = await getPendingOperations()
      if (operations.length) {
        return syncPendingOperations(options)
      }
    }

    const remoteChanges = await fetchPullStatus()
    return emitStatus({ remoteChanges })
  }

  function triggerBackgroundSync(options = {}) {
    scheduleBackgroundTask(() => {
      refreshSyncState(options)
    })
  }

  async function syncPendingOperations(options = {}) {
    if (syncInProgress || !navigator.onLine) {
      return { syncedIds: [], failedIds: [] }
    }

    const operations = await getPendingOperations()
    if (!operations.length) {
      const remoteChanges = await fetchPullStatus()
      await emitStatus({ remoteChanges })
      return { syncedIds: [], failedIds: [] }
    }

    syncInProgress = true
    try {
      const response = await fetch(SYNC_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          device_id: getDeviceId(),
          operations: operations.map(({ id, entity, action, data }) => ({ id, entity, action, data })),
        }),
      })

      if (!response.ok) {
        throw new Error('Sync request failed')
      }

      const payload = await response.json()
      const syncedIds = []
      const failedIds = []
      let firstError = payload.last_error || ''

      for (const result of payload.results || []) {
        if (result.status === 'completed') {
          syncedIds.push(result.id)
          await updateOperation(result.id, {
            status: 'completed',
            syncedAt: new Date().toISOString(),
            error: '',
          })
        } else if (result.status === 'failed') {
          failedIds.push(result.id)
          await updateOperation(result.id, {
            status: 'failed',
            error: result.error || 'Sync xətası',
          })
          if (!firstError) {
            firstError = result.error || 'Sync xətası'
          }
        }
      }

      await pruneHistory()

      if (payload.last_sync) {
        setLastSync(payload.last_sync)
      }

      const shouldReload =
        options.reloadOnOperationId &&
        syncedIds.includes(options.reloadOnOperationId) &&
        !options.skipReloadOnSuccess

      if (shouldReload) {
        if (options.successMessage) {
          queueToast(options.successMessage, 'success')
        }
        window.location.reload()
        return { syncedIds, failedIds }
      }

      if (options.skipRemoteStatusRefresh) {
        await emitStatus({ lastError: firstError })
      } else {
        const remoteChanges = await fetchPullStatus()
        await emitStatus({ lastError: firstError, remoteChanges })
      }

      if (failedIds.length) {
        showToast(firstError || 'Bəzi qeydlər sync olmadı.', 'warning')
      } else if (syncedIds.length && !options.silentSuccess) {
        showToast('Məlumat buluda göndərildi.', 'info')
      }

      return { syncedIds, failedIds }
    } catch (error) {
      await emitStatus()
      return { syncedIds: [], failedIds: [] }
    } finally {
      syncInProgress = false
    }
  }

  async function handleSyncFormSubmit(event) {
    const form = event.target
    if (!(form instanceof HTMLFormElement) || !form.matches('form[data-sync-entity]')) {
      return
    }

    event.preventDefault()

    const submitButton = event.submitter
    if (submitButton) {
      submitButton.disabled = true
    }

    const operationId = generateId()
    const operation = {
      id: operationId,
      entity: form.dataset.syncEntity,
      action: form.dataset.syncAction || 'create',
      data: serializeForm(form),
      createdAt: new Date().toISOString(),
    }

    try {
      await addOperation(operation)

      if (form.dataset.syncRedirectAfterQueue) {
        if (form.dataset.syncKeepKey) {
          sessionStorage.removeItem(form.dataset.syncKeepKey)
        }
        if (form.dataset.syncReset !== 'false') {
          resetOfflineForm(form)
        }
        emitStatus()
        if (navigator.onLine) {
          syncPendingOperations({ silentSuccess: true })
        }
        window.location.assign(form.dataset.syncRedirectAfterQueue)
        return
      }

      if (form.dataset.syncKeepKey) {
        sessionStorage.removeItem(form.dataset.syncKeepKey)
      }

      if (form.dataset.syncReset !== 'false') {
        resetOfflineForm(form)
      }

      if (!navigator.onLine) {
        showToast('Offline saxlanıldı. İnternet gələndə göndəriləcək.', 'warning')
        await emitStatus()
        return
      }

      await emitStatus()

      syncPendingOperations({
        reloadOnOperationId: operationId,
        skipReloadOnSuccess: Boolean(form.dataset.syncSuccessRedirect),
        silentSuccess: true,
        skipRemoteStatusRefresh: true,
        successMessage: successMessageForAction(operation.action),
      }).then((result) => {
        if (result.failedIds.includes(operationId)) {
          showToast('Məlumat yoxlamadan keçmədi.', 'error')
          return
        }
        if (result.syncedIds.includes(operationId) && form.dataset.syncSuccessRedirect) {
          queueToast(successMessageForAction(operation.action), 'success')
          window.location.assign(form.dataset.syncSuccessRedirect)
          return
        }
        if (result.syncedIds.includes(operationId)) {
          showToast(successMessageForAction(operation.action), 'success')
        }
      }).catch(() => {
        showToast('Şəbəkə problemi var. Məlumat lokal saxlanıldı.', 'warning')
      })
      return
    } catch (error) {
      showToast('Offline queue yazılmadı.', 'error')
    } finally {
      if (submitButton) {
        submitButton.disabled = false
      }
    }
  }

  function bindSyncPageActions() {
    const button = document.querySelector('[data-sync-now]')
    if (!button) return

    button.addEventListener('click', async () => {
      button.disabled = true
      await syncPendingOperations()
      button.disabled = false
    })
  }

  async function initialize() {
    getDeviceId()
    bindSyncPageActions()
    document.addEventListener('submit', handleSyncFormSubmit)
    window.addEventListener('online', () => {
      emitStatus()
      triggerBackgroundSync({ silentSuccess: true })
    })
    window.addEventListener('offline', () => emitStatus())
    setInterval(() => {
      if (navigator.onLine) {
        triggerBackgroundSync({ silentSuccess: true })
      } else {
        emitStatus()
      }
    }, RETRY_INTERVAL_MS)

    await emitStatus()
    if (navigator.onLine) {
      triggerBackgroundSync({ silentSuccess: true })
    }
  }

  window.farmSync = {
    fetchServerStatus,
    getDeviceId,
    getPendingCount,
    syncNow: () => syncPendingOperations(),
  }

  initialize()
})()
