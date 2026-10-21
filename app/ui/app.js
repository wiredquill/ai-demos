"use strict";

// AI Compare web UI. Talks to the Flask API served from the same origin.

const LEVEL_PERIOD_S = 30; // must match the rotation in chat_via_pipeline()
const CHAT_TIMEOUT_MS = 120000;

const $ = (sel) => document.querySelector(sel);
const state = { levels: [], availabilityOn: false, loadRunning: false, sending: false };

// ---------- helpers ----------

async function api(path, opts = {}) {
  const { timeout = 15000, ...rest } = opts;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      ...rest,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || body.message || `HTTP ${res.status}`);
    return body;
  } catch (err) {
    if (err.name === "AbortError") throw new Error("Request timed out");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Small, safe Markdown subset: fenced code, headings, lists, bold/italic, inline code.
function renderMarkdown(src) {
  const blocks = [];
  const text = escapeHtml(src.trim()).replace(/```[\w-]*\n?([\s\S]*?)```/g, (_, code) => {
    blocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
    return `\u0000${blocks.length - 1}\u0000`;
  });
  const inline = (s) =>
    s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");

  return text
    .split(/\n{2,}/)
    .map((para) => {
      const fenced = para.match(/^\u0000(\d+)\u0000$/);
      if (fenced) return blocks[+fenced[1]];
      const lines = para.split("\n");
      if (lines.every((l) => /^\s*([-*•]|\d+[.)])\s+/.test(l))) {
        const ordered = /^\s*\d/.test(lines[0]);
        const items = lines.map((l) => `<li>${inline(l.replace(/^\s*([-*•]|\d+[.)])\s+/, ""))}</li>`).join("");
        return ordered ? `<ol>${items}</ol>` : `<ul>${items}</ul>`;
      }
      const heading = para.match(/^#{1,4}\s+(.+)$/);
      if (heading) return `<h4>${inline(heading[1])}</h4>`;
      return `<p>${inline(lines.join("<br>"))}</p>`;
    })
    .join("")
    .replace(/\u0000(\d+)\u0000/g, (_, i) => blocks[+i]);
}

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function log(message, level = "info") {
  const list = $("#activity");
  list.querySelector(".activity-empty")?.remove();
  const li = document.createElement("li");
  li.dataset.level = level;
  li.innerHTML = `<time>${timeNow()}</time><span></span>`;
  li.querySelector("span").textContent = message;
  list.prepend(li);
  while (list.children.length > 30) list.lastChild.remove();
}

function toast(message, level = "info") {
  const el = document.createElement("div");
  el.className = "toast";
  el.dataset.level = level;
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), 6000);
}

function setChip(id, ok, label) {
  const chip = $(id);
  chip.dataset.state = ok === null ? "off" : ok ? "ok" : "bad";
  if (label) chip.lastChild.textContent = label;
}

// ---------- theme ----------

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("aic-theme"); } catch {}
  if (saved) document.documentElement.dataset.theme = saved;
  $("#theme-toggle").addEventListener("click", () => {
    const isDark =
      document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = isDark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("aic-theme", next); } catch {}
  });
}

// ---------- pipeline levels ----------

function renderLevels() {
  const track = $("#levels-track");
  track.innerHTML = state.levels
    .map((l, i) => `<li class="level" data-i="${i}"><span aria-hidden="true">${l.icon}</span><span>${escapeHtml(l.name)}</span></li>`)
    .join("");
  tickLevels();
}

function tickLevels() {
  if (!state.levels.length) return;
  const now = Date.now() / 1000;
  const idx = Math.floor(now / LEVEL_PERIOD_S) % state.levels.length;
  const remaining = Math.ceil(LEVEL_PERIOD_S - (now % LEVEL_PERIOD_S));
  document.querySelectorAll(".level").forEach((el) => {
    const current = +el.dataset.i === idx;
    el.setAttribute("aria-current", current);
    let bar = el.querySelector(".level-progress");
    if (current) {
      if (!bar) {
        bar = document.createElement("i");
        bar.className = "level-progress";
        el.append(bar);
      }
      bar.style.width = `${((LEVEL_PERIOD_S - remaining) / LEVEL_PERIOD_S) * 100}%`;
    } else {
      bar?.remove();
    }
  });
  const next = state.levels[(idx + 1) % state.levels.length];
  $("#levels-timer").textContent = `${next.icon} ${next.name} in ${remaining}s`;
}

// ---------- chat ----------

function paneEls(id) {
  const pane = $(id);
  return {
    pane,
    body: pane.querySelector('[data-role="body"]'),
    route: pane.querySelector('[data-role="route"]'),
    latency: pane.querySelector('[data-role="latency"]'),
  };
}

function setPaneLoading(id, note) {
  const p = paneEls(id);
  p.pane.dataset.state = "loading";
  p.latency.textContent = "";
  p.body.innerHTML = `<div class="skeleton" aria-label="Waiting for response"><i></i><i></i><i></i><i></i><i></i></div><p class="skeleton-note">${escapeHtml(note)}</p>`;
  const started = Date.now();
  p.pane._timer = setInterval(() => {
    p.latency.textContent = `${((Date.now() - started) / 1000).toFixed(0)}s`;
  }, 1000);
}

