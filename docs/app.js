/* Load dashboard.json and render the indicator tiles and sources. */

"use strict";

const STALE_AFTER_DAYS = 4;

const $ = (sel) => document.querySelector(sel);

function text(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}

function banner(message, kind) {
  const b = $("#banner");
  b.textContent = message;
  b.className = `banner ${kind}`;
  b.hidden = false;
}

/* ------------------------------------------------------------------ tiles */

function renderTile(ind) {
  const decimals = ind.key === "fed_funds" ? 2 : 1;
  const fmt = (v) => `${(+v).toFixed(decimals)}%`;

  const tile = text("div", "tile");

  // Stretched link: covers the card and opens the FRED series page. The
  // sparkline sits above it (z-index) so hover/tap there still reads values.
  const link = text("a", "tile-link");
  link.href = ind.source.fred_url;
  link.target = "_blank";
  link.rel = "noopener";
  link.setAttribute("aria-label",
    `${ind.label}: open the full series at FRED (new tab)`);
  tile.appendChild(link);

  const label = text("div", "tile-label", ind.label);
  label.appendChild(text("span", "tile-ext", " ↗"));
  tile.appendChild(label);

  tile.appendChild(text("div", "tile-value", ind.value_display));

  const delta = text("div", "tile-delta");
  const arrow = { up: "▲", down: "▼", flat: "–" }[ind.direction];
  const word = { up: "up", down: "down", flat: "unchanged" }[ind.direction];
  delta.appendChild(text("span", "tile-arrow", arrow));
  delta.appendChild(text("span", "sr-only", word + " "));
  const amt = ind.direction === "flat" ? "" :
    `${Math.abs(ind.change).toFixed(decimals)} ${ind.change_units} `;
  delta.appendChild(document.createTextNode(` ${amt}${ind.change_label}`));
  tile.appendChild(delta);

  const sparkBox = text("div", "tile-spark");
  tile.appendChild(sparkBox);

  tile.appendChild(text("div", "tile-asof",
    `${ind.period_label} · ${ind.source.origin}`));

  if (ind.status === "stale") {
    tile.appendChild(text("div", "tile-stale",
      "Update failed — showing the last good data."));
  }

  tile.appendChild(text("div", "tile-plain", ind.plain_language));
  $("#tiles").appendChild(tile);

  const span = ind.history_cadence === "quarterly"
    ? "last 2 years, quarterly" : "last 2 years, monthly";
  requestAnimationFrame(() => Charts.spark(sparkBox, {
    points: ind.spark,
    color: "var(--series-1)",
    format: fmt,
    name: `${ind.label}, ${span}`,
  }));
}

/* -------------------------------------------------------------------- main */

async function main() {
  let data;
  try {
    const cacheBust = Math.floor(Date.now() / 6e5); // new URL every 10 minutes
    const resp = await fetch(`data/dashboard.json?t=${cacheBust}`, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    data = await resp.json();
  } catch (err) {
    banner("The dashboard data could not be loaded. Please try again later.", "error");
    return;
  }

  const generated = new Date(data.generated_at_utc);
  $("#updated").textContent = "Updated " + generated.toLocaleDateString(undefined,
    { year: "numeric", month: "long", day: "numeric" });

  const ageDays = (Date.now() - generated.getTime()) / 86400e3;
  if (ageDays > STALE_AFTER_DAYS) {
    banner(`Data last updated ${generated.toLocaleDateString()}. ` +
      "It may be out of date.", "warn");
  } else if (data.indicators.some((i) => i.status === "stale")) {
    banner("Some series failed to update. Those tiles show the last good data.", "warn");
  }

  data.indicators.forEach(renderTile);
}

main();
