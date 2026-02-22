(function () {
  const el = document.getElementById("reportsTrendChart");
  if (!el) return;

  const raw = document.getElementById("reportsData");
  if (!raw) return;

  let data;
  try {
    data = JSON.parse(raw.textContent);
  } catch (e) {
    return;
  }

  const values = (data.values || []).map(Number);
  if (!values.length) return;

  const canvas = el;
  const ctx = canvas.getContext("2d");

  const w = canvas.width = canvas.parentElement.clientWidth - 24;
  const h = canvas.height;

  const pad = 12;
  const maxV = Math.max(...values);
  const minV = Math.min(...values);
  const range = (maxV - minV) || 1;

  function x(i) {
    if (values.length === 1) return pad;
    return pad + (i * (w - pad * 2)) / (values.length - 1);
  }

  function y(v) {
    return pad + (h - pad * 2) * (1 - (v - minV) / range);
  }

  ctx.clearRect(0, 0, w, h);

  // grid line
  ctx.globalAlpha = 0.25;
  ctx.beginPath();
  ctx.moveTo(pad, h - pad);
  ctx.lineTo(w - pad, h - pad);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // line
  ctx.beginPath();
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";

  values.forEach((v, i) => {
    const px = x(i);
    const py = y(v);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.stroke();

  // points
  values.forEach((v, i) => {
    const px = x(i);
    const py = y(v);
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, Math.PI * 2);
    ctx.fill();
  });
})();