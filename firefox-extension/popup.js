(async function () {
  const API = globalThis.browser ?? globalThis.chrome;

  const t = (key, subs = [], fallback = "") => {
    try {
      const msg = API.i18n ? API.i18n.getMessage(key, subs) : "";
      return msg || fallback || key;
    } catch {
      return fallback || key;
    }
  };

  function localizeHtml() {
    if (!API.i18n) return;
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const msg = API.i18n.getMessage(el.dataset.i18n);
      if (msg) el.textContent = msg;
    });
    document.querySelectorAll("[data-i18n-html]").forEach(el => {
      const msg = API.i18n.getMessage(el.dataset.i18nHtml);
      if (msg) el.innerHTML = msg;
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      const msg = API.i18n.getMessage(el.dataset.i18nPlaceholder);
      if (msg) el.placeholder = msg;
    });
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
      const msg = API.i18n.getMessage(el.dataset.i18nTitle);
      if (msg) el.title = msg;
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach(el => {
      const msg = API.i18n.getMessage(el.dataset.i18nAriaLabel);
      if (msg) el.setAttribute("aria-label", msg);
    });
  }

  localizeHtml();

  const ids = [
    "source", "text", "url", "wpm", "wave", "start",
    "typo", "delay", "seed",
    "wpmMode", "wpmMin", "wpmMax",
    "thinkEvery", "thinkPause",
    "thinkEveryMode", "thinkPauseMode", "thinkEveryMin", "thinkEveryMax", "thinkPauseMin", "thinkPauseMax",
    "typoWords", "typoDelay", "typoWordsMode", "typoDelayMode",
    "typoWordsMin", "typoWordsMax", "typoDelayMin", "typoDelayMax", "noTypo"
  ];

  const $ = id => document.getElementById(id);
  const statusEl = $("status");
  const setStatus = msg => {
    if (statusEl) statusEl.textContent = msg;
  };

  const isHtmlSource = value => /<!doctype\s+html|<html\b|<(?:p|h[1-6]|div|li|span)\b/i.test(value || "");
  function getSourceStats(value) {
    if (!isHtmlSource(value)) {
      const text = value || "";
      return { characters: text.length, words: text.trim().split(/\s+/).filter(Boolean).length };
    }
    const doc = new DOMParser().parseFromString(value, "text/html");
    const blocks = [...doc.body.querySelectorAll("p,h1,h2,h3,h4,h5,h6,li")]
      .map(el => (el.textContent || "").replace(/\u00a0/g, " "))
      .filter(text => text.trim());
    const parts = blocks.length ? blocks : [(doc.body.textContent || "").replace(/\u00a0/g, " ")];
    const content = parts.join("\n");
    return { characters: content.length, words: content.trim().split(/\s+/).filter(Boolean).length };
  }
  function renderDocumentPreview(source) {
    const parsed = new DOMParser().parseFromString(source, "text/html");
    parsed.querySelectorAll("script,iframe,object,embed,form,base,link,meta[http-equiv]").forEach(el => el.remove());
    parsed.querySelectorAll("img,video,audio,source").forEach(el => {
      const url = el.getAttribute("src") || "";
      if (!url.startsWith("data:")) el.remove();
    });
    parsed.querySelectorAll("*").forEach(el => {
      [...el.attributes].forEach(attr => {
        if (/^on/i.test(attr.name) || ((attr.name === "href" || attr.name === "src") && /^\s*javascript:/i.test(attr.value))) el.removeAttribute(attr.name);
      });
    });
    const csp = parsed.createElement("meta");
    csp.httpEquiv = "Content-Security-Policy";
    csp.content = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:";
    parsed.head.prepend(csp);
    const viewport = parsed.createElement("meta");
    viewport.name = "viewport";
    viewport.content = "width=device-width, initial-scale=1";
    parsed.head.append(viewport);
    const fit = parsed.createElement("style");
    fit.textContent = "html,body{min-width:0!important;width:auto!important;margin:0!important;background:#fff!important}body{padding:0!important}.doc-content{box-sizing:border-box!important;width:100%!important;max-width:100%!important;margin:0 auto!important;padding:22px!important}*{box-sizing:border-box}img{max-width:100%;height:auto}";
    parsed.head.append(fit);
    $("documentFrame").srcdoc = "<!doctype html>" + parsed.documentElement.outerHTML;
  }
  function showDocumentPreview() {
    const raw = $("text").value;
    if (!isHtmlSource(raw)) {
      $("documentPreview").classList.add("hidden");
      $("text").classList.remove("hidden");
      return false;
    }
    $("text").dataset.html = "1";
    renderDocumentPreview(raw);
    $("text").classList.add("hidden");
    $("documentPreview").classList.remove("hidden");
    $("toggleSource").textContent = t("toggleSourceHtml", [], "Lihat sumber HTML");
    return true;
  }
  function showRawSource() {
    $("documentPreview").classList.add("hidden");
    $("text").classList.remove("hidden");
    $("toggleSource").textContent = t("toggleSourceDoc", [], "Kembali ke pratinjau dokumen");
    $("text").focus();
  }
  function syncRange(name, save = true) {
    const mode = $(`${name}Mode`).value;
    const min = $(`${name}Min`).value.trim();
    const max = $(`${name}Max`).value.trim();
    const wrap = document.querySelector(`[data-range="${name}"]`);
    wrap.classList.toggle("is-constant", mode === "constant");
    $(`${name}`).value = mode === "constant" ? min : `${min}-${max}`;
    if (save) API.storage.local.set({
      [name]: $(`${name}`).value,
      [`${name}Mode`]: mode,
      [`${name}Min`]: min,
      [`${name}Max`]: max
    });
  }
  function initRangeControls(saved = {}) {
    for (const name of ["wpm", "thinkEvery", "thinkPause", "typoWords", "typoDelay"]) {
      const raw = String(saved[name] ?? $(`${name}`).value);
      const match = raw.match(/^\s*(-?\d+(?:\.\d+)?)\s*(?:-\s*(-?\d+(?:\.\d+)?))?\s*$/);
      if (match) {
        $(`${name}Min`).value = match[1];
        if (match[2] !== undefined) $(`${name}Max`).value = match[2];
      }
      if (saved[`${name}Min`] !== undefined) $(`${name}Min`).value = saved[`${name}Min`];
      if (saved[`${name}Max`] !== undefined) $(`${name}Max`).value = saved[`${name}Max`];
      const mode = saved[`${name}Mode`] || (match && match[2] === undefined ? "constant" : "random");
      $(`${name}Mode`).value = mode;
      syncRange(name, false);
      for (const id of [`${name}Min`, `${name}Max`]) {
        $(`${id}`).addEventListener("input", () => syncRange(name));
        $(`${id}`).addEventListener("change", () => syncRange(name));
      }
      document.querySelectorAll(`[data-range="${name}"] [data-range-mode]`).forEach(button => {
        button.addEventListener("click", () => {
          $(`${name}Mode`).value = button.dataset.rangeMode;
          syncRange(name);
          button.closest("details").open = false;
        });
      });
    }
  }

  function updateSourceVisibility() {
    const src = $("source").value;
    const urlBox = $("urlBox");
    const fileBox = $("fileBox");
    if (urlBox) urlBox.classList.toggle("hidden", src !== "url");
    if (fileBox) fileBox.classList.toggle("hidden", src !== "file");
  }

  // Info tooltip interaction (prevent triggering input & allow click/touch toggle)
  document.querySelectorAll(".info-tip").forEach(tip => {
    tip.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      const wasActive = tip.classList.contains("is-active");
      document.querySelectorAll(".info-tip.is-active").forEach(el => el.classList.remove("is-active"));
      if (!wasActive) tip.classList.add("is-active");
    });
  });
  document.addEventListener("click", () => {
    document.querySelectorAll(".info-tip.is-active").forEach(el => el.classList.remove("is-active"));
  });

  // Load saved values
  let storedSettings = {};
  try {
    const vals = await API.storage.local.get(ids);
    storedSettings = vals;
    for (const id of ids) {
      const el = $(id);
      if (el && vals[id] !== undefined) {
        if (el.type === "checkbox") {
          el.checked = Boolean(vals[id]);
        } else {
          el.value = vals[id];
        }
      }
    }
  } catch (err) {
    console.error("Gagal memuat pengaturan:", err);
  }

  initRangeControls(storedSettings);

  updateSourceVisibility();
  showDocumentPreview();

  // Save changes automatically
  for (const id of ids) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener("change", () => {
      const val = el.type === "checkbox" ? el.checked : el.value;
      API.storage.local.set({ [id]: val });
    });
  }

  $("source").addEventListener("change", updateSourceVisibility);

  // File import
  $("file").addEventListener("change", async e => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        const content = await file.text();
        $("text").value = content;
        $("text").dataset.html = /\.html?$/i.test(file.name) ? "1" : "0";
        if (!showDocumentPreview()) $("text").classList.remove("hidden");
        API.storage.local.set({ text: content });
        const stats = getSourceStats(content);
        const extra = isHtmlSource(content) ? t("statusHtmlNotCounted", [], "; HTML/CSS tidak dihitung") : "";
        setStatus(t("statusFileLoaded", [file.name, stats.characters.toLocaleString(), extra], `File berhasil dimuat: ${file.name} (${stats.characters.toLocaleString()} karakter isi${extra})`));
      } catch (err) {
        setStatus(t("statusFileError", [err.message], `Gagal membaca file: ${err.message}`));
      }
    }
  });

  // Google Docs fetch
  $("fetch").addEventListener("click", async () => {
    const urlVal = $("url").value.trim();
    const match = urlVal.match(/\/document\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      setStatus(t("statusDocsInvalidUrl", [], "URL Google Docs tidak valid. Pastikan link memiliki format https://docs.google.com/document/d/..."));
      return;
    }

    setStatus(t("statusDocsDownloading", [], "Mengunduh teks dari Google Docs..."));
    try {
      const exportUrl = `https://docs.google.com/document/d/${match[1]}/export?format=html`;
      const res = await fetch(exportUrl);
      if (!res.ok) {
        throw new Error(t("statusDocsDownloadError", [], "Gagal mengunduh dokumen. Pastikan akses Google Docs disetel ke publik ('Siapa saja yang memiliki link')."));
      }
      const text = await res.text();
      $("text").value = text;
      $("text").dataset.html = "1";
      showDocumentPreview();
      API.storage.local.set({ text });
      const stats = getSourceStats(text);
      setStatus(t("statusDocsLoaded", [stats.characters.toLocaleString()], `Teks Google Docs berhasil dimuat (${stats.characters.toLocaleString()} karakter isi; HTML/CSS tidak dihitung).`));
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  });

  // Open in Sidebar
  $("openSidebar").addEventListener("click", async () => {
    try {
      if (API.sidebarAction && typeof API.sidebarAction.open === "function") {
        await API.sidebarAction.open();
        window.close();
      } else {
        const res = await API.runtime.sendMessage({ type: "OPEN_SIDEBAR" });
        if (res && res.ok) {
          window.close();
        } else {
          setStatus(t("statusSidebarMenu1", [], "Buka menu browser Firefox > Sidebar > AutoKetik."));
        }
      }
    } catch {
      setStatus(t("statusSidebarMenu2", [], "Buka menu Firefox: Tekan Alt, lalu pilih View > Sidebar > AutoKetik."));
    }
  });

  // Preview text length
  $("preview").addEventListener("click", () => {
    const text = $("text").value;
    if (!text.trim()) {
      setStatus(t("statusTextEmpty", [], "Teks masih kosong. Masukkan atau tempel teks terlebih dahulu."));
      return;
    }
    if (isHtmlSource(text)) showDocumentPreview();
    const stats = getSourceStats(text);
    setStatus(t("statusPreviewStats", [stats.characters.toLocaleString(), stats.words.toLocaleString()], `Pratinjau: ${stats.characters.toLocaleString()} karakter isi | ${stats.words.toLocaleString()} kata.`));
  });
  $("toggleSource")?.addEventListener("click", () => {
    if ($("documentPreview").classList.contains("hidden")) showDocumentPreview();
    else showRawSource();
  });
  $("text").addEventListener("input", () => {
    const html = isHtmlSource($("text").value);
    $("text").dataset.html = html ? "1" : "0";
    API.storage.local.set({ text: $("text").value });
  });

  // Send control commands to content script
  async function sendCommand(type) {
    const text = $("text").value;
    if (type === "START" && !text.trim()) {
      setStatus(t("statusEnterTextFirst", [], "Masukkan atau tempel teks yang ingin diketik terlebih dahulu."));
      return;
    }

    let tabs;
    try {
      tabs = await API.tabs.query({ active: true, currentWindow: true });
    } catch (err) {
      setStatus(t("statusTabDetectError", [err.message], "Gagal mendeteksi tab aktif: " + err.message));
      return;
    }

    const tab = tabs?.[0];
    if (!tab || !tab.id) {
      setStatus(t("statusNoTabFound", [], "Tidak ada tab aktif yang ditemukan."));
      return;
    }

    // Check if on protected browser page
    if (tab.url && (tab.url.startsWith("about:") || tab.url.startsWith("moz-extension:") || tab.url.startsWith("chrome:"))) {
      setStatus(t("statusProtectedPage", [], "Ekstensi tidak dapat berjalan di halaman sistem Firefox (about:). Buka tab halaman web biasa."));
      return;
    }

    const options = {
      wpm: $("wpm").value,
      wave: Number($("wave").value) || 120,
      start: $("start").value,
      typo: $("noTypo").checked ? 0 : $("typo").value,
      delay: Number($("delay").value) || 0,
      seed: $("seed").value,
      thinkEvery: $("thinkEvery").value,
      thinkPause: $("thinkPause").value,
      typoWords: $("typoWords").value,
      typoDelay: $("typoDelay").value
    };
    options.html = $("text").dataset.html === "1" || /<!doctype\s+html|<html\b|<(?:p|h[1-6]|div|li|span)\b/i.test(text);

    try {
      await API.tabs.sendMessage(tab.id, {
        type,
        text,
        options
      });

      if (type === "START") {
        const delaySec = options.delay;
        if (delaySec > 0) {
          setStatus(t("statusCountdown", [String(delaySec)], `Hitung mundur ${delaySec} detik... Segera klik kolom tujuan di halaman!`));
        } else {
          setStatus(t("statusTypingStarted", [], "Pengetikan dimulai pada kolom aktif di halaman."));
        }
      } else {
        setStatus(t("statusCommandSent", [type.toLowerCase()], `Perintah ${type.toLowerCase()} dikirim.`));
      }
    } catch {
      setStatus(t("statusScriptNotActive", [], "Skrip belum aktif di tab ini. Silakan muat ulang (Refresh / F5) tab web Anda lalu coba lagi."));
    }
  }

  $("startBtn").addEventListener("click", () => sendCommand("START"));
  $("pause").addEventListener("click", () => sendCommand("PAUSE"));
  $("resume").addEventListener("click", () => sendCommand("RESUME"));
  $("stop").addEventListener("click", () => sendCommand("STOP"));

  // Real-time status updates from content script
  API.runtime.onMessage.addListener(msg => {
    if (msg.type === "AUTOKETIK_STATUS" && msg.text) {
      setStatus(msg.text);
    }
  });
})();