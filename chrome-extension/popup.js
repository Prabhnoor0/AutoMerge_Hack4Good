/**
 * AutoMerge Debugger — Popup v3
 *
 * KEY RULES:
 * 1. If content script sends a "selection" payload → use it, lock it, ignore
 *    subsequent non-selection messages unless user explicitly re-detects.
 * 2. Analyze uses ONLY the active payload's `code` field.
 * 3. Parser-first: backend returns syntax errors before LLM results.
 */

"use strict";

// ── Configurable endpoints ──────────────────────────────
// For LOCAL dev:  defaults below work out of the box.
// For PRODUCTION: set via chrome.storage.sync (e.g. from an options page)
//   chrome.storage.sync.set({ API_BASE: "https://automerge-backend.onrender.com/api",
//                             SITE_BASE: "https://automerge-frontend.vercel.app" });
let API_BASE  = "http://localhost:8000/api";
let SITE_BASE = "http://localhost:3000";

// Load any production overrides from storage
chrome.storage?.sync?.get(["API_BASE", "SITE_BASE"], (cfg) => {
  if (cfg.API_BASE)  API_BASE  = cfg.API_BASE;
  if (cfg.SITE_BASE) SITE_BASE = cfg.SITE_BASE;
});

/* ── State ──────────────────────────────────────────── */
let _active     = null;   // current CodePayload — set by content script
let _lastResult = null;   // last backend AnalysisResult
let _port       = null;
let _analyzing  = false;
let _selectionLocked = false; // true when an active user selection is displayed

/* ── DOM ────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const show = (el) => { if (el) el.style.display = ""; };
const hide = (el) => { if (el) el.style.display = "none"; };

const SOURCE_META = {
  selection:  { label: "Selection",  badge: "🖱️ Selection",  method: "User selection" },
  github:     { label: "GitHub",     badge: "🐙 GitHub",      method: "GitHub code view" },
  codeblock:  { label: "Code Block", badge: "📦 Code Block",  method: "Code block" },
  web_editor: { label: "Editor",     badge: "⚡ Editor",      method: "Browser editor" },
  textarea:   { label: "Textarea",   badge: "📝 Textarea",    method: "Active textarea" },
  none:       { label: "None",       badge: "❓ None",         method: "none" },
};

/* ── Payload acceptance logic ────────────────────────── */
function shouldAcceptPayload(incoming) {
  if (!incoming || !incoming.code?.trim()) return true; // clear always accepted
  // If we currently have an active user selection, ONLY accept another selection payload
  if (_selectionLocked && incoming.source_type !== "selection") return false;
  return true;
}

/* ── UI: render source bar ───────────────────────────── */
function renderSourceBar(data) {
  const meta = SOURCE_META[data.source_type] || SOURCE_META.none;
  $("sourceBadge").textContent  = meta.badge;
  $("sourceMethod").textContent = data.method || meta.method;
  $("sourceLabel").textContent  = data.filename || trimUrl(data.page_url);
  // Highlight selection badge in green
  $("sourceBadge").style.color      = data.source_type === "selection" ? "#22c55e" : "#4f8ef7";
  $("sourceBadge").style.background = data.source_type === "selection"
    ? "rgba(34,197,94,.12)" : "rgba(79,142,247,.12)";
  show($("sourceBar"));
}

function trimUrl(url) {
  try { const u = new URL(url); return (u.hostname + u.pathname).slice(0, 50); }
  catch { return (url || "").slice(0, 50); }
}

/* ── UI: code preview ────────────────────────────────── */
function renderPreview(data) {
  if (!data?.code) { hide($("previewSection")); return; }
  const lines = data.code.split("\n").slice(0, 10).join("\n");
  $("codePreview").textContent = lines;
  const lc = data.line_count || data.code.split("\n").length;
  const cc = data.char_count || data.code.length;
  const lang = data.language ? ` · ${data.language}` : "";
  $("previewMeta").textContent = `${lc} lines · ${cc} chars${lang}`;
  // Colour the LIVE tag by source
  const liveTag = $("liveTag");
  if (liveTag) {
    liveTag.textContent = data.source_type === "selection" ? "SELECTED" : "LIVE";
    liveTag.style.color = data.source_type === "selection" ? "#22c55e" : "#4f8ef7";
  }
  show($("previewSection"));
}