function setPaneResult(id, r) {
  const p = paneEls(id);
  clearInterval(p.pane._timer);
  p.pane.dataset.state = r.ok ? "done" : "error";
  p.latency.textContent = r.latency_ms != null ? `${(r.latency_ms / 1000).toFixed(1)}s · ${r.model || ""}` : "";
  if (id === "#pane-pipeline" && r.level) {
    p.route.textContent = `${r.level_icon || ""} ${r.level}`.trim();
    // Make silent fallbacks visible during a demo
    if (r.route && r.route !== "Pipelines Service") p.latency.textContent += ` · via ${r.route}`;
  } else if (r.route) {
    p.route.textContent = r.route === "Direct Ollama" ? "Model only" : r.route;
  }
  if (r.ok) {
    p.body.innerHTML = renderMarkdown(r.content || "(empty response)");
  } else {
    p.body.innerHTML = `<div class="error-box"><strong>No answer</strong></div>`;
    p.body.querySelector(".error-box").append(document.createTextNode(r.content || r.error || "Unknown error"));
  }
}

async function runSide(target, paneId, message, model) {
  try {
    const r = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, model, target }),
      timeout: CHAT_TIMEOUT_MS,
    });
    setPaneResult(paneId, r);
    return r;
  } catch (err) {
    const hint = state.availabilityOn ? " The availability demo is ON, so the service is meant to be unresponsive." : "";
    const r = { ok: false, content: `${err.message}.${hint}` };
    setPaneResult(paneId, r);
    return r;
  }
}

async function send(e) {
  e?.preventDefault();
  const message = $("#prompt").value.trim();
  const model = $("#model").value;
  if (!message || state.sending) return;
  state.sending = true;
  const btn = $("#send");
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");

  setPaneLoading("#pane-direct", `Asking ${model || "the model"} directly…`);
  setPaneLoading("#pane-pipeline", "Rewriting the prompt in the pipeline, then asking the model…");
  log(`Compare: “${message.slice(0, 60)}${message.length > 60 ? "…" : ""}”`);

  const [a, b] = await Promise.all([
    runSide("direct", "#pane-direct", message, model),
    runSide("pipeline", "#pane-pipeline", message, model),
  ]);
  if (!a.ok || !b.ok) log("One or both paths returned an error", "error");

  state.sending = false;
  btn.disabled = false;
  btn.removeAttribute("aria-busy");
}

// ---------- models / info ----------

async function loadModels() {
  const select = $("#model");
  try {
    const { models, error } = await api("/api/models");
    if (!models.length) throw new Error(error || "No models installed");
    const previous = select.value;
    select.innerHTML = models.map((m) => `<option>${escapeHtml(m)}</option>`).join("");
    if (models.includes(previous)) select.value = previous;
    setChip("#chip-ollama", true, `Ollama · ${models.length} model${models.length > 1 ? "s" : ""}`);
  } catch (err) {
    select.innerHTML = `<option value="">No models available</option>`;
    setChip("#chip-ollama", false, "Ollama unreachable");
    log(`Models: ${err.message}`, "error");
  }
}

async function loadInfo() {
  try {
    const info = await api("/api/info");
    state.levels = info.levels || [];
    renderLevels();
    setChip("#chip-pipelines", info.pipelines_url ? true : null, info.pipelines_url ? "Pipelines" : "Pipelines off");
    setChip("#chip-otel", info.observability_enabled ? true : null, info.observability_enabled ? "Telemetry on" : "Telemetry off");
    $("#chip-otel").title = info.otlp_endpoint || "";
    if (info.namespace) {
      const ns = $("#chip-ns");
      ns.textContent = info.namespace;
      ns.title = info.pod ? `pod ${info.pod}` : "";
      ns.hidden = false;
    }
  } catch (err) {
    log(`Info: ${err.message}`, "error");
  }
}

// ---------- providers ----------

function renderProviders(providers) {
  const entries = Object.entries(providers || {}).sort(([a], [b]) => a.localeCompare(b));
  let online = 0;
  const times = [];
  $("#providers").innerHTML = entries
    .map(([name, p]) => {
      const ok = p.status === "🟢";
      if (ok) online++;
      const ms = parseInt(p.response_time, 10);
      if (!Number.isNaN(ms)) times.push(ms);
      return `<li class="provider" title="${escapeHtml(p.country || "")} · HTTP ${escapeHtml(String(p.status_code ?? ""))}">
        <span class="dot" data-state="${ok ? "ok" : "bad"}"></span>
        <span class="provider-name">${escapeHtml(name)}</span>
        <span class="provider-rt">${Number.isNaN(ms) ? "—" : ms + "ms"}</span>
      </li>`;
    })
    .join("");
  const avg = times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : null;
  $("#providers-summary").innerHTML =
    `<span><b>${online}</b> / ${entries.length} reachable</span><span>avg <b>${avg ?? "—"}</b>${avg != null ? "ms" : ""}</span>`;
}

