const API = globalThis.browser ?? globalThis.chrome;

API.runtime.onInstalled.addListener(() => {
  console.log("AutoKetik extension installed.");
});

// Listener for messages from popup or elsewhere
API.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "OPEN_SIDEBAR") {
    if (API.sidebarAction && typeof API.sidebarAction.open === "function") {
      API.sidebarAction.open();
      sendResponse({ ok: true });
    } else {
      sendResponse({ ok: false, error: "sidebarAction not supported" });
    }
    return true;
  }
});
