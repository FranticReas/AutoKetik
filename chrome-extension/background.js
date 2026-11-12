// AutoKetik - background.js (Chrome MV3)
// Mendukung Native Typing Engine via chrome.debugger untuk Google Docs & Canvas editor

const API = globalThis.browser ?? globalThis.chrome;

let currentRun = {
  token: 0,
  state: "idle", // idle | running | paused
  tabId: null,
  progress: { i: 0, total: 0 }
};

// =========================================================================
// 1. LISTENER PESAN DITEMPATKAN DI PALING ATAS (WAJIB UNTUK CHROME MV3)
// =========================================================================
API.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "NATIVE_CONNECT") {
    ensureAttached(msg.tabId)
      .then(() => sendResponse({ ok: true }))
      .catch(err => {
        console.error("[AutoKetik attach err]", err);
        sendResponse({ ok: false, error: err.message || String(err) });
      });
    return true; // respon asynchronous
  }

  if (msg.type === "NATIVE_START") {
    runNative(msg.tabId, msg.text, msg.options);
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === "NATIVE_STOP") {
    currentRun.token++;
    currentRun.state = "idle";
    if (currentRun.tabId) safeDetach(currentRun.tabId);
    notifyStatus({ state: "idle", text: "Pengetikan dihentikan." });
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === "NATIVE_PAUSE") {
    if (currentRun.state === "running") {
      currentRun.state = "paused";
      notifyStatus({
        state: "paused",
        text: `Pengetikan dijeda (${currentRun.progress.i}/${currentRun.progress.total}).`
      });
    }
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === "NATIVE_RESUME") {
    if (currentRun.state === "paused") {
      currentRun.state = "running";
      notifyStatus({ state: "running", text: "Pengetikan dilanjutkan." });
    }
    sendResponse({ ok: true });
    return true;
  }
});

// Listener jika user menutup banner debugger di atas tab
if (chrome.debugger && chrome.debugger.onDetach) {
  chrome.debugger.onDetach.addListener((source, reason) => {
    if (currentRun.tabId === source.tabId && currentRun.state === "running") {
      currentRun.token++;
      currentRun.state = "idle";
      notifyStatus({
        state: "idle",
        text: "Pengetikan dihentikan (debugger dilepas)."
      });
    }
  });
}

// =========================================================================
// 2. HELPER & ENGINE PENGETIKAN
// =========================================================================
const neighbors = {
  q: "wa", w: "qes", e: "wrd", r: "etf", t: "ryg", y: "tuh", u: "yij", i: "uok", o: "ipl", p: "o",
  a: "qwsz", s: "awedxz", d: "serfcx", f: "drtgvc", g: "ftyhbv", h: "gyujnb", j: "huikmn", k: "jiolm", l: "kop",
  z: "asx", x: "zsdc", c: "xdfv", v: "cfgb", b: "vghn", n: "bhjm", m: "njk",
};

function range(s, fallback) {
  if (typeof s === "number" && Number.isFinite(s)) return [s, s];
  const str = String(s ?? "").trim();
  if (!str) return fallback;
  const a = str.split("-").map(x => x.trim()).filter(x => x !== "").map(Number).filter(Number.isFinite);
  if (a.length === 0) return fallback;
  return a.length === 1 ? [a[0], a[0]] : [Math.min(...a), Math.max(...a)];
}

function rand(a, b) {
  return a + Math.random() * (b - a);
}

function typoAt(text, i) {
  const ch = text[i];
  const n = text[i + 1] || "";
  const k = Math.random();
  if (k < 0.55 && neighbors[ch.toLowerCase()]) {
    const x = neighbors[ch.toLowerCase()];
    return [x[Math.floor(Math.random() * x.length)], 1];
  }
  if (k < 0.7 && /[a-z]/i.test(n) && n.toLowerCase() !== ch.toLowerCase()) {
    return [n + ch, 2];
  }
  if (k < 0.87) {
    return [ch + ch, 1];
  }
  return ["", 1];
}

function notifyStatus(statusData) {
  try {
    chrome.storage.local.set({
      __autoketik_live_status: {
        time: Date.now(),
        ...statusData
      }
    });
  } catch {}
}

async function waitWhilePaused(t) {
  while (currentRun.state === "paused" && t === currentRun.token) {
    await new Promise(r => setTimeout(r, 60));
  }
}

async function sleep(ms, t) {
  let remaining = ms;
  let last = performance.now();
  while (remaining > 0) {
    if (t !== currentRun.token) return;
    if (currentRun.state === "paused") {
      await waitWhilePaused(t);
      last = performance.now();
      continue;
    }
    await new Promise(r => setTimeout(r, Math.min(remaining, 50)));
    const now = performance.now();
    remaining -= now - last;
    last = now;
  }
}

async function ensureAttached(tabId) {
  if (!chrome.debugger) {
    throw new Error("API chrome.debugger tidak tersedia. Pastikan izin debugger di manifest aktif.");
  }
  const target = { tabId: Number(tabId) };
  try {
    await chrome.debugger.attach(target, "1.3");
  } catch (err) {
    if (!err.message?.includes("already attached")) {
      console.error("[AutoKetik attach error]", err);
      throw new Error(err.message || String(err));
    }
  }
}

async function safeDetach(tabId) {
  if (!chrome.debugger) return;
  try {
    await chrome.debugger.detach({ tabId: Number(tabId) });
  } catch {}
}

