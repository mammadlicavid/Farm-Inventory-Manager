{% load i18n common_extras static %}
        ;(function () {
          window.createProgressiveListController = function ({ items, batchSize = 100, sentinelClassName = 'progressive-list-sentinel' }) {
            const listItems = Array.isArray(items) ? items.filter(Boolean) : []
            if (!listItems.length) {
              return {
                refresh() {},
                loadMore() {},
              }
            }

            const container = listItems[0].parentElement
            if (!container || container.dataset.progressiveReady === '1') {
              return {
                refresh() {
                  const matchedItems = listItems.filter((item) => item.dataset.filterMatch !== '0')
                  matchedItems.forEach((item) => {
                    item.style.display = ''
                  })
                  listItems
                    .filter((item) => item.dataset.filterMatch === '0')
                    .forEach((item) => {
                      item.style.display = 'none'
                    })
                },
                loadMore() {},
              }
            }

            container.dataset.progressiveReady = '1'

            let revealedCount = batchSize
            const sentinel = document.createElement('div')
            sentinel.className = sentinelClassName
            sentinel.style.width = '100%'
            sentinel.style.height = '1px'
            sentinel.style.pointerEvents = 'none'
            container.insertAdjacentElement('afterend', sentinel)

            function matchedItems() {
              return listItems.filter((item) => item.dataset.filterMatch !== '0')
            }

            function render() {
              const active = matchedItems()
              listItems.forEach((item) => {
                item.style.display = 'none'
              })
              active.forEach((item, index) => {
                item.style.display = index < revealedCount ? '' : 'none'
              })
              sentinel.style.display = active.length > revealedCount ? 'block' : 'none'
            }

            function refresh(reset = true) {
              if (reset) {
                revealedCount = batchSize
              }
              render()
            }

            function loadMore() {
              const active = matchedItems()
              if (revealedCount >= active.length) return
              revealedCount += batchSize
              render()
            }

            if ('IntersectionObserver' in window) {
              const observer = new IntersectionObserver(
                (entries) => {
                  entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                      loadMore()
                    }
                  })
                },
                { rootMargin: '320px 0px' }
              )
              observer.observe(sentinel)
            } else {
              window.addEventListener('scroll', loadMore, { passive: true })
            }

            return { refresh, loadMore }
          }
        })()
