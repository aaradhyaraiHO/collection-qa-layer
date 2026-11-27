/* Inline SVG charts. No network. */
var Charts = (() => {
  const LIKERT = ["#c45c5c", "#e09a4a", "#e4d27a", "#7db87a", "#2f7d57"];

  function el(name, attrs, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
    if (text != null) node.textContent = text;
    return node;
  }

  function stacked(pmf, width = 220, height = 14) {
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img" });
    let x = 0;
    (pmf || []).forEach((share, index) => {
      const w = Math.max(0, Number(share) || 0) * width;
      const rect = el("rect", { x: x.toFixed(2), y: 0, width: w.toFixed(2), height, fill: LIKERT[index] });
      const title = el("title", {}, `${index + 1}: ${Math.round((Number(share) || 0) * 100)}%`);
      rect.append(title);
      svg.append(rect);
      x += w;
    });
    return svg;
  }

  function bars(rows, { value = "mean", label = "title", max = 5, color = "#8000ff", height = 22 } = {}) {
    const width = 640;
    const svg = el("svg", {
      viewBox: `0 0 ${width} ${Math.max(rows.length, 1) * (height + 8) + 8}`,
      width: "100%",
      role: "img",
    });
    rows.forEach((row, index) => {
      const y = index * (height + 8) + 4;
      const amount = Math.max(0, Number(row[value]) || 0);
      const bar = (amount / max) * (width - 280);
      svg.append(el("text", { x: 0, y: y + 15, "font-size": 12, fill: "#1b1226" }, String(row[label] || "").slice(0, 36)));
      svg.append(el("rect", { x: 250, y, width: bar.toFixed(1), height: height - 4, rx: 4, fill: color }));
      svg.append(el("text", { x: 256 + bar, y: y + 14, "font-size": 12, fill: "#5e5670" }, amount.toFixed(2)));
    });
    return svg;
  }

  function heatmap(spec) {
    const columns = spec.columns || [];
    const rows = spec.rows || [];
    if (!rows.length || !columns.length) return document.createElement("p");
    const labelW = 128;
    const cellW = 78;
    const cellH = 42;
    const headerH = 128;
    const width = labelW + columns.length * cellW + 12;
    const height = headerH + rows.length * cellH + 8;
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", role: "img" });
    columns.forEach((column, index) => {
      const x = labelW + index * cellW + 6;
      const y = headerH - 10;
      svg.append(el("text", {
        x,
        y,
        "font-size": 11,
        fill: "#5e5670",
        transform: `rotate(-58 ${x} ${y})`,
      }, String(column.title || "").slice(0, 28)));
    });
    rows.forEach((row, rowIndex) => {
      const y = headerH + rowIndex * cellH;
      svg.append(el("text", { x: 0, y: y + 20, "font-size": 12, fill: "#1b1226" }, row.label));
      row.cells.forEach((cell, colIndex) => {
        const mean = cell.mean == null ? 3 : Number(cell.mean);
        const tint = heatColor(mean);
        const rect = el("rect", {
          x: labelW + colIndex * cellW,
          y,
          width: cellW - 4,
          height: cellH - 6,
          rx: 6,
          fill: tint,
          opacity: cell.faded ? 0.35 : 1,
        });
        rect.append(el("title", {}, `${row.label}: ${cell.mean == null ? "n/a" : cell.mean} (n=${cell.n})`));
        svg.append(rect);
        svg.append(el("text", {
          x: labelW + colIndex * cellW + (cellW - 4) / 2,
          y: y + 18,
          "text-anchor": "middle",
          "font-size": 11,
          fill: "#1b1226",
          opacity: cell.faded ? 0.55 : 1,
        }, cell.mean == null ? "—" : Number(cell.mean).toFixed(2)));
      });
    });
    return svg;
  }

  function heatColor(mean) {
    const t = Math.max(0, Math.min(1, (mean - 3.0) / 0.7));
    const r = Math.round(232 + (128 - 232) * t);
    const g = Math.round(224 + (0 - 224) * t);
    const b = Math.round(214 + (255 - 214) * t);
    return `rgb(${r},${g},${b})`;
  }

  function dots(items) {
    if (!items.length) return document.createElement("p");
    const width = 720;
    const rowH = 28;
    const left = 210;
    const height = items.length * rowH + 28;
    const means = items.map((item) => Number(item.mean));
    const min = Math.min(...means) - 0.08;
    const max = Math.max(...means) + 0.08;
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", role: "img" });
    [3.2, 3.4, 3.6].filter((mark) => mark > min && mark < max).forEach((mark) => {
      const x = left + ((mark - min) / (max - min)) * (width - left - 20);
      svg.append(el("line", { x1: x, x2: x, y1: 8, y2: height - 8, stroke: "#e6e1ef" }));
      svg.append(el("text", { x, y: height - 2, "font-size": 10, fill: "#5e5670", "text-anchor": "middle" }, String(mark)));
    });
    items.forEach((item, index) => {
      const y = 16 + index * rowH;
      const x = left + ((Number(item.mean) - min) / (max - min)) * (width - left - 20);
      svg.append(el("text", { x: 0, y: y + 4, "font-size": 12, fill: "#1b1226" }, `${item.axis}: ${item.label}`.slice(0, 28)));
      const dot = el("circle", {
        cx: x.toFixed(1),
        cy: y,
        r: item.faded ? 5 : 7,
        fill: "#8000ff",
        opacity: item.faded ? 0.35 : 0.9,
      });
      dot.append(el("title", {}, `${item.label} ${item.mean} (n=${item.n})`));
      svg.append(dot);
    });
    return svg;
  }

  function stability(trust) {
    const points = trust.points || [];
    const width = 680;
    const height = 220;
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", role: "img" });
    const values = points.map((point) => Number(point.page)).filter((value) => !Number.isNaN(value));
    const base = Number(trust.page_base);
    const low = Math.min(base || 3.2, ...(values.length ? values : [3.2])) - 0.05;
    const high = Math.max(base || 3.4, ...(values.length ? values : [3.4])) + 0.05;
    const left = 36;
    const plotW = width - left - 12;
    const yOf = (value) => 20 + ((high - value) / Math.max(high - low, 0.05)) * 160;
    if (!Number.isNaN(base)) {
      const y = yOf(base);
      svg.append(el("rect", { x: left, y: yOf(base + 0.05), width: plotW, height: Math.max(2, yOf(base - 0.05) - yOf(base + 0.05)), fill: "#f3e8ff" }));
      svg.append(el("line", { x1: left, x2: left + plotW, y1: y, y2: y, stroke: "#8000ff", "stroke-dasharray": "4 3" }));
    }
    points.forEach((point, index) => {
      if (point.page == null) return;
      const x = left + ((index + 0.5) / Math.max(points.length, 1)) * plotW;
      const moved = Math.abs(Number(point.delta) || 0) > 0.05;
      svg.append(el("circle", { cx: x.toFixed(1), cy: yOf(point.page).toFixed(1), r: 5, fill: moved ? "#8a5a00" : "#2f7d57" }));
    });
    svg.append(el("text", { x: 8, y: 16, "font-size": 11, fill: "#5e5670" }, high.toFixed(2)));
    svg.append(el("text", { x: 8, y: 190, "font-size": 11, fill: "#5e5670" }, low.toFixed(2)));
    return svg;
  }

  function counts(checks) {
    const rows = [
      { title: "Pass", mean: checks.pass || 0 },
      { title: "Warn", mean: checks.warn || 0 },
      { title: "Fail", mean: checks.fail || 0 },
    ];
    const max = Math.max(1, ...rows.map((row) => row.mean));
    const colors = { Pass: "#2f7d57", Warn: "#8a5a00", Fail: "#8d1d1d" };
    const svg = el("svg", { viewBox: "0 0 420 110", width: "100%", role: "img" });
    rows.forEach((row, index) => {
      const y = 12 + index * 32;
      const w = (row.mean / max) * 280;
      svg.append(el("text", { x: 0, y: y + 16, "font-size": 13, fill: "#1b1226" }, row.title));
      svg.append(el("rect", { x: 70, y, width: w.toFixed(1), height: 18, rx: 4, fill: colors[row.title] }));
      svg.append(el("text", { x: 78 + w, y: y + 14, "font-size": 13, fill: "#1b1226" }, String(row.mean)));
    });
    return svg;
  }

  function prices(rows) {
    const width = 640;
    const height = Math.max(rows.length, 1) * 26 + 8;
    const max = Math.max(1, ...rows.map((row) => Number(row.price) || 0));
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", role: "img" });
    rows.forEach((row, index) => {
      const y = index * 26 + 4;
      const w = (Number(row.price) / max) * 280;
      svg.append(el("text", { x: 0, y: y + 14, "font-size": 11, fill: "#1b1226" }, String(row.name).slice(0, 34)));
      svg.append(el("rect", {
        x: 250,
        y,
        width: w.toFixed(1),
        height: 16,
        rx: 4,
        fill: row.kind === "Headout" ? "#8000ff" : "#8d86a3",
      }));
      svg.append(el("text", { x: 256 + w, y: y + 13, "font-size": 11, fill: "#5e5670" }, `${row.currency || ""} ${Number(row.price).toFixed(0)}`));
    });
    return svg;
  }

  return { stacked, bars, heatmap, dots, stability, counts, prices };
})();