async function sendChar(tabId, ch) {
  if (ch === "\n") {
    await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
      type: "keyDown",
      code: "Enter",
      key: "Enter",
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13,
      text: "\r",
      unmodifiedText: "\r"
    });
    await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
      type: "keyUp",
      code: "Enter",
      key: "Enter",
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13
    });
  } else {
    await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
      type: "keyDown",
      text: ch,
      unmodifiedText: ch
    });
    await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
      type: "keyUp",
      text: ch,
      unmodifiedText: ch
    });
  }
}

async function sendBackspace(tabId) {
  await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
    type: "keyDown",
    code: "Backspace",
    key: "Backspace",
    windowsVirtualKeyCode: 8,
    nativeVirtualKeyCode: 8
  });
  await chrome.debugger.sendCommand({ tabId }, "Input.dispatchKeyEvent", {
    type: "keyUp",
    code: "Backspace",
    key: "Backspace",
    windowsVirtualKeyCode: 8,
    nativeVirtualKeyCode: 8
  });
}

async function runNative(tabId, text, options) {
  const t = ++currentRun.token;
  currentRun.state = "running";
  currentRun.tabId = tabId;

  const o = options || {};
  const chars = Array.from(text || "");

  if (!chars.length) {
    currentRun.state = "idle";
    notifyStatus({ state: "idle", text: "Teks kosong." });
    return;
  }

  try {
    await ensureAttached(tabId);

    const wr = range(o.wpm, [60, 60]);
    const tr = range(o.typo, [0.03, 0.03]);
    const te = range(o.thinkEvery, [8, 25]);
    const tp = range(o.thinkPause, [1.5, 6]);
    const tw = range(o.typoWords, [1, 3]);
    const td = range(o.typoDelay, [0.8, 2]);

    notifyStatus({
      state: "running",
      text: `Mengetik dimulai... (0/${chars.length})`
    });

    currentRun.progress = { i: 0, total: chars.length };
    const start = performance.now();
    let speed = 1;
    let words = 0;
    let next = rand(...te);
    let prev = "";
    let typoEnabled = Boolean(!o.noTypo && Number(o.typo) > 0);

    for (let i = 0; i < chars.length && t === currentRun.token; i++) {
      currentRun.progress.i = i;
      await waitWhilePaused(t);
      if (t !== currentRun.token) break;

      const waveDuration = Math.max(1, Number(o.wave) || 120);
      let phase = ((performance.now() - start) / 1000 / waveDuration) * 2 * Math.PI;
      if (o.start === "slow") phase += Math.PI;
      const wave = (1 + Math.cos(phase)) / 2;
      const wpm = Math.max(5, wr[0] + (wr[1] - wr[0]) * wave);
      const prob = tr[0] + (tr[1] - tr[0]) * wave;
      const ch = chars[i];

      // Simulasi typo
      if (typoEnabled && prob > 0 && /[a-z]/i.test(ch) && Math.random() < prob) {
        const [wrong, n] = typoAt(chars, i);
        let tail = "";
        let wordsN = Math.floor(rand(...tw));
        for (let j = i + n; j < chars.length && wordsN > 0 && !/\n/.test(chars[j]); j++) {
          tail += chars[j];
          if (/\s/.test(chars[j])) wordsN--;
        }

        for (const c of wrong + tail) {
          await sendChar(tabId, c);
          await sleep(60000 / (wpm * 5), t);
        }

        await sleep(rand(...td) * 1000, t);

        for (let b = 0; b < wrong.length + tail.length; b++) {
          await sendBackspace(tabId);
          await sleep(60, t);
        }

        await sleep(200, t);
        i--;
        continue;
      }

      await sendChar(tabId, ch);

      let d = ((60000 / (wpm * 5)) * rand(0.75, 1.3)) / speed;
      if (/[A-Z]/.test(ch)) d *= 1.3;
      if ('!?@#$%^&*()_+{}|:"<>~'.includes(ch)) d += rand(0.12, 0.3) * 1000;
      if (ch === "\n") d += rand(1000, 3000);
      if (".!?".includes(ch) && /\s/.test(chars[i + 1] || "")) d += rand(400, 1200);
      if (",;:".includes(ch) && Math.random() < 0.5) d += rand(150, 450);

      await sleep(d, t);

      if (i % 10 === 0 || i === chars.length - 1) {
        notifyStatus({
          state: "running",
          current: i + 1,
          total: chars.length,
          text: `Mengetik: ${i + 1}/${chars.length} karakter (${Math.round(((i + 1) / chars.length) * 100)}%)`
        });
      }

      if (/\s/.test(ch) && prev && !/\s/.test(prev)) {
        words++;
        speed = Math.max(0.8, Math.min(1.25, speed * rand(0.92, 1.08)));
        if (words >= next) {
          await sleep(rand(...tp) * 1000, t);
          words = 0;
          next = rand(...te);
        }
      }
      prev = ch;
    }

    if (t === currentRun.token && currentRun.state === "running") {
      currentRun.state = "idle";
      notifyStatus({
        state: "idle",
        text: "Pengetikan selesai!"
      });
    }
  } catch (err) {
    console.error("[AutoKetik Debugger Error]", err);
    if (t === currentRun.token) {
      currentRun.state = "idle";
      notifyStatus({
        state: "error",
        text: `Error Native Engine: ${err.message || err}`
      });
    }
  } finally {
    if (t === currentRun.token) {
      await safeDetach(tabId);
    }
  }
}
