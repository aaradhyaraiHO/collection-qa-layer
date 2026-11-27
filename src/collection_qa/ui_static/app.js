const steps = ["collection", "inputs", "panel", "run"];
const state = {
  step: 0,
  query: "",
  lookup: null,
  competitors: [],
  threads: [],
  exports: [],
  shots: [],
  personas: 8,
  mock: true,
};

const $ = (id) => document.getElementById(id);

function showStep(index) {
  state.step = index;
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.panel !== steps[index]);
  });
  document.querySelectorAll(".steps button").forEach((button, i) => {
    button.setAttribute("aria-current", i === index ? "step" : "false");
  });
}

document.querySelectorAll(".steps button").forEach((button) => {
  button.addEventListener("click", () => showStep(Number(button.dataset.go)));
});
document.querySelectorAll("[data-next]").forEach((button) => {
  button.addEventListener("click", () => showStep(state.step + 1));
});
document.querySelectorAll("[data-back]").forEach((button) => {
  button.addEventListener("click", () => showStep(state.step - 1));
});

let lookupTimer;
$("query").addEventListener("input", () => {
  state.query = $("query").value.trim();
  clearTimeout(lookupTimer);
  lookupTimer = setTimeout(lookup, 350);
});

async function lookup() {
  const badge = $("badge");
  const meta = $("lookup-meta");
  if (!state.query) {
    badge.className = "badge idle";
    badge.textContent = "Waiting";
    meta.textContent = "Type a collection name or a numeric CE id.";
    return;
  }
  badge.className = "badge idle";
  badge.textContent = "Looking up";
  const response = await fetch("/api/lookup?q=" + encodeURIComponent(state.query));
  const data = await response.json();
  state.lookup = data;
  badge.className = "badge " + (data.status || "NOT_FOUND");
  badge.textContent = (data.status || "NOT_FOUND").replaceAll("_", " ");
  const url = data.collection_url
    ? `<a href="${data.collection_url}">${data.collection_url}</a>`
    : "No collection URL yet.";
  meta.innerHTML = `${data.name || state.query}. ${url} ${data.note || ""}`;
  refreshCost();
}

function chipList(list, host, field) {
  host.innerHTML = "";
  list.forEach((value, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = value;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.setAttribute("aria-label", "Remove " + value);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      list.splice(index, 1);
      chipList(list, host, field);
    });
    chip.append(remove);
    host.append(chip);
  });
}

function bindChips(inputId, list, hostId) {
  const input = $(inputId);
  const host = $(hostId);
  input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    list.push(value);
    input.value = "";
    chipList(list, host);
  });
}
bindChips("competitor", state.competitors, "competitor-chips");
bindChips("thread", state.threads, "thread-chips");

function bindDrop(zoneId, inputId, list, kind) {
  const zone = $(zoneId);
  const input = $(inputId);
  const host = zone.querySelector(".thumbs");
  const take = async (files) => {
    for (const file of files) {
      const body = new FormData();
      body.append("query", state.query || $("query").value.trim());
      body.append("kind", kind);
      body.append("file", file);
      const response = await fetch("/api/upload", { method: "POST", body });
      const saved = await response.json();
      list.push(saved);
      drawFiles(host, list);
    }
  };
  zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("hot"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("hot"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("hot");
    take(event.dataTransfer.files);
  });
  input.addEventListener("change", () => take(input.files));
}

function drawFiles(host, list) {
  host.innerHTML = "";
  list.forEach((item) => {
    const figure = document.createElement("figure");
    if (item.thumbnail) {
      const img = document.createElement("img");
      img.src = item.thumbnail;
      img.alt = item.name;
      figure.append(img);
    } else {
      const chip = document.createElement("div");
      chip.className = "filechip";
      chip.textContent = item.name.split(".").pop();
      figure.append(chip);
    }
    const caption = document.createElement("figcaption");
    caption.textContent = item.name;
    figure.append(caption);
    host.append(figure);
  });
}

bindDrop("export-drop", "export-file", state.exports, "exports");
bindDrop("shot-drop", "shot-file", state.shots, "screenshots");

$("personas").addEventListener("input", () => {
  state.personas = Number($("personas").value || 8);
  refreshCost();
});
$("mock").addEventListener("change", () => {
  state.mock = $("mock").checked;
  refreshCost();
});

async function refreshCost() {
  const products = state.lookup && state.lookup.product_count ? state.lookup.product_count : 8;
  const response = await fetch(`/api/estimate?personas=${state.personas}&products=${products}&mock=${state.mock ? 1 : 0}`);
  const data = await response.json();
  $("cost").textContent = data.line;
}

$("run").addEventListener("click", startRun);

async function startRun() {
  showStep(3);
  $("progress-wrap").classList.remove("hidden");
  $("run-panel").classList.remove("as-report");
  $("exec").classList.add("hidden");
  document.querySelectorAll(".progress li").forEach((item) => item.className = "");
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: state.query || $("query").value.trim(),
      personas: state.personas,
      mock: state.mock,
      eos_mmp_link: $("eos-mmp").value.trim(),
      eos_assortment_link: $("eos-assortment").value.trim(),
      eos_content_link: $("eos-content").value.trim(),
      microbrand_url: $("microbrand").value.trim(),
      notes: $("notes").value.trim(),
      competitor_urls: state.competitors,
      slack_threads: state.threads,
    }),
  });
  const started = await response.json();
  const source = new EventSource("/api/runs/" + started.id + "/events");
  source.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    const item = document.querySelector(`.progress li[data-stage="${data.stage}"]`);
    const rows = [...document.querySelectorAll(".progress li")];
    const index = rows.indexOf(item);
    rows.forEach((row, rowIndex) => {
      row.classList.toggle("active", row === item);
      row.classList.toggle("done", index > -1 && rowIndex < index);
    });
    if (item) item.querySelector("em").textContent = data.detail;
  });
  source.addEventListener("done", (event) => {
    source.close();
    const data = JSON.parse(event.data);
    showResult(data);
  });
  source.onerror = () => {
    source.close();
  };
}

function showResult(data) {
  if (!data.view) return;
  $("progress-wrap").classList.add("hidden");
  $("run-panel").classList.add("as-report");
  renderExecutive($("exec"), data.view);
  loadHistory();
}

async function loadHistory() {
  const response = await fetch("/api/history");
  const rows = await response.json();
  const host = $("history");
  host.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `${row.name}<small>${row.verdict} · ${row.when}</small>`;
    button.addEventListener("click", () => {
      showStep(3);
      showResult(row);
    });
    item.append(button);
    host.append(item);
  });
}

async function loadPilots() {
  const response = await fetch("/api/pilots");
  const rows = await response.json();
  const host = $("pilots");
  host.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `${row.name}<small>Live pilot · CE ${row.ce_id || ""}</small>`;
    button.addEventListener("click", async () => {
      const loaded = await fetch("/api/pilots/" + encodeURIComponent(row.id));
      const view = await loaded.json();
      showStep(3);
      showResult({ view });
    });
    item.append(button);
    host.append(item);
  });
}

loadPilots();
loadHistory();
refreshCost();