/* ── UI: button sync ─────────────────────────────────── */
function syncButton() {
  const hasCode = !!(_active?.code?.trim());
  $("analyzeBtn").disabled = _analyzing || !hasCode;
  if (!_analyzing) {
    $("analyzeBtnIcon").textContent = _lastResult ? "↺" : "🔬";
    $("analyzeBtnText").textContent = _lastResult ? "Re-analyze" : "Analyze";
  }
}

/* ── UI: empty state ─────────────────────────────────── */
function renderEmpty(msg) {
  $("emptyTitle").textContent = msg || "Select or type code to analyze";
  show($("emptyState"));
  hide($("sourceBar"));
  hide($("previewSection"));
  hide($("results"));
  hide($("loading"));
  hideError();
  _active = null;
  _selectionLocked = false;
  syncButton();
}

/* ── UI: error ───────────────────────────────────────── */
function showError(msg) { $("errorMsg").textContent = msg; show($("errorState")); }
function hideError()    { hide($("errorState")); }

/* ── UI: loading ─────────────────────────────────────── */
function showLoading() {
  show($("loading")); hide($("results"));
  $("analyzeBtnIcon").textContent = "⏳";
  $("analyzeBtnText").textContent = "Analyzing…";
  $("analyzeBtn").disabled = true;
}

/* ── Confidence coloring ─────────────────────────────── */
function confStyle(c) {
  if (c >= 0.8) return { bg:"rgba(34,197,94,.15)", color:"#22c55e" };
  if (c >= 0.5) return { bg:"rgba(245,158,11,.15)", color:"#f59e0b" };
  return             { bg:"rgba(239,68,68,.15)",   color:"#ef4444" };
}

/* ── Handle incoming code payload ────────────────────── */
function handleCodePayload(data) {
  // Reject stale non-selection updates when selection is locked
  if (!shouldAcceptPayload(data)) return;

  if (!data || !data.code?.trim()) {
    _selectionLocked = false;
    renderEmpty(data?.error);
    return;
  }

  _active = data;
  _selectionLocked = (data.source_type === "selection");

  hide($("emptyState"));
  hideError();
  renderSourceBar(data);
  renderPreview(data);
  syncButton();
}

/* ── Connect long-lived port to content script ───────── */
function connectPort(tabId) {
  try {
    _port = chrome.tabs.connect(tabId, { name: "automerge-popup" });
    _port.onMessage.addListener((msg) => {
      if (msg.action === "codeUpdated") handleCodePayload(msg.data);
      if (msg.action === "codeCleared") handleCodePayload(null);
    });
    _port.onDisconnect.addListener(() => { _port = null; });
  } catch (e) {
    console.warn("[AutoMerge] Port connect failed:", e.message);
  }
}

/* ── Fresh extraction via one-shot message ───────────── */
async function freshExtract(tabId) {
  return new Promise((resolve) => {
    try {
      chrome.tabs.sendMessage(tabId, { action: "extractCode" }, (resp) => {
        if (chrome.runtime.lastError) { resolve(null); return; }
        resolve(resp?.ok ? resp.data : null);
      });
    } catch { resolve(null); }
  });
}

/* ── Inject content script if missing ───────────────── */
async function ensureContentScript(tabId) {
  const alive = await new Promise((resolve) => {
    try {
      chrome.tabs.sendMessage(tabId, { action: "ping" }, (r) => {
        resolve(!chrome.runtime.lastError && r?.ok);
      });
    } catch { resolve(false); }
  });
  if (!alive) {
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ["contentScript.js"] });
      await new Promise(r => setTimeout(r, 300));
    } catch (e) { console.warn("[AutoMerge] inject failed:", e.message); }
  }
}

