const API = globalThis.browser ?? globalThis.chrome;

const neighbors = {
  q: "wa", w: "qes", e: "wrd", r: "etf", t: "ryg", y: "tuh", u: "yij", i: "uok", o: "ipl", p: "o",
  a: "qwsz", s: "awedxz", d: "serfcx", f: "drtgvc", g: "ftyhbv", h: "gyujnb", j: "huikmn", k: "jiolm", l: "kop",
  z: "asx", x: "zsdc", c: "xdfv", v: "cfgb", b: "vghn", n: "bhjm", m: "njk"
};

let state = "idle";
let token = 0;
let pausedResolve = null;

function range(s, fallback) {
  if (typeof s === "number") return [s, s];
  const a = String(s ?? fallback).split("-").map(Number).filter(Number.isFinite);
  return a.length === 1 ? [a[0], a[0]] : a.length > 1 ? [Math.min(...a), Math.max(...a)] : fallback;
}

function rand(a, b) {
  return a + Math.random() * (b - a);
}

function sleep(ms, t) {
  return new Promise(resolve => {
    let done = false;
    const timer = setTimeout(() => {
      done = true;
      resolve();
    }, ms);

    const poll = () => {
      if (done) return;
      if (t !== token) {
        done = true;
        clearTimeout(timer);
        resolve();
      } else if (state === "paused") {
        pausedResolve = () => {
          if (!done) {
            done = true;
            clearTimeout(timer);
            resolve();
          }
        };
      } else if (state === "running") {
        setTimeout(poll, 40);
      }
    };
    poll();
  });
}

function notifyStatus(statusData) {
  try {
    API.runtime.sendMessage({ type: "AUTOKETIK_STATUS", ...statusData }).catch(() => {});
  } catch {
    // Popup or sidebar might not be open, ignore error
  }
}

function isEditable(el) {
  if (!el || el === document.body || el === document.documentElement) return false;
  if (el instanceof HTMLInputElement) {
    const nonText = ["button", "checkbox", "color", "file", "hidden", "image", "radio", "range", "reset", "submit"];
    return !nonText.includes((el.type || "").toLowerCase()) && !el.readOnly && !el.disabled;
  }
  if (el instanceof HTMLTextAreaElement) {
    return !el.readOnly && !el.disabled;
  }
  if (el.isContentEditable || el.getAttribute("contenteditable") === "true" || el.getAttribute("contenteditable") === "") {
    return true;
  }
  if (el.getAttribute("role") === "textbox") {
    return true;
  }
  if (el.ownerDocument && el.ownerDocument.designMode && el.ownerDocument.designMode.toLowerCase() === "on") {
    return true;
  }
  return false;
}

