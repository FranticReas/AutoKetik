(async function () {
  const API = globalThis.browser ?? globalThis.chrome;

  const ids = [
    "source", "text", "url", "wpm", "wave", "start",
    "typo", "delay", "seed", "thinkEvery", "thinkPause",
    "typoWords", "typoDelay", "noTypo"
  ];

  const $ = id => document.getElementById(id);
  const statusEl = $("status");
  const setStatus = msg => {
    if (statusEl) statusEl.textContent = msg;
  };

  function updateSourceVisibility() {
    const src = $("source").value;
    const urlBox = $("urlBox");
    const fileBox = $("fileBox");
    if (urlBox) urlBox.classList.toggle("hidden", src !== "url");
    if (fileBox) fileBox.classList.toggle("hidden", src !== "file");
  }

  // Load saved values
  try {
    const vals = await API.storage.local.get(ids);
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

  updateSourceVisibility();

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
        API.storage.local.set({ text: content });
        setStatus(`File berhasil dimuat: ${file.name} (${content.length} karakter)`);
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
      const exportUrl = `https://docs.google.com/document/d/${match[1]}/export?format=txt`;
      const res = await fetch(exportUrl);
      if (!res.ok) {
        throw new Error("Gagal mengunduh dokumen. Pastikan akses Google Docs disetel ke publik ('Siapa saja yang memiliki link').");
      }
      const text = await res.text();
      $("text").value = text;
      API.storage.local.set({ text });
      setStatus(`Teks Google Docs berhasil dimuat (${text.length} karakter).`);
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
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    setStatus(`Pratinjau: ${text.length} karakter | ${words} kata.`);
  });

  // Send control commands to content script
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
    if (tab.url && (tab.url.startsWith("about:") || tab.url.startsWith("moz-extension:") || tab.url.startsWith("chrome:"))) {
      setStatus("Ekstensi tidak dapat berjalan di halaman sistem Firefox (about:). Buka tab halaman web biasa.");
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

    try {
      await API.tabs.sendMessage(tab.id, {
        type,
        text,
        options
      });

      if (type === "START") {
        const delaySec = options.delay;
        if (delaySec > 0) {
          setStatus(`Hitung mundur ${delaySec} detik... Segera klik dokumen tujuan di halaman!`);
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