/* ── Init ────────────────────────────────────────────── */
async function init() {
  // Full UI reset on every open
  _active = null; _lastResult = null; _selectionLocked = false; _analyzing = false;
  hide($("sourceBar")); hide($("previewSection")); hide($("errorState"));
  hide($("loading")); hide($("results")); show($("emptyState"));
  $("analyzeBtn").disabled = true;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) { renderEmpty("Cannot access this tab."); return; }

  await ensureContentScript(tab.id);

  // Connect port for live updates AFTER we ensure the script is running
  connectPort(tab.id);

  // Also do a fresh one-shot extract to get the current state immediately
  // (the port's onMessage fires async — one-shot is faster for initial paint)
  const data = await freshExtract(tab.id);
  handleCodePayload(data);
}

/* ── Analyze ─────────────────────────────────────────── */
async function runAnalysis() {
  if (!_active?.code?.trim() || _analyzing) return;

  _analyzing = true;
  showLoading();
  hideError();

  // CRITICAL: send ONLY the active payload's code — never mix in other content
  const payload = {
    code:          _active.code,              // ONLY the selected/detected snippet
    language:      _active.language || "",
    filename:      _active.filename || "",
    source_type:   _active.source_type || "selection",
    page_url:      _active.page_url || "",
    repo_url:      _active.repo_url || "",
    selected_text: _active.source_type === "selection" ? _active.code : "",
    extension_version: "3.0",
  };

  try {
    const res  = await fetch(`${API_BASE}/extension/analyze`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.status === "error") throw new Error(json.error || "Backend error");

    _lastResult = json.data;
    renderResults(_lastResult);
    chrome.runtime.sendMessage({ action: "setBadge", count: _lastResult.issue_count || 0 });

  } catch (e) {
    hide($("loading"));
    showError(`Analysis failed: ${e.message}`);
  }

  _analyzing = false;
  syncButton();
}

/* ── Render results ──────────────────────────────────── */
function renderResults(r) {
  hide($("loading"));
  show($("results"));

  const cc = confStyle(r.confidence || 0);
  const isClean = r.issue_count === 0;

  $("resultHeader").innerHTML = `
    <div class="result-status" style="color:${isClean ? "#22c55e" : "#ef4444"}">
      ${isClean ? "✓ No issues found" : `⚠ ${r.issue_count} issue${r.issue_count !== 1 ? "s" : ""} found`}
    </div>
    <span class="confidence-pill" style="background:${cc.bg};color:${cc.color}">
      ${Math.round((r.confidence || 0) * 100)}% confidence
    </span>`;

  setSection("issueSection",   "issueBody",   r.issue_summary);
  setSection("rootSection",    "rootBody",    r.root_cause);
  setSection("explainSection", "explainBody", r.explanation,    350);
  setSection("fixSection",     "fixBody",     r.fix_suggestion, 350);
  setSection("learnSection",   "learnBody",   r.learning_notes);

  $("openReport").onclick  = () =>
    chrome.tabs.create({ url: `${SITE_BASE}/extension?report=${r.analysis_id}` });
  $("openDevmitra").onclick = () =>
    chrome.tabs.create({ url: `${SITE_BASE}/?devmitra=open&context=extension&id=${r.analysis_id}` });
}

function setSection(sectionId, bodyId, content, maxLen) {
  const text = (content || "").trim();
  if (!text) { hide($(sectionId)); return; }
  $(bodyId).textContent = maxLen ? text.slice(0, maxLen) : text;
  show($(sectionId));
}

/* ── Event wiring ────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", init);

document.addEventListener("click", (e) => {
  const btn = e.target.closest("#analyzeBtn");
  if (btn && !btn.disabled) { runAnalysis(); return; }
  if (e.target.id === "reDetect") {
    _selectionLocked = false;   // allow re-scan to override stale selection
    _lastResult = null;
    init();
  }
  if (e.target.id === "openHistory")
    chrome.tabs.create({ url: `${SITE_BASE}/extension` });
});
