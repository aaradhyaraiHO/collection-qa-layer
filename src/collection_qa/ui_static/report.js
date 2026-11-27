function renderExecutive(host, view) {
  host.innerHTML = "";
  host.classList.remove("hidden");
  const article = document.createElement("article");
  article.className = "exec";
  article.id = "exec-body";

  const head = document.createElement("header");
  head.className = `exec-head verdict-${slug(view.verdict)}`;
  head.innerHTML = `
    <p class="eyebrow">${escapeHtml(view.status || "")}${view.mock ? " · mock" : ""} ${view.ce_id ? "· CE " + escapeHtml(String(view.ce_id)) : ""}</p>
    <h2>${escapeHtml(view.title || "Collection")}</h2>
    <p class="verdict-line"><strong>${escapeHtml(view.verdict || "")}</strong> ${escapeHtml(view.verdict_reason || "")}</p>
  `;
  const kpis = document.createElement("div");
  kpis.className = "kpis";
  (view.kpis || []).forEach((item) => {
    const card = document.createElement("div");
    card.innerHTML = `<span>${escapeHtml(item.label)}</span><strong>${escapeHtml(String(item.value))}</strong><em>${escapeHtml(item.note || "")}</em>`;
    kpis.append(card);
  });
  head.append(kpis);
  const actions = document.createElement("div");
  actions.className = "nav";
  const htmlButton = document.createElement("button");
  htmlButton.type = "button";
  htmlButton.className = "btn secondary";
  htmlButton.textContent = "Download HTML";
  htmlButton.addEventListener("click", () => downloadReportHtml(view, article));
  const pdfButton = document.createElement("button");
  pdfButton.type = "button";
  pdfButton.className = "btn secondary";
  pdfButton.textContent = "Download PDF";
  pdfButton.addEventListener("click", () => window.print());
  actions.append(htmlButton, pdfButton);
  head.append(actions);
  article.append(head);

  article.append(section("1. Would they book?", () => {
    const table = document.createElement("table");
    table.className = "grid-table";
    table.innerHTML = "<thead><tr><th>Product</th><th>Mean</th><th>4 or 5</th><th>Share of the panel</th></tr></thead>";
    const body = document.createElement("tbody");
    (view.likely_to_book || []).forEach((row) => {
      const tr = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = row.title;
      const mean = document.createElement("td");
      mean.textContent = Number(row.mean).toFixed(2);
      const likely = document.createElement("td");
      likely.textContent = row.likely == null ? "—" : `${Math.round(row.likely * 100)}%`;
      const chart = document.createElement("td");
      if (row.pmf && row.pmf.length) chart.append(Charts.stacked(row.pmf));
      tr.append(name, mean, likely, chart);
      body.append(tr);
    });
    table.append(body);
    const legend = document.createElement("p");
    legend.className = "legend";
    legend.textContent = "Each bar is the share of replies closest to 1, 2, 3, 4, and 5. Green is the likely-to-book end.";
    return [table, legend];
  }));

  article.append(section("2. What they said", () => {
    const wrap = document.createElement("div");
    wrap.className = "quotes";
    (view.quotes || []).forEach((quote) => {
      const block = document.createElement("blockquote");
      const text = document.createElement("p");
      text.textContent = quote.text;
      const footer = document.createElement("footer");
      footer.textContent = `${quote.who} on ${quote.on}${quote.mean != null ? ` · ${quote.mean}` : ""}`;
      block.append(text, footer);
      wrap.append(block);
    });
    const chartHost = document.createElement("div");
    chartHost.className = "chart-block";
    const caption = document.createElement("h3");
    caption.textContent = "Best to worst";
    chartHost.append(caption, Charts.bars(view.ranking || []));
    return [wrap, chartHost];
  }));

  article.append(section("3. What to fix", () => {
    const table = document.createElement("table");
    table.className = "grid-table fixes";
    table.innerHTML = "<thead><tr><th>Priority</th><th>Issue</th><th>Page</th><th>What to change</th><th>Owner</th><th>Quote</th></tr></thead>";
    const body = document.createElement("tbody");
    (view.fixes || []).forEach((row) => {
      const tr = document.createElement("tr");
      const cells = ["priority", "issue", "what_to_change", "owner"].map((key) => {
        const td = document.createElement("td");
        td.textContent = row[key] || "";
        return td;
      });
      const link = document.createElement("td");
      if (row.page_link) {
        const anchor = document.createElement("a");
        anchor.href = row.page_link;
        anchor.textContent = "Open";
        anchor.rel = "noreferrer";
        link.append(anchor);
      }
      const quote = document.createElement("td");
      quote.textContent = (row.quote || "").slice(0, 180);
      tr.append(cells[0], cells[1], link, cells[2], cells[3], quote);
      body.append(tr);
    });
    table.append(body);
    return [table];
  }));

  article.append(section("4. Who it works for", () => {
    const note = document.createElement("p");
    note.className = "lede";
    note.textContent = "A cell with fewer than 8 travellers is faded. Those means are thin.";
    const heat = document.createElement("div");
    heat.className = "chart-block";
    heat.append(Charts.heatmap(view.heatmap || { columns: [], rows: [] }));
    const dots = document.createElement("div");
    dots.className = "chart-block";
    const caption = document.createElement("h3");
    caption.textContent = "Page intent by traveller type";
    dots.append(caption, Charts.dots(view.dots || []));
    return [note, heat, dots];
  }));

  const detail = document.createElement("section");
  detail.className = "exec-section";
  const detailTitle = document.createElement("h3");
  detailTitle.textContent = "5. Detail";
  detail.append(detailTitle);
  detail.append(disclosure("Product scores", () => {
    const host = document.createElement("div");
    host.append(Charts.bars(view.detail.products || []));
    const table = document.createElement("table");
    table.className = "grid-table";
    table.innerHTML = "<thead><tr><th>Product</th><th>Mean</th><th>z vs collection</th><th>Likely</th></tr></thead>";
    const body = document.createElement("tbody");
    (view.detail.products || []).forEach((row) => {
      const tr = document.createElement("tr");
      [row.title, Number(row.mean).toFixed(2), row.z == null ? "—" : row.z, row.likely == null ? "—" : `${Math.round(row.likely * 100)}%`].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      });
      body.append(tr);
    });
    table.append(body);
    host.append(table);
    return host;
  }));
  detail.append(disclosure("Microbrand vs Headout", () => {
    const host = document.createElement("div");
    const note = document.createElement("p");
    note.textContent = (view.detail.microbrand || {}).note || "";
    host.append(note);
    const bars = ((view.detail.microbrand || {}).bars || []).map((row) => ({ title: row.label, mean: row.mean }));
    if (bars.length) host.append(Charts.bars(bars, { max: 5 }));
    return host;
  }));
  detail.append(disclosure("Competitor prices", () => {
    const host = document.createElement("div");
    const rows = (view.detail || {}).prices || [];
    if (!rows.length) {
      host.textContent = "No comparable prices were attached.";
      return host;
    }
    const note = document.createElement("p");
    note.className = "lede";
    note.textContent = "Purple is Headout. Grey is a competitor in the same currency. Other currencies are left off this chart.";
    host.append(note, Charts.prices(rows));
    return host;
  }));
  detail.append(disclosure("Pass, warn, and fail", () => {
    const host = document.createElement("div");
    host.append(Charts.counts(view.detail.checks || {}));
    return host;
  }));
  article.append(detail);

  article.append(section("6. Can we trust it?", () => {
    const trust = view.trust || {};
    const badge = document.createElement("p");
    badge.className = `trust-label ${trust.label === "ROBUST" ? "good" : "wait"}`;
    badge.textContent = trust.label || "";
    const note = document.createElement("p");
    note.textContent = trust.note || "";
    const chips = document.createElement("div");
    chips.className = "kpis";
    (trust.highlights || []).forEach((item) => {
      const card = document.createElement("div");
      card.innerHTML = `<span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.detail || "")}</strong>`;
      chips.append(card);
    });
    const chart = document.createElement("div");
    chart.className = "chart-block";
    chart.append(Charts.stability(trust));
    const list = document.createElement("ul");
    (trust.bullets || []).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      list.append(li);
    });
    const meta = document.createElement("p");
    meta.className = "lede";
    meta.textContent = `Page intent across the mixes runs ${trust.page_low ?? "—"} to ${trust.page_high ?? "—"}. Mean rank agreement (Kendall tau) ${trust.kendall_mean ?? "—"}. Bars under the range are the mean page move on each persona axis.`;
    return [badge, note, chips, chart, meta, list];
  }));

  const appendix = disclosure("7. Appendix · inputs used / missing and pages checked", () => {
    const host = document.createElement("div");
    const table = document.createElement("table");
    table.className = "grid-table";
    table.innerHTML = "<thead><tr><th>Field</th><th>Status</th><th>Source</th><th>Detail</th></tr></thead>";
    const body = document.createElement("tbody");
    ((view.appendix || {}).inputs || []).forEach((row) => {
      const tr = document.createElement("tr");
      ["field", "status", "source", "detail"].forEach((key) => {
        const td = document.createElement("td");
        td.textContent = row[key] || "";
        if (key === "status" && row[key] === "not provided") td.className = "missing";
        tr.append(td);
      });
      body.append(tr);
    });
    table.append(body);
    const pages = document.createElement("ul");
    ((view.appendix || {}).pages || []).forEach((url) => {
      const li = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.textContent = url;
      li.append(anchor);
      pages.append(li);
    });
    const method = document.createElement("p");
    method.textContent = (view.appendix || {}).method || "";
    host.append(table, method, pages);
    return host;
  }, true);
  const appendixSection = document.createElement("section");
  appendixSection.className = "exec-section";
  appendixSection.append(appendix);
  article.append(appendixSection);

  host.append(article);
}

function section(title, build) {
  const block = document.createElement("section");
  block.className = "exec-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  block.append(heading);
  build().forEach((node) => block.append(node));
  return block;
}

function disclosure(title, build, collapsed = true) {
  const details = document.createElement("details");
  details.className = "fold";
  if (!collapsed) details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = title;
  details.append(summary);
  details.append(build());
  return details;
}

function slug(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, "-");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function downloadReportHtml(view, article) {
  const css = await (await fetch("/static/report.css")).text();
  const doc = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>${escapeHtml(view.title)} — ${escapeHtml(view.verdict)}</title><style>${css}</style></head><body>${article.outerHTML}</body></html>`;
  const blob = new Blob([doc], { type: "text/html" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${slug(view.title) || "collection"}.check.html`;
  link.click();
  URL.revokeObjectURL(link.href);
}
