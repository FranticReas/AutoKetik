// content-bridge.js — berjalan di ISOLATED world (default Chrome MV3)
// Tugasnya: jembatan antara popup (chrome.runtime) dan content-main.js (MAIN world)
// via window.postMessage.

const API = globalThis.browser ?? globalThis.chrome;

// Popup → MAIN world
API.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (["START", "STOP", "PAUSE", "RESUME"].includes(msg.type)) {
    window.postMessage({ __autoketik_cmd: msg }, "*");
    sendResponse({ ok: true });
    return true;
  }
});

// MAIN world → Popup
window.addEventListener("message", (ev) => {
  if (ev.source !== window) return;
  if (!ev.data || !ev.data.__autoketik_status) return;
  try {
    API.runtime.sendMessage(ev.data.__autoketik_status, () => {
      // Baca lastError agar tidak muncul peringatan "Unchecked runtime.lastError"
      if (chrome.runtime?.lastError) { /* sengaja diabaikan bila popup tertutup */ }
    });
  } catch {}
});

