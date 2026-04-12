(function () {
  const canvas = document.getElementById('reportsTrendChart')
  const payloadNode = document.getElementById('reportsTrendData')
  const focusLabel = document.getElementById('reportsChartFocusLabel')
  const focusIncome = document.getElementById('reportsChartFocusIncome')
  const focusExpense = document.getElementById('reportsChartFocusExpense')
  const focusNet = document.getElementById('reportsChartFocusNet')
  const focusTax = document.getElementById('reportsChartFocusTax')
  const toggleButtons = Array.from(document.querySelectorAll('[data-series-toggle]'))

  if (!canvas || !payloadNode) return

  let chartData
  try {
    chartData = JSON.parse(payloadNode.textContent)
  } catch (error) {
    console.error('reportsTrendData JSON parse error', error)
    return
  }

  const points = Array.isArray(chartData.points) ? chartData.points : []
  if (!points.length) return

  const ctx = canvas.getContext('2d')
  const currencySymbol = canvas.dataset.currencySymbol || '₼'
  const usesSuffixCurrency = currencySymbol === '₼'

  const seriesConfig = {
    income: { color: '#16a34a', soft: 'rgba(22, 163, 74, 0.12)', label: 'income' },
    expense: { color: '#ea580c', soft: 'rgba(234, 88, 12, 0.12)', label: 'expense' },
    net: { color: '#2563eb', soft: 'rgba(37, 99, 235, 0.12)', label: 'net' },
  }

  const activeSeries = {
    income: true,
    expense: true,
    net: true,
  }

  let hoverIndex = Math.max(0, points.length - 1)

  function formatNumber(value) {
    const amount = Number(value || 0)
    return amount.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  function formatMoney(value, prefix = '') {
    const text = formatNumber(value)
    return usesSuffixCurrency ? `${prefix}${text}${currencySymbol}` : `${prefix}${currencySymbol}${text}`
  }

  function updateFocus(point) {
    if (!point) return
    if (focusLabel) focusLabel.textContent = point.label
    if (focusIncome) focusIncome.textContent = formatMoney(point.income, '+')
    if (focusExpense) focusExpense.textContent = formatMoney(point.expense, '-')
    if (focusNet) {
      const netPrefix = Number(point.net) >= 0 ? '+' : ''
      focusNet.textContent = formatMoney(point.net, netPrefix)
    }
    if (focusTax) focusTax.textContent = formatMoney(point.tax)
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect()
    const ratio = window.devicePixelRatio || 1
    canvas.width = Math.max(1, Math.floor(rect.width * ratio))
    canvas.height = Math.max(1, Math.floor(rect.height * ratio))
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  }

  function visibleKeys() {
    return Object.keys(activeSeries).filter((key) => activeSeries[key])
  }

  function visibleValues() {
    const values = [0]
    visibleKeys().forEach((key) => {
      points.forEach((point) => values.push(Number(point[key] || 0)))
    })
    return values
  }

  function yFor(value, frame) {
    const range = frame.maxValue - frame.minValue || 1
    return frame.top + ((frame.maxValue - value) / range) * frame.chartHeight
  }

  function drawGrid(frame) {
    const gridCount = 5
    const range = frame.maxValue - frame.minValue || 1

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)'
    ctx.lineWidth = 1
    ctx.fillStyle = '#64748b'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'

    for (let index = 0; index <= gridCount; index += 1) {
      const y = frame.top + (frame.chartHeight / gridCount) * index
      const value = frame.maxValue - (range / gridCount) * index
      ctx.beginPath()
      ctx.moveTo(frame.left, y)
      ctx.lineTo(frame.right, y)
      ctx.stroke()
      ctx.fillText(formatMoney(value), frame.left - 10, y + 4)
    }
  }

  function roundedRect(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2)
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.arcTo(x + width, y, x + width, y + height, r)
    ctx.arcTo(x + width, y + height, x, y + height, r)
    ctx.arcTo(x, y + height, x, y, r)
    ctx.arcTo(x, y, x + width, y, r)
    ctx.closePath()
  }

  function drawZeroLine(frame) {
    if (frame.minValue > 0 || frame.maxValue < 0) return
    const zeroY = yFor(0, frame)
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.16)'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(frame.left, zeroY)
    ctx.lineTo(frame.right, zeroY)
    ctx.stroke()
    ctx.setLineDash([])
  }

  function drawPeriodGuides(frame) {
    const groupWidth = frame.chartWidth / Math.max(points.length, 1)
    const labelStep = Math.max(1, Math.ceil(points.length / 7))

    ctx.save()
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)'
    ctx.lineWidth = 1
    ctx.setLineDash([3, 6])

    points.forEach((point, index) => {
      if (index % labelStep !== 0 && index !== points.length - 1 && index !== hoverIndex) return
      const x = frame.left + groupWidth * index + groupWidth / 2
      ctx.beginPath()
      ctx.moveTo(x, frame.top)
      ctx.lineTo(x, frame.bottom)
      ctx.stroke()
    })

    ctx.restore()
  }

  function drawLabels(frame) {
    const groupWidth = frame.chartWidth / Math.max(points.length, 1)
    const labelStep = Math.max(1, Math.ceil(points.length / 7))

    ctx.save()
    ctx.fillStyle = '#64748b'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'center'

    function labelLines(label) {
      const text = String(label || '').trim()
      if (!text) return ['']
      if (text.includes(' - ')) {
        const [start, end] = text.split(' - ', 2)
        return [start, end]
      }
      const parts = text.split(/\s+/)
      if (parts.length === 2) return parts
      if (parts.length > 2) return [parts.slice(0, -1).join(' '), parts.at(-1)]
      return [text]
    }

    points.forEach((point, index) => {
      if (index % labelStep !== 0 && index !== points.length - 1) return
      const x = frame.left + groupWidth * index + groupWidth / 2
      const lines = labelLines(point.label)
      const widths = lines.map((line) => ctx.measureText(line).width)
      const boxWidth = Math.max(...widths, 36) + 12
      const boxHeight = lines.length * 14 + 8
      const boxX = x - boxWidth / 2
      const boxY = frame.bottom + 6

      ctx.save()
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
      ctx.strokeStyle = 'rgba(226, 232, 240, 0.92)'
      ctx.lineWidth = 1
      roundedRect(boxX, boxY, boxWidth, boxHeight, 10)
      ctx.fill()
      ctx.stroke()
      ctx.restore()

      lines.forEach((line, lineIndex) => {
        ctx.fillText(line, x, boxY + 14 + lineIndex * 14)
      })
    })

    ctx.restore()
  }

  function drawBars(frame) {
    const activeKeys = visibleKeys()
    const groupWidth = frame.chartWidth / Math.max(points.length, 1)
    const barAreaWidth = Math.min(64, groupWidth * 0.78)
    const barWidth = Math.max(12, Math.min(20, barAreaWidth / Math.max(activeKeys.length, 1) - 6))
    const totalBarsWidth = activeKeys.length * barWidth + Math.max(activeKeys.length - 1, 0) * 6
    const zeroY = yFor(0, frame)

    points.forEach((point, index) => {
      const groupLeft = frame.left + groupWidth * index
      const centerX = groupLeft + groupWidth / 2
      const startX = centerX - totalBarsWidth / 2

      if (index === hoverIndex) {
        ctx.fillStyle = 'rgba(15, 23, 42, 0.04)'
        ctx.fillRect(groupLeft + 4, frame.top, Math.max(groupWidth - 8, 0), frame.chartHeight)
      }

      activeKeys.forEach((key, keyIndex) => {
        const value = Number(point[key] || 0)
        const config = seriesConfig[key]
        const x = startX + keyIndex * (barWidth + 6)
        const targetY = yFor(value, frame)
        const y = Math.min(zeroY, targetY)
        const height = Math.max(Math.abs(zeroY - targetY), 2)
        const radius = Math.min(8, barWidth / 2)

        ctx.fillStyle = config.soft
        ctx.fillRect(x, y, barWidth, height)

        ctx.fillStyle = config.color
        ctx.beginPath()
        ctx.moveTo(x, y + radius)
        ctx.arcTo(x, y, x + radius, y, radius)
        ctx.arcTo(x + barWidth, y, x + barWidth, y + radius, radius)
        ctx.lineTo(x + barWidth, y + height)
        ctx.lineTo(x, y + height)
        ctx.closePath()
        ctx.fill()

        if (index === hoverIndex) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.86)'
          ctx.lineWidth = 2
          ctx.stroke()
        }
      })
    })
  }

  function draw() {
    resizeCanvas()

    const width = canvas.clientWidth
    const height = canvas.clientHeight
    ctx.clearRect(0, 0, width, height)

    const padding = {
      top: 20,
      right: 18,
      bottom: 74,
      left: 86,
    }

    const values = visibleValues()
    const min = Math.min(...values, 0)
    const max = Math.max(...values, 0)
    const spread = max - min || 1
    const margin = Math.max(spread * 0.18, 20)

    const frame = {
      left: padding.left,
      right: width - padding.right,
      top: padding.top,
      bottom: height - padding.bottom,
      chartWidth: width - padding.left - padding.right,
      chartHeight: height - padding.top - padding.bottom,
      minValue: min - (min < 0 ? margin * 0.5 : 0),
      maxValue: max + margin,
    }

    drawGrid(frame)
    drawZeroLine(frame)
    drawPeriodGuides(frame)
    drawBars(frame)
    drawLabels(frame)
    updateFocus(points[hoverIndex] || points[points.length - 1])
  }

  function nearestIndex(clientX) {
    const rect = canvas.getBoundingClientRect()
    const left = 86
    const right = rect.width - 18
    const chartWidth = right - left
    const relativeX = clientX - rect.left - left
    const groupWidth = chartWidth / Math.max(points.length, 1)
    const rawIndex = Math.floor(relativeX / groupWidth)
    return Math.min(points.length - 1, Math.max(0, rawIndex))
  }

  canvas.addEventListener('mousemove', (event) => {
    hoverIndex = nearestIndex(event.clientX)
    draw()
  })

  canvas.addEventListener('mouseleave', () => {
    hoverIndex = Math.max(0, points.length - 1)
    draw()
  })

  toggleButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const key = button.dataset.seriesToggle
      if (!key || !(key in activeSeries)) return

      activeSeries[key] = !activeSeries[key]
      button.classList.toggle('is-active', activeSeries[key])

      if (!Object.values(activeSeries).some(Boolean)) {
        activeSeries[key] = true
        button.classList.add('is-active')
      }

      draw()
    })
  })

  window.addEventListener('resize', draw)
  draw()
})()
