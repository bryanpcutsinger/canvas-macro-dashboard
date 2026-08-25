/* Hand-rolled SVG sparklines with a hover/keyboard readout of past values.
   No dependencies. All colors come from CSS custom properties. */

"use strict";

const Charts = (() => {
  const NS = "http://www.w3.org/2000/svg";

  const ms = (d) => Date.parse(d + "T00:00:00Z");

  function el(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
  }

  function periodLabel(d) {
    return new Date(ms(d)).toLocaleDateString(undefined,
      { year: "numeric", month: "short", timeZone: "UTC" });
  }

  /* Interactive trend line for a stat tile. Hover or focus + arrow keys read
     past values; the crosshair snaps to the nearest observation. */
  function spark(container, opts) {
    const { points, color, format, name } = opts;
    container.textContent = "";
    container.classList.add("spark");
    container.tabIndex = 0;
    container.setAttribute("role", "img");

    const vs = points.map((p) => p.v);
    container.setAttribute("aria-label",
      `${name}, ${periodLabel(points[0].d)} to ${periodLabel(points[points.length - 1].d)}: ` +
      `low ${format(Math.min(...vs))}, high ${format(Math.max(...vs))}, ` +
      `latest ${format(vs[vs.length - 1])}. ` +
      "Use the left and right arrow keys to read each value.");

    const readout = document.createElement("div");
    readout.className = "spark-readout";
    readout.setAttribute("aria-hidden", "true");
    container.appendChild(readout);

    let activeIndex = null;

    function render() {
      // Keep the readout; rebuild only the SVG.
      container.querySelectorAll("svg").forEach((s) => s.remove());
      const w = container.clientWidth || 140, h = 44, pad = 5;
      const svg = el("svg", {
        viewBox: `0 0 ${w} ${h}`, width: w, height: h, "aria-hidden": "true",
      }, container);
      const xs = points.map((p) => ms(p.d));
      const [x0, x1] = [xs[0], xs[xs.length - 1]];
      const [v0, v1] = [Math.min(...vs), Math.max(...vs)];
      const X = (t) => pad + ((t - x0) / (x1 - x0 || 1)) * (w - 2 * pad);
      const Y = (v) => h - pad - ((v - v0) / (v1 - v0 || 1)) * (h - 2 * pad);

      const d = points.map((p, i) =>
        `${i ? "L" : "M"}${X(ms(p.d)).toFixed(1)},${Y(p.v).toFixed(1)}`).join("");
      el("path", { d, fill: "none", stroke: color, "stroke-width": 1.5,
        "stroke-linejoin": "round", "stroke-linecap": "round", opacity: 0.55 }, svg);
      const last = points[points.length - 1];
      el("circle", { cx: X(ms(last.d)).toFixed(1), cy: Y(last.v).toFixed(1), r: 3,
        fill: color, stroke: "var(--surface-1)", "stroke-width": 2 }, svg);

      // Crosshair + highlight dot, drawn on demand.
      const cross = el("line", { y1: 0, y2: h, stroke: "var(--baseline)",
        "stroke-width": 1, visibility: "hidden" }, svg);
      const dot = el("circle", { r: 3.5, fill: color,
        stroke: "var(--surface-1)", "stroke-width": 2, visibility: "hidden" }, svg);

      function show(i) {
        activeIndex = Math.max(0, Math.min(points.length - 1, i));
        const p = points[activeIndex];
        const x = X(ms(p.d));
        cross.setAttribute("x1", x); cross.setAttribute("x2", x);
        cross.setAttribute("visibility", "visible");
        dot.setAttribute("cx", x); dot.setAttribute("cy", Y(p.v));
        dot.setAttribute("visibility", "visible");
        readout.textContent = "";
        const val = document.createElement("strong");
        val.textContent = format(p.v);
        const when = document.createElement("span");
        when.textContent = " " + periodLabel(p.d);
        readout.append(val, when);
        readout.style.display = "block";
        // Keep the readout inside the tile: flip sides at the midpoint.
        if (x > w / 2) { readout.style.left = ""; readout.style.right = `${w - x + 8}px`; }
        else { readout.style.right = ""; readout.style.left = `${x + 8}px`; }
      }

      function hide() {
        activeIndex = null;
        cross.setAttribute("visibility", "hidden");
        dot.setAttribute("visibility", "hidden");
        readout.style.display = "none";
      }

      // The whole sparkline is the hit target — no pinpoint aiming.
      svg.addEventListener("pointermove", (ev) => {
        const rect = svg.getBoundingClientRect();
        const t = x0 + ((ev.clientX - rect.left) / rect.width) * (x1 - x0);
        let best = 0;
        for (let i = 1; i < xs.length; i++) {
          if (Math.abs(xs[i] - t) < Math.abs(xs[best] - t)) best = i;
        }
        show(best);
      });
      svg.addEventListener("pointerleave", hide);
      container.onkeydown = (ev) => {
        const step = { ArrowLeft: -1, ArrowRight: 1 }[ev.key];
        if (step) {
          show((activeIndex === null ? points.length - 1 : activeIndex) + step);
          ev.preventDefault();
        } else if (ev.key === "Home") { show(0); ev.preventDefault(); }
        else if (ev.key === "End") { show(points.length - 1); ev.preventDefault(); }
        else if (ev.key === "Escape") hide();
      };
      container.onblur = hide;
    }

    let raf = null;
    new ResizeObserver(() => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(render);
    }).observe(container);
    render();
  }

  return { spark };
})();
