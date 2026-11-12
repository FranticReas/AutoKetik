(async function () {
  const API = globalThis.browser ?? globalThis.chrome;

  // Pantau update status dari background secara real-time via storage
  API.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.__autoketik_live_status?.newValue?.text) {
      setStatus(changes.__autoketik_live_status.newValue.text);
    }
  });

  const ids = [
    "source", "text", "url", "wpm", "wave", "start",
    "typo", "delay", "seed", "thinkEvery", "thinkPause",
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
    $("toggleSource").textContent = "Lihat sumber HTML";
    return true;
  }
  function showRawSource() {
    $("documentPreview").classList.add("hidden");
    $("text").classList.remove("hidden");
    $("toggleSource").textContent = "Kembali ke pratinjau dokumen";
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
    for (const name of ["thinkEvery", "thinkPause", "typoWords", "typoDelay"]) {
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
        setStatus(`File berhasil dimuat: ${file.name} (${stats.characters.toLocaleString("id-ID")} karakter isi${isHtmlSource(content) ? "; HTML/CSS tidak dihitung" : ""})`);
      } catch (err) {
        setStatus(`Gagal membaca file: ${err.message}`);
      }
    }
  });

  // Google Docs fetch
  $("fetch").addEventListener("click", async () => {
    const urlVal = $("url").value.trim();
    const match = urlVal.match(/\/document\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      setStatus("URL Google Docs tidak valid. Pastikan link memiliki format https://docs.google.com/document/d/...");
      return;
    }

    setStatus("Mengunduh teks dari Google Docs...");
    try {
      const exportUrl = `https://docs.google.com/document/d/${match[1]}/export?format=html`;
      const res = await fetch(exportUrl);
      if (!res.ok) {
        throw new Error("Gagal mengunduh dokumen. Pastikan akses Google Docs disetel ke publik ('Siapa saja yang memiliki link').");
      }
      const text = await res.text();
      $("text").value = text;
      $("text").dataset.html = "1";
      showDocumentPreview();
      API.storage.local.set({ text });
      const stats = getSourceStats(text);
      setStatus(`Teks Google Docs berhasil dimuat (${stats.characters.toLocaleString("id-ID")} karakter isi; HTML/CSS tidak dihitung).`);
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  });

  // Preview text length
  $("preview").addEventListener("click", () => {
    const text = $("text").value;
    if (!text.trim()) {
      setStatus("Teks masih kosong. Masukkan atau tempel teks terlebih dahulu.");
      return;
    }
    if (isHtmlSource(text)) showDocumentPreview();
    const stats = getSourceStats(text);
    setStatus(`Pratinjau: ${stats.characters.toLocaleString("id-ID")} karakter isi | ${stats.words.toLocaleString("id-ID")} kata.`);
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

  function extractPlainTextFromHtml(source) {
    try {
      const doc = new DOMParser().parseFromString(source, "text/html");
      const blocks = [...doc.body.querySelectorAll("p,h1,h2,h3,h4,h5,h6,li")]
        .map(el => (el.textContent || "").replace(/\u00a0/g, " "))
        .filter(text => text.trim());
      const parts = blocks.length ? blocks : [(doc.body.textContent || "").replace(/\u00a0/g, " ")];
      return parts.join("\n");
    } catch {
      return source;
    }
  }

  // Send control commands to content script or background native engine
  async function sendCommand(type) {
    const text = $("text").value;
    if (type === "START" && !text.trim()) {
      setStatus("Masukkan atau tempel teks yang ingin diketik terlebih dahulu.");
      return;
    }

    let tabs;
    try {
      tabs = await API.tabs.query({ active: true, currentWindow: true });
    } catch (err) {
      setStatus("Gagal mendeteksi tab aktif: " + err.message);
      return;
    }

    const tab = tabs?.[0];
    if (!tab || !tab.id) {
      setStatus("Tidak ada tab aktif yang ditemukan.");
      return;
    }

    // Check if on protected browser page
    if (tab.url && (tab.url.startsWith("about:") || tab.url.startsWith("chrome:") || tab.url.startsWith("chrome-extension:") || tab.url.startsWith("moz-extension:"))) {
      setStatus("Ekstensi tidak dapat berjalan di halaman sistem browser ini. Buka tab halaman web biasa.");
      return;
    }

    const isDocs = Boolean(tab.url && tab.url.includes("docs.google.com"));
    const payloadText = isHtmlSource(text) ? extractPlainTextFromHtml(text) : text;

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
      typoDelay: $("typoDelay").value,
      noTypo: $("noTypo").checked
    };
    options.html = $("text").dataset.html === "1" || isHtmlSource(text);

    // Jika di Google Docs, gunakan Native Typing Engine via chrome.debugger langsung dari popup
    if (isDocs) {
      if (type === "START") {
        try {
          if (!chrome.debugger) {
            setStatus("Error: chrome.debugger API tidak tersedia. Hapus lalu 'Load unpacked' ulang ekstensi di chrome://extensions.");
            return;
          }

          setStatus("Menghubungkan Native Debugger ke Google Docs...");
          
          // Pasang debugger langsung ke tab Google Docs
          try {
            await chrome.debugger.attach({ tabId: tab.id }, "1.3");
          } catch (attachErr) {
            if (!attachErr.message?.includes("already attached")) {
              setStatus("Gagal attach debugger: " + attachErr.message);
              return;
            }
          }

          const delaySec = options.delay;
          for (let d = delaySec; d > 0; d--) {
            setStatus(`Hitung mundur ${d} detik... Klik kursor pada lembar Google Docs!`);
            await new Promise(r => setTimeout(r, 1000));
          }

          setStatus("Sedang mengetik ke Google Docs...");

          const chars = Array.from(payloadText);
          for (let i = 0; i < chars.length; i++) {
            const ch = chars[i];
            if (ch === "\n") {
              await chrome.debugger.sendCommand({ tabId: tab.id }, "Input.dispatchKeyEvent", {
                type: "keyDown", code: "Enter", key: "Enter",
                windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, text: "\r", unmodifiedText: "\r"
              });
              await chrome.debugger.sendCommand({ tabId: tab.id }, "Input.dispatchKeyEvent", {
                type: "keyUp", code: "Enter", key: "Enter",
                windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
              });
            } else {
              await chrome.debugger.sendCommand({ tabId: tab.id }, "Input.dispatchKeyEvent", {
                type: "keyDown", text: ch, unmodifiedText: ch
              });
              await chrome.debugger.sendCommand({ tabId: tab.id }, "Input.dispatchKeyEvent", {
                type: "keyUp", text: ch, unmodifiedText: ch
              });
            }

            // Kecepatan ketik berdasarkan WPM
            const wpmVal = Number(options.wpm) || 60;
            const msPerChar = 60000 / (wpmVal * 5);
            await new Promise(r => setTimeout(r, msPerChar));

            if (i % 5 === 0 || i === chars.length - 1) {
              setStatus(`Mengetik: ${i + 1}/${chars.length} karakter (${Math.round(((i + 1) / chars.length) * 100)}%)`);
            }
          }

          setStatus("Pengetikan Google Docs selesai!");
          try {
            await chrome.debugger.detach({ tabId: tab.id });
          } catch {}

        } catch (err) {
          setStatus("Error Debugger: " + (err.message || err));
          try {
            await chrome.debugger.detach({ tabId: tab.id });
          } catch {}
        }
      } else if (type === "STOP") {
        try {
          await chrome.debugger.detach({ tabId: tab.id });
        } catch {}
        setStatus("Pengetikan dihentikan.");
      }
      return;
    }

    // Untuk web biasa, gunakan Content Script
    try {
      // Hentikan juga background engine jika sempat aktif
      if (type === "STOP") {
        API.runtime.sendMessage({ type: "NATIVE_STOP" }).catch(() => {});
      }

      await API.tabs.sendMessage(tab.id, {
        type,
        text,
        options
      });

      if (type === "START") {
        const delaySec = options.delay;
        if (delaySec > 0) {
          setStatus(`Hitung mundur ${delaySec} detik... Segera klik kolom tujuan di halaman!`);
        } else {
          setStatus("Pengetikan dimulai pada kolom aktif di halaman.");
        }
      } else {
        setStatus(`Perintah ${type.toLowerCase()} dikirim.`);
      }
    } catch {
      setStatus("Skrip belum aktif di tab ini. Silakan muat ulang (Refresh / F5) tab web Anda lalu coba lagi.");
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
