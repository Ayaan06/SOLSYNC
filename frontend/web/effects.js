// Background particle glow effect (lightweight)
(function () {
  const canvas = document.getElementById('bgfx');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, dpr;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth = window.innerWidth;
    h = canvas.clientHeight = window.innerHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  window.addEventListener('resize', resize);
  resize();

  // Fewer, softer particles for a subtler background
  const N = 40;
  const pts = new Array(N).fill(0).map(() => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: 1.0 + Math.random() * 2.0,
    a: 0.10 + Math.random() * 0.12,
    vx: (Math.random() - 0.5) * 0.18,
    vy: (Math.random() - 0.5) * 0.18,
    hue: 160 + Math.random() * 80 // teal to blue
  }));

  function step() {
    ctx.clearRect(0, 0, w, h);

    for (const p of pts) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < -50) p.x = w + 50; else if (p.x > w + 50) p.x = -50;
      if (p.y < -50) p.y = h + 50; else if (p.y > h + 50) p.y = -50;

      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 14);
      grad.addColorStop(0, `hsla(${p.hue}, 100%, 60%, ${p.a})`);
      grad.addColorStop(1, 'hsla(0, 0%, 0%, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 8, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(step);
  }

  step();
})();