async function loadProviders(refresh = false) {
  try {
    const data = refresh ? await api("/api/providers/refresh", { method: "POST", timeout: 30000 }) : await api("/api/status");
    renderProviders(data.providers);
    if (refresh) log("Provider reachability re-checked");
  } catch (err) {
    log(`Providers: ${err.message}`, "error");
  }
}

// ---------- demos ----------

function renderAvailability(on, configValue) {
  state.availabilityOn = on;
  const sw = $("#avail-toggle");
  sw.setAttribute("aria-checked", on);
  sw.closest(".control").dataset.state = on ? "on" : "off";
  $("#avail-detail").textContent = configValue || (on ? "Broken config" : "Working config");
  $("#outage-banner").hidden = !on;
}

async function loadDemoStatus() {
  try {
    const d = await api("/api/demo/status", { timeout: 8000 });
    const a = d.availability_demo || {};
    if (a.is_active !== state.availabilityOn) {
      if (state._availKnown) log(`Availability demo is now ${a.is_active ? "ON" : "OFF"}`, a.is_active ? "warning" : "info");
    }
    state._availKnown = true;
    renderAvailability(!!a.is_active, a.config_value);
  } catch {
    // The demo itself can make the API slow; keep the last known state
  }
}

async function toggleAvailability() {
  const sw = $("#avail-toggle");
  const turningOn = !state.availabilityOn;
  if (turningOn && !confirm("Break the app on purpose? Health checks will fail and Kubernetes may restart the pod.")) return;
  sw.disabled = true;
  try {
    const r = await api("/api/availability-demo/toggle", { method: "POST", timeout: 30000 });
    renderAvailability(!!r.is_active, r.config_value);
    const level = r.status === "error" ? "error" : r.is_active ? "warning" : "info";
    log(r.message, level);
    toast(r.message, level);
  } catch (err) {
    log(`Availability demo: ${err.message}`, "error");
    toast(`Availability demo failed: ${err.message}`, "error");
  } finally {
    sw.disabled = false;
  }
}

async function runDataLeak() {
  const btn = $("#leak-run");
  btn.disabled = true;
  try {
    const r = await api("/api/data-leak-demo", { method: "POST", timeout: 15000 });
    $("#leak-detail").textContent = `Last run ${timeNow()}`;
    log(r.message, "warning");
    toast("Synthetic card/SSN patterns sent. Check NeuVector for a DLP event.", "warning");
  } catch (err) {
    log(`Data leak demo: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
  }
}

function renderLoad(running, detail, interval) {
  state.loadRunning = running;
  if (interval) state.loadInterval = interval;
  const btn = $("#load-toggle");
  btn.disabled = false;
  btn.textContent = running ? "Stop" : "Start";
  const every = state.loadInterval ? ` · every ${state.loadInterval}s` : "";
  $("#load-detail").textContent = running
    ? `Running${every}`
    : detail && detail !== "Not Deployed" ? detail : "Stopped";
}

async function loadLoadStatus() {
  try {
    const s = await api("/api/load-simulator/status", { timeout: 15000 });
    renderLoad(!!s.is_running, s.detail, s.interval_seconds);
  } catch {
    $("#load-detail").textContent = "Status unavailable";
    $("#load-toggle").disabled = false;
  }
}

async function toggleLoad() {
  const btn = $("#load-toggle");
  btn.disabled = true;
  const action = state.loadRunning ? "stop" : "start";
  try {
    const r = await api(`/api/load-simulator/${action}`, { method: "POST", timeout: 40000 });
    log(r.message);
    renderLoad(action === "start", r.message);
    setTimeout(loadLoadStatus, 5000);
  } catch (err) {
    log(`Load simulator: ${err.message}`, "error");
    toast(`Load simulator ${action} failed: ${err.message}`, "error");
    btn.disabled = false;
  }
}

// ---------- wiring ----------

function init() {
  initTheme();

  $("#composer").addEventListener("submit", send);
  $("#prompt").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send(e);
  });
  $("#suggestions").addEventListener("click", (e) => {
    const b = e.target.closest(".suggestion");
    if (!b) return;
    $("#prompt").value = b.textContent;
    $("#prompt").focus();
  });
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) $(".kbd").textContent = "Ctrl↵";

  $("#avail-toggle").addEventListener("click", toggleAvailability);
  $("#leak-run").addEventListener("click", runDataLeak);
  $("#load-toggle").addEventListener("click", toggleLoad);
  $("#providers-refresh").addEventListener("click", () => loadProviders(true));
  $("#help-open").addEventListener("click", () => $("#help").showModal());

  loadInfo();
  loadModels();
  loadProviders();
  loadDemoStatus();
  loadLoadStatus();

  setInterval(tickLevels, 1000);
  setInterval(loadDemoStatus, 5000);
  setInterval(() => loadProviders(), 30000);
  setInterval(loadLoadStatus, 20000);
  setInterval(loadModels, 60000);
}

document.addEventListener("DOMContentLoaded", init);