function getActiveEditableElement() {
  let el = document.activeElement;
  while (el && el.shadowRoot && el.shadowRoot.activeElement) {
    el = el.shadowRoot.activeElement;
  }
  if (isEditable(el)) return el;

  // Check if activeElement is an iframe
  if (el && (el.tagName === "IFRAME" || el.tagName === "FRAME")) {
    try {
      const doc = el.contentDocument || el.contentWindow.document;
      let inner = doc.activeElement;
      while (inner && inner.shadowRoot && inner.shadowRoot.activeElement) {
        inner = inner.shadowRoot.activeElement;
      }
      if (isEditable(inner)) return inner;
    } catch {
      // Cross-origin iframe
    }
  }

  // Fallback: check query selector for focused editable element
  const focused = document.querySelector("input:focus, textarea:focus, [contenteditable='true']:focus, [role='textbox']:focus");
  if (isEditable(focused)) return focused;

  // Google Docs editor canvas/event target
  const docsIframe = document.querySelector("iframe.docs-texteventtarget-iframe");
  if (docsIframe) {
    try {
      const doc = docsIframe.contentDocument || docsIframe.contentWindow.document;
      if (doc && doc.body) return doc.body;
    } catch {}
  }

  return null;
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

function insert(target, ch) {
  try {
    target.focus();
  } catch {}

  const keyEvent = {
    key: ch,
    code: ch === "\n" ? "Enter" : (ch === " " ? "Space" : (/^[a-zA-Z]$/.test(ch) ? `Key${ch.toUpperCase()}` : (/^[0-9]$/.test(ch) ? `Digit${ch}` : ""))),
    bubbles: true,
    cancelable: true,
    composed: true
  };

  target.dispatchEvent(new KeyboardEvent("keydown", keyEvent));
  target.dispatchEvent(new KeyboardEvent("keypress", keyEvent));

  let inserted = false;
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
    try {
      inserted = document.execCommand("insertText", false, ch);
    } catch {}

    if (!inserted) {
      if (typeof target.setRangeText === "function") {
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? start;
        target.setRangeText(ch, start, end, "end");
        inserted = true;
      } else {
        target.value = (target.value || "") + ch;
        inserted = true;
      }
    }
  } else if (target.isContentEditable || target.getAttribute?.("contenteditable") === "true" || target.ownerDocument?.designMode === "on") {
    try {
      if (ch === "\n") {
        inserted = document.execCommand("insertParagraph") || document.execCommand("insertLineBreak");
      } else {
        inserted = document.execCommand("insertText", false, ch);
      }
    } catch {}

    if (!inserted) {
      const sel = window.getSelection();
      if (sel) {
        if (!sel.rangeCount || !target.contains(sel.anchorNode)) {
          const r = document.createRange();
          r.selectNodeContents(target);
          r.collapse(false);
          sel.removeAllRanges();
          sel.addRange(r);
        }
        const r = sel.getRangeAt(0);
        r.deleteContents();
        const node = document.createTextNode(ch);
        r.insertNode(node);
        r.setStartAfter(node);
        r.collapse(true);
        sel.removeAllRanges();
        sel.addRange(r);
        inserted = true;
      }
    }
  }

  target.dispatchEvent(new InputEvent("input", {
    bubbles: true,
    cancelable: true,
    composed: true,
    inputType: "insertText",
    data: ch
  }));

  target.dispatchEvent(new KeyboardEvent("keyup", keyEvent));
}

function deleteChar(target) {
  try {
    target.focus();
  } catch {}

  const bsEvent = {
    key: "Backspace",
    code: "Backspace",
    keyCode: 8,
    which: 8,
    bubbles: true,
    cancelable: true,
    composed: true
  };

  target.dispatchEvent(new KeyboardEvent("keydown", bsEvent));

  let deleted = false;
  try {
    deleted = document.execCommand("delete");
  } catch {}

  if (!deleted) {
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      const p = target.selectionStart ?? target.value.length;
      if (p > 0) {
        target.setRangeText("", p - 1, p, "end");
      }
    } else if (target.isContentEditable) {
      const sel = window.getSelection();
      if (sel && sel.rangeCount > 0) {
        const r = sel.getRangeAt(0);
        if (r.startOffset > 0) {
          r.setStart(r.startContainer, r.startOffset - 1);
          r.deleteContents();
        }
      }
    }
  }

  target.dispatchEvent(new InputEvent("input", {
    bubbles: true,
    cancelable: true,
    composed: true,
    inputType: "deleteContentBackward"
  }));

  target.dispatchEvent(new KeyboardEvent("keyup", bsEvent));
}

