/**
 * AutoMerge Debugger — Background Service Worker
 * Handles extension lifecycle and icon badge updates.
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("[AutoMerge] Extension installed v1.0.0");
});

// Update badge when analysis completes
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === "setBadge") {
    const count = msg.count || 0;
    chrome.action.setBadgeText({ text: count > 0 ? String(count) : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#ef4444" });
  }
  sendResponse({ ok: true });
  return true;
});
