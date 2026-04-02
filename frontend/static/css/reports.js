(function () {
  const canvas = document.getElementById("reportsCategoryChart");
  const raw = document.getElementById("reportsData");

  if (!canvas || !raw) return;

  let data;
  try {
    data = JSON.parse(raw.textContent);
  } catch (e) {
    console.error("reportsData JSON error", e);
    return;
  }

  const labels = Array.isArray(data.labels) ? data.labels : [];
  const values = Array.isArray(data.values) ? data.values.map(Number) : [];

  if (!labels.length || !values.length) return;

  const ctx = canvas.getContext("2d");

  function formatValue(v) {
    return `${v.toFixed(2)}₼`;
  }

  function resizeCanvas() {
    const parent = canvas.parentElement;
    if (!parent) return;

    const rect = parent.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;

    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    canvas.width = Math.floor(rect.width * ratio);
    canvas.height = Math.floor(rect.height * ratio);

    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function draw() {
    resizeCanvas();

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    ctx.clearRect(0, 0, width, height);

    const rootStyles = getComputedStyle(document.documentElement);
    const barColor = rootStyles.getPropertyValue("--primary-green").trim() || "#2E8B57";
    const gridColor = "rgba(0,0,0,0.08)";
    const textColor = "#5b6b84";
    const axisColor = "#94a3b8";

    const padTop = 24;
    const padRight = 20;
    const padBottom = 70;
    const padLeft = 50;

    const chartW = width - padLeft - padRight;
    const chartH = height - padTop - padBottom;

    const maxValue = Math.max(...values, 0);
    const safeMax = maxValue === 0 ? 100 : maxValue * 1.15;

    const gridLines = 5;

    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;

    for (let i = 0; i <= gridLines; i++) {
      const y = padTop + (chartH / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();

      const gridValue = safeMax - (safeMax / gridLines) * i;
      ctx.fillStyle = axisColor;
      ctx.font = "11px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(formatValue(gridValue), padLeft - 8, y + 4);
    }

    const count = values.length;
    const slotWidth = chartW / count;
    const barWidth = Math.min(56, slotWidth * 0.55);

    values.forEach((value, i) => {
      const barHeight = (value / safeMax) * chartH;
      const x = padLeft + i * slotWidth + (slotWidth - barWidth) / 2;
      const y = padTop + chartH - barHeight;

      ctx.fillStyle = barColor;
      roundRect(ctx, x, y, barWidth, barHeight, 12);
      ctx.fill();

      ctx.fillStyle = textColor;
      ctx.font = "600 11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(formatValue(value), x + barWidth / 2, y - 8);

      ctx.save();
      ctx.translate(x + barWidth / 2, padTop + chartH + 18);
      ctx.rotate(-0.35);
      ctx.fillStyle = textColor;
      ctx.font = "600 12px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(labels[i], 0, 0);
      ctx.restore();
    });
  }

  function roundRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height);
    ctx.lineTo(x, y + height);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  draw();
  window.addEventListener("resize", draw);
})();