async function run(msg) {
  const t = ++token;
  state = "running";

  const o = msg.options || msg;
  const chars = Array.from(msg.text || "");
  if (!chars.length) {
    state = "idle";
    notifyStatus({ state: "idle", text: "Teks kosong." });
    return;
  }

  const delaySec = Math.max(0, Number(o.delay) || 0);

  // Countdown timer loop to allow user to focus target element
  for (let d = delaySec; d > 0 && t === token; d--) {
    notifyStatus({
      state: "counting",
      countdown: d,
      text: `Hitung mundur ${d} detik... Fokuskan kursor ke kolom tujuan.`
    });
    await sleep(1000, t);
  }

  if (t !== token) return;

  // Find target element after countdown
  let target = getActiveEditableElement();
  if (!target) {
    // If inside an iframe and no focus, quietly return
    if (window !== window.top) return;

    state = "idle";
    notifyStatus({
      state: "error",
      text: "Gagal: Kolom input tidak aktif. Klik kolom teks atau editor di halaman lalu ulangi."
    });
    return;
  }

  const wr = range(o.wpm, [60, 60]);
  const tr = range(o.typo, [0.03, 0.03]).map(Number);
  const te = range(o.thinkEvery, [8, 25]).map(Number);
  const tp = range(o.thinkPause, [1.5, 6]).map(Number);
  const tw = range(o.typoWords, [1, 3]).map(Number);
  const td = range(o.typoDelay, [0.8, 2]).map(Number);

  if (o.seed) {
    let x = Number(o.seed) >>> 0;
    Math.random = () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
  }

  notifyStatus({
    state: "running",
    text: `Mengetik dimulai... (0/${chars.length})`
  });

  const start = performance.now();
  let speed = 1;
  let words = 0;
  let next = rand(...te);
  let prev = "";

  for (let i = 0; i < chars.length && t === token; i++) {
    if (state === "paused") {
      notifyStatus({ state: "paused", text: `Pengetikan dijeda (${i}/${chars.length}).` });
      await new Promise(r => { pausedResolve = r; });
    }
    if (t !== token) break;

    const waveDuration = Math.max(1, Number(o.wave) || 120);
    let phase = ((performance.now() - start) / 1000 / waveDuration) * 2 * Math.PI;
    if (o.start === "slow") phase += Math.PI;
    const wave = (1 + Math.cos(phase)) / 2;
    const wpm = wr[0] + (wr[1] - wr[0]) * wave;
    const prob = tr[0] + (tr[1] - tr[0]) * wave;
    const ch = chars[i];

    // Typo simulation
    if (prob > 0 && /[a-z]/i.test(ch) && Math.random() < prob) {
      const [wrong, n] = typoAt(chars, i);
      let tail = "";
      let wordsN = Math.floor(rand(...tw));
      for (let j = i + n; j < chars.length && wordsN > 0 && !/\n/.test(chars[j]); j++) {
        tail += chars[j];
        if (/\s/.test(chars[j])) wordsN--;
      }

      for (const c of wrong + tail) {
        insert(target, c);
        await sleep(60000 / (wpm * 5), t);
      }

      await sleep(rand(...td) * 1000, t);

      for (let b = 0; b < wrong.length + tail.length; b++) {
        deleteChar(target);
        await sleep(60, t);
      }

      await sleep(200, t);
      i--;
      continue;
    }

    insert(target, ch);

    let d = (60000 / (wpm * 5)) * rand(0.75, 1.3);
    if (/[A-Z]/.test(ch)) d *= 1.3;
    if ("!?@#$%^&*()_+{}|:\"<>~".includes(ch)) d += rand(0.12, 0.3) * 1000;
    if (ch === "\n") d += rand(1000, 3000);
    if (".!?".includes(ch) && /\s/.test(chars[i + 1] || "")) d += rand(400, 1200);
    if (",;:".includes(ch) && Math.random() < 0.5) d += rand(150, 450);

    await sleep(d, t);

    // Send progress every 10 characters or at the end
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

  if (t === token && state === "running") {
    state = "idle";
    notifyStatus({
      state: "idle",
      text: "Pengetikan selesai!"
    });
  }
}

API.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "START") {
    run(msg);
    sendResponse({ ok: true });
  } else if (msg.type === "STOP") {
    token++;
    state = "idle";
    if (pausedResolve) {
      const r = pausedResolve;
      pausedResolve = null;
      r();
    }
    notifyStatus({ state: "idle", text: "Pengetikan dihentikan." });
    sendResponse({ ok: true });
  } else if (msg.type === "PAUSE") {
    state = "paused";
    sendResponse({ ok: true });
  } else if (msg.type === "RESUME") {
    state = "running";
    if (pausedResolve) {
      const r = pausedResolve;
      pausedResolve = null;
      r();
    }
    notifyStatus({ state: "running", text: "Pengetikan dilanjutkan." });
    sendResponse({ ok: true });
  }
});
