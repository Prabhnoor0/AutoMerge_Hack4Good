/**
 * AutoMerge Debugger — Content Script v3
 *
 * GOLDEN RULE: If user has selected text → selection ALWAYS wins.
 * Nothing else can override an active selection.
 *
 * Priority (strict):
 *   1. window.getSelection() — if non-empty, STOP HERE
 *   2. Focused textarea/input (only if no selection)
 *   3. Focused contenteditable (only if no selection)
 *   4. Monaco editor DOM
 *   5. CodeMirror / ACE editor DOM
 *   6. GitHub code view DOM
 *   7. <pre><code> blocks
 *
 * The cached _current is only used for change-detection.
 * When the popup opens or requests code, we ALWAYS do a fresh sync read.
 */

(function () {
  "use strict";

  /* ── Internal state ──────────────────────────────────── */
  let _lastCodeSent  = "";    // for change detection only
  let _lastValidPayload = null; // caches last good payload if focus is lost
  let _debounceTimer = null;
  let _popupPort     = null;

  /* ── CodePayload factory ─────────────────────────────── */
  function makePayload(source_type, code, opts) {
    opts = opts || {};
    const lines = code.split("\n");
    return {
      source_type:   source_type,
      code:          code,
      language:      opts.language || detectLangFromPage(),
      filename:      opts.filename || extractFilename(),
      page_url:      window.location.href,
      repo_url:      opts.repo_url || extractRepoUrl(),
      selected_text: source_type === "selection" ? code : "",
      method:        opts.method || source_type,
      line_count:    lines.length,
      char_count:    code.length,
      error:         null,
    };
  }

  function emptyPayload(reason) {
    return {
      source_type: "none", code: "", language: "", filename: "",
      page_url: window.location.href, method: "none",
      line_count: 0, char_count: 0,
      error: reason || "No code found. Select code on the page or open a supported editor.",
    };
  }

  /* ── Language detection ──────────────────────────────── */
  function detectLangFromPage() {
    const url = window.location.href.toLowerCase();
    const extMap = { ".py":"python", ".js":"javascript", ".ts":"typescript",
      ".jsx":"javascript", ".tsx":"typescript", ".java":"java",
      ".go":"go", ".rs":"rust", ".rb":"ruby", ".cpp":"cpp",
      ".c.html":"c", ".cs":"csharp", ".php":"php", ".sh":"bash" };
    for (var ext in extMap) { if (url.includes(ext)) return extMap[ext]; }
    // DOM language hint
    var langEl = document.querySelector("[data-canonical-lang]");
    if (langEl) return (langEl.getAttribute("data-canonical-lang") || "").toLowerCase();
    var codeEl = document.querySelector("pre code[class]");
    if (codeEl) {
      var hint = Array.from(codeEl.classList).find(function(c){ return c.startsWith("language-"); });
      if (hint) return hint.slice(9).toLowerCase();
    }
    return "";
  }

  function detectLangFromCode(code) {
    var c = code.slice(0, 600);
    if (/^(def |import |from .* import|class .+:|\s+self\.)/m.test(c)) return "python";
    if (/(interface |: string|: number|: boolean|React\.FC)/m.test(c)) return "typescript";
    if (/^(function |const |let |var |=>\s*{|import .* from)/m.test(c)) return "javascript";
    if (/^(public class |System\.out|void main)/m.test(c)) return "java";
    if (/^(func |package main|fmt\.)/m.test(c)) return "go";
    if (/^(#include|int main\(\))/m.test(c)) return "cpp";
    return "";
  }

  function bestLanguage(code, filename) {
    return detectLangFromPage() || detectLangFromCode(code) ||
           (filename && filename.match(/\.py$/) ? "python" :
            filename && filename.match(/\.(js|jsx)$/) ? "javascript" :
            filename && filename.match(/\.(ts|tsx)$/) ? "typescript" : "");
  }

  /* ── URL helpers ─────────────────────────────────────── */
  function extractFilename() {
    var el = document.querySelector(".final-path, [data-testid='breadcrumb-last-item'], .js-final-path");
    if (el) return el.textContent.trim();
    var title = document.title;
    var m = title.match(/([\w\-]+\.(py|js|ts|jsx|tsx|java|go|rs|rb|php|cpp|c|cs|sh))/);
    return m ? m[1] : "";
  }

  function extractRepoUrl() {
    var m = window.location.href.match(/https:\/\/github\.com\/[^/]+\/[^/]+/);
    return m ? m[0] : "";
  }

  /* ── DETECTOR 1: Selection (HIGHEST PRIORITY) ────────── */
  function trySelection() {
    var text = "";

    // 1. Native Window Selection
    try { 
      var sel = window.getSelection(); 
      if (sel && !sel.isCollapsed && sel.rangeCount > 0) {
        text = sel.toString();
      }
    } catch(e) {}

    // 2. GitHub Custom React Selection (when native is hijacked)
    if (!text || text.trim().length < 2) {
      try {
        var ghSelected = document.querySelectorAll(".react-file-line.highlighted, [data-selected='true'], .blob-code-inner.highlighted");
        if (ghSelected.length > 0) {
          text = Array.from(ghSelected).map(function(el){ return el.textContent || ""; }).join("\n");
        }
      } catch(e) {}
    }

    text = text.replace(/^\n+|\n+$/g, "").replace(/^[ \t]+$/, "");
    if (text.length < 2) return null;

    var fn = extractFilename();
    return makePayload("selection", text, {
      language: bestLanguage(text, fn),
      filename: fn,
      method: "User selection",
    });
  }

  /* ── DETECTOR 2: Focused textarea/input ──────────────── */
  function tryFocusedTextarea() {
    var el = document.activeElement;
    if (!el) return null;
    if (el.tagName !== "TEXTAREA" && !(el.tagName === "INPUT" && el.type === "text")) return null;
    
    // If there is an active selection inside the textarea, prioritize it!
    var selectedVal = "";
    try {
      if (typeof el.selectionStart === "number" && typeof el.selectionEnd === "number" && el.selectionStart !== el.selectionEnd) {
        selectedVal = el.value.substring(el.selectionStart, el.selectionEnd).trim();
      }
    } catch(e) {}
    
    if (selectedVal && selectedVal.length >= 2) {
      return makePayload("selection", selectedVal, {
        language: bestLanguage(selectedVal, extractFilename()),
        method: "Textarea selection",
      });
    }

    // Fallback to the whole textarea if no selection
    var val = (el.value || "").trim();
    if (val.length < 10) return null;
    return makePayload("textarea", val, {
      language: bestLanguage(val, extractFilename()),
      method: "Active textarea (" + el.tagName.toLowerCase() + ")",
    });
  }

  /* ── DETECTOR 3: Contenteditable ─────────────────────── */
  function tryContenteditable() {
    var el = document.activeElement;
    if (!el || !el.isContentEditable) return null;
    var text = (el.innerText || el.textContent || "").trim();
    if (text.length < 10) return null;
    return makePayload("web_editor", text, {
      language: bestLanguage(text, extractFilename()),
      method: "ContentEditable editor",
    });
  }

  /* ── DETECTOR 4: Monaco ──────────────────────────────── */
  function tryMonaco() {
    var lines = document.querySelectorAll(".view-lines .view-line");
    if (lines.length === 0) return null;
    var code = Array.from(lines).map(function(l){ return l.textContent || ""; }).join("\n").trim();
    if (code.length < 10) return null;
    return makePayload("web_editor", code, {
      language: bestLanguage(code, extractFilename()),
      method: "Monaco editor",
    });
  }

  /* ── DETECTOR 5: CodeMirror / ACE ───────────────────── */
  function tryOtherEditor() {
    var cmLines = document.querySelectorAll(".CodeMirror-line, .cm-line");
    if (cmLines.length > 0) {
      var code = Array.from(cmLines).map(function(l){ return l.textContent || ""; }).join("\n").trim();
      if (code.length >= 10)
        return makePayload("web_editor", code, { language: bestLanguage(code, extractFilename()), method: "CodeMirror" });
    }
    var aceLines = document.querySelectorAll(".ace_line");
    if (aceLines.length > 0) {
      var code2 = Array.from(aceLines).map(function(l){ return l.textContent || ""; }).join("\n").trim();
      if (code2.length >= 10)
        return makePayload("web_editor", code2, { language: bestLanguage(code2, extractFilename()), method: "ACE editor" });
    }
    return null;
  }

  /* ── DETECTOR 6: GitHub code view ────────────────────── */
  function tryGitHub() {
    var blobLines = document.querySelectorAll(".blob-code-inner");
    if (blobLines.length > 0) {
      var code = Array.from(blobLines).map(function(l){ return l.textContent || ""; }).join("\n").trim();
      if (code.length < 10) return null;
      var fn = extractFilename();
      return makePayload("github", code, {
        filename: fn, language: bestLanguage(code, fn), method: "GitHub file view",
      });
    }
    var ghPre = document.querySelector(".highlight pre, .blob-wrapper pre");
    if (ghPre) {
      var code2 = (ghPre.textContent || "").trim();
      if (code2.length >= 10) {
        var fn2 = extractFilename();
        return makePayload("github", code2, {
          filename: fn2, language: bestLanguage(code2, fn2), method: "GitHub highlight block",
        });
      }
    }
    return null;
  }

  /* ── DETECTOR 7: Pre/code blocks ─────────────────────── */
  function tryCodeBlocks() {
    var blocks = Array.from(document.querySelectorAll("pre code, pre"))
      .map(function(el) {
        return {
          code: (el.textContent || "").trim(),
          lang: Array.from(el.classList || []).find(function(c){ return c.startsWith("language-"); })?.slice(9) || "",
        };
      })
      .filter(function(b){ return b.code.length >= 20; })
      .sort(function(a, b){ return b.code.length - a.code.length; });
    if (blocks.length === 0) return null;
    var best = blocks[0];
    return makePayload("codeblock", best.code, {
      language: best.lang || bestLanguage(best.code, extractFilename()),
      method: "Code block (" + blocks.length + " on page)",
    });
  }

  /* ── MAIN DETECTOR — selection is an absolute gate ───── */
  function detectCurrentCode() {
    var sel = trySelection();
    if (sel) return sel;

    // Only reach here if NO selection is active
    return tryFocusedTextarea()
        || tryContenteditable()
        || tryMonaco()
        || tryOtherEditor()
        || tryGitHub()
        || tryCodeBlocks()
        || null;
  }

  /* ── Debounced update + notification ─────────────────── */
  function scheduleUpdate(delay) {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(runUpdate, delay || 200);
  }

  function runUpdate() {
    var detected = detectCurrentCode();
    
    // If we lost focus/selection because popup opened, but we had a valid payload, keep it.
    if (!detected && _lastValidPayload && (_lastValidPayload.source_type === "selection" || _lastValidPayload.source_type === "textarea" || _lastValidPayload.source_type === "web_editor")) {
      // Keep using the cached payload if the page just lost focus
      if (document.activeElement === document.body) {
        detected = _lastValidPayload;
      }
    }

    if (detected) {
      _lastValidPayload = detected;
    }

    var codeNow = (detected && detected.code) || "";
    if (codeNow === _lastCodeSent && detected?.source_type === _lastValidPayload?.source_type) return;
    
    _lastCodeSent = codeNow;

    if (_popupPort) {
      try {
        _popupPort.postMessage(detected
          ? { action: "codeUpdated", data: detected }
          : { action: "codeCleared" });
      } catch(e) { _popupPort = null; }
    }
  }

  /* ── Event listeners ─────────────────────────────────── */
  document.addEventListener("selectionchange", function() { scheduleUpdate(80); });
  document.addEventListener("mouseup",         function() { scheduleUpdate(100); });
  document.addEventListener("input",           function() { scheduleUpdate(350); });
  document.addEventListener("keyup",           function() { scheduleUpdate(400); });
  document.addEventListener("focusin",         function() { scheduleUpdate(200); });
  
  // Do NOT update immediately on focusout, because clicking the popup causes focusout
  // and we don't want to clear the payload before the popup can request it.
  document.addEventListener("focusout",        function() { scheduleUpdate(500); });
  
  var _observer = new MutationObserver(function() { scheduleUpdate(500); });
  try { _observer.observe(document.body, { childList: true, subtree: true, characterData: true }); } catch(e) {}

  /* ── Port handler (long-lived connection from popup) ─── */
  chrome.runtime.onConnect.addListener(function(port) {
    if (port.name !== "automerge-popup") return;
    _popupPort = port;

    var fresh = detectCurrentCode();
    // Fallback to last valid if popup stole focus
    if (!fresh && _lastValidPayload) fresh = _lastValidPayload;
    if (fresh) _lastValidPayload = fresh;

    _lastCodeSent = (fresh && fresh.code) || "";
    port.postMessage(fresh
      ? { action: "codeUpdated", data: fresh }
      : { action: "codeCleared" });

    port.onDisconnect.addListener(function() { _popupPort = null; });
  });

  /* ── One-shot message handler (popup extractCode) ────── */
  chrome.runtime.onMessage.addListener(function(request, _sender, sendResponse) {
    if (request.action === "extractCode") {
      var fresh = detectCurrentCode();
      if (!fresh && _lastValidPayload) fresh = _lastValidPayload;
      if (fresh) _lastValidPayload = fresh;
      
      _lastCodeSent = (fresh && fresh.code) || "";
      sendResponse({ ok: true, data: fresh || emptyPayload() });
    }
    if (request.action === "ping") {
      sendResponse({ ok: true });
    }
    return true;
  });

  // Initial scan
  scheduleUpdate(100);

})();
