(function () {
  const picker = document.getElementById('calendar-month-picker')
  const input = document.getElementById('calendar-month-input')

  if (!picker || !input) return

  input.addEventListener('change', () => {
    if (!input.value) return
    picker.requestSubmit()
  })
})()
