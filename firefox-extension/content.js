// AutoKetik - content script (versi perbaikan)
//
// Perubahan utama dari versi sebelumnya:
//  - insert()/deleteChar() memakai document/window milik elemen target (ownerDocument),
//    bukan milik halaman utama. Ini penyebab utama gagal mengetik di iframe Google Docs.
//  - Event "input" buatan hanya dikirim bila execCommand gagal (tidak lagi ganda).
//  - Kegagalan tidak lagi diam-diam: error dan kegagalan input berulang dilaporkan ke UI.
//  - Seed dikembalikan setelah selesai, range() menangani kolom kosong,
//    jeda (pause) benar-benar menghentikan waktu, dan variabel `speed` sekarang dipakai.
//  - Hanya frame yang memegang fokus yang mengetik; pesan error hanya dari frame utama.
//
// Ubah DEBUG ke false jika log di Console (F12) sudah tidak diperlukan.
const DEBUG = true;

const API = globalThis.browser ?? globalThis.chrome;
const ORIGINAL_RANDOM = Math.random;

const t = (key, subs = [], fallback = "") => {
    try {
        const msg = API.i18n ? API.i18n.getMessage(key, subs) : "";
        return msg || fallback || key;
    } catch {
        return fallback || key;
    }
};

const neighbors = {
    q: "wa",
    w: "qes",
    e: "wrd",
    r: "etf",
    t: "ryg",
    y: "tuh",
    u: "yij",
    i: "uok",
    o: "ipl",
    p: "o",
    a: "qwsz",
    s: "awedxz",
    d: "serfcx",
    f: "drtgvc",
    g: "ftyhbv",
    h: "gyujnb",
    j: "huikmn",
    k: "jiolm",
    l: "kop",
    z: "asx",
    x: "zsdc",
    c: "xdfv",
    v: "cfgb",
    b: "vghn",
    n: "bhjm",
    m: "njk",
};

let state = "idle"; // idle | running | paused
let token = 0; // naik setiap START/STOP untuk membatalkan run lama
let seededBy = 0; // token run yang mengganti Math.random
let childClaimed = false; // frame utama: apakah ada iframe yang mengambil alih pengetikan
const progress = { i: 0, total: 0 };

function dbg(...args) {
    if (DEBUG) console.debug("[AutoKetik]", ...args);
}

// ---------------------------------------------------------------- utilitas

function range(s, fallback) {
    if (typeof s === "number" && Number.isFinite(s))
        return [s, s];
    const str = String(s ?? "").trim();
    if (!str) return fallback;
    const a = str
        .split("-")
        .map((x) => x.trim())
        .filter((x) => x !== "")
        .map(Number)
        .filter(Number.isFinite);
    if (a.length === 0) return fallback;
    return a.length === 1
        ? [a[0], a[0]]
        : [Math.min(...a), Math.max(...a)];
}

function rand(a, b) {
    return a + Math.random() * (b - a);
}

async function waitWhilePaused(t) {
    while (state === "paused" && t === token) {
        await new Promise((r) => setTimeout(r, 60));
    }
}

// Menunggu `ms` milidetik. Waktu tidak berjalan saat dijeda, dan langsung
// berhenti bila run dibatalkan (token berubah).
async function sleep(ms, t) {
    let remaining = ms;
    let last = performance.now();
    while (remaining > 0) {
        if (t !== token) return;
        if (state === "paused") {
            await waitWhilePaused(t);
            last = performance.now();
            continue;
        }
        await new Promise((r) =>
            setTimeout(r, Math.min(remaining, 50)),
        );
        const now = performance.now();
        remaining -= now - last;
        last = now;
    }
}

function notifyStatus(statusData) {
    try {
        API.runtime
            .sendMessage({
                type: "AUTOKETIK_STATUS",
                ...statusData,
            })
            .catch(() => {});
    } catch {
        // Popup atau sidebar mungkin tidak terbuka, abaikan.
    }
}

// ---------------------------------------------------------------- deteksi elemen

function isEditable(el) {
    if (
        !el ||
        el === document.body ||
        el === document.documentElement
    )
        return false;
    const tag = el.tagName;
    if (tag === "INPUT") {
        const nonText = [
            "button",
            "checkbox",
            "color",
            "file",
            "hidden",
            "image",
            "radio",
            "range",
            "reset",
            "submit",
        ];
        return (
            !nonText.includes(
                (el.type || "").toLowerCase(),
            ) &&
            !el.readOnly &&
            !el.disabled
        );
    }
    if (tag === "TEXTAREA") {
        return !el.readOnly && !el.disabled;
    }
    if (el.isContentEditable) return true;
    const ce = el.getAttribute?.("contenteditable");
    if (
        ce === "" ||
        ce === "true" ||
        ce === "plaintext-only"
    )
        return true;
    if (el.getAttribute?.("role") === "textbox")
        return true;
    const dm = el.ownerDocument?.designMode;
    if (dm && dm.toLowerCase() === "on") return true;
    return false;
}

// Mengikuti activeElement ke dalam shadow root dan iframe satu origin.
function deepActiveElement(doc) {
    let el = doc.activeElement;
    for (let guard = 0; guard < 10; guard++) {
        if (
            el &&
            el.shadowRoot &&
            el.shadowRoot.activeElement
        ) {
            el = el.shadowRoot.activeElement;
            continue;
        }
        if (
            el &&
            (el.tagName === "IFRAME" ||
                el.tagName === "FRAME")
        ) {
            try {
                const inner = el.contentDocument;
                if (inner && inner.activeElement) {
                    el = inner.activeElement;
                    continue;
                }
            } catch {
                // iframe lintas origin: dihandle oleh content script di frame itu sendiri
            }
        }
        break;
    }
    return el;
}

function getActiveEditableElement() {
    const el = deepActiveElement(document);
    if (isEditable(el)) return el;

    const focused = document.querySelector(
        "input:focus, textarea:focus, [contenteditable='true']:focus, [role='textbox']:focus",
    );
    if (isEditable(focused)) return focused;

    // Google Docs: target input tersembunyi (iframe satu origin)
    const docsIframe = document.querySelector(
        "iframe.docs-texteventtarget-iframe",
    );
    if (docsIframe) {
        try {
            const doc =
                docsIframe.contentDocument ||
                docsIframe.contentWindow.document;
            if (doc && doc.body) return doc.body;
        } catch {
            // abaikan
        }
    }

    return null;
}

function isDocsTarget(el) {
    try {
        return Boolean(
            el.ownerDocument?.defaultView?.frameElement?.classList?.contains(
                "docs-texteventtarget-iframe",
            ),
        );
    } catch {
        return false;
    }
}

// ---------------------------------------------------------------- typo

function typoAt(text, i) {
    const ch = text[i];
    const n = text[i + 1] || "";
    const k = Math.random();
    if (k < 0.55 && neighbors[ch.toLowerCase()]) {
        const x = neighbors[ch.toLowerCase()];
        return [x[Math.floor(Math.random() * x.length)], 1];
    }
    if (
        k < 0.7 &&
        /[a-z]/i.test(n) &&
        n.toLowerCase() !== ch.toLowerCase()
    ) {
        return [n + ch, 2];
    }
    if (k < 0.87) {
        return [ch + ch, 1];
    }
    return ["", 1];
}

// ---------------------------------------------------------------- input

function keyInit(ch) {
    let code = "";
    let keyCode = 0;
    if (ch === "\n") {
        code = "Enter";
        keyCode = 13;
    } else if (ch === " ") {
        code = "Space";
        keyCode = 32;
    } else if (/^[a-zA-Z]$/.test(ch)) {
        code = `Key${ch.toUpperCase()}`;
        keyCode = ch.toUpperCase().charCodeAt(0);
    } else if (/^[0-9]$/.test(ch)) {
        code = `Digit${ch}`;
        keyCode = ch.charCodeAt(0);
    }
    return {
        key: ch === "\n" ? "Enter" : ch,
        code,
        keyCode,
        which: keyCode,
        bubbles: true,
        cancelable: true,
        composed: true,
    };
}

// Google Docs (hasil uji manual di Firefox):
//  - Huruf/karakter: HANYA rangkaian event komposisi IME yang diterima.
//    execCommand, paste buatan, dan beforeinput diabaikan Docs.
//  - Enter: event keyboard buatan (keydown, keypress, keyup) diterima, dan komposisi "\n" juga.
//    Event keyboard dipilih karena berperilaku seperti menekan Enter sungguhan.
//  - Backspace: event keyboard buatan (keydown, keypress, keyup) diterima.
// DOCS_ENTER: "key" (default) | "composition" | "none"
const DOCS_ENTER = "key";

function composeDocs(target, data) {
    target.dispatchEvent(
        new CompositionEvent("compositionstart", {
            bubbles: true,
        }),
    );
    target.dispatchEvent(
        new CompositionEvent("compositionupdate", {
            data,
            bubbles: true,
        }),
    );
    target.dispatchEvent(
        new CompositionEvent("compositionend", {
            data,
            bubbles: true,
        }),
    );
}

function fireKeys(target, init, withPress) {
    target.dispatchEvent(
        new KeyboardEvent("keydown", init),
    );
    if (withPress)
        target.dispatchEvent(
            new KeyboardEvent("keypress", init),
        );
    target.dispatchEvent(new KeyboardEvent("keyup", init));
}

// Ambil struktur HTML seperti parser Python: paragraf, heading, run inline, alignment.
function htmlDocument(source) {
    const parsed = new DOMParser().parseFromString(source, "text/html");
    const root = parsed.body;
    const blocks = [];
    const cssRules = {};
    for (const styleTag of parsed.querySelectorAll("style")) {
        for (const [, selector, body] of styleTag.textContent.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
            const props = Object.fromEntries([...body.matchAll(/([\w-]+)\s*:\s*([^;]+)/g)].map(m => [m[1].toLowerCase(), m[2].trim()]));
            for (const cls of selector.matchAll(/\.([\w-]+)/g)) cssRules[cls[1]] = { ...(cssRules[cls[1]] || {}), ...props };
        }
    }
    const cssOf = el => {
        const props = {};
        for (const cls of el.classList || []) Object.assign(props, cssRules[cls] || {});
        for (const rule of (el.getAttribute("style") || "").split(";")) {
            const m = rule.match(/^\s*([\w-]+)\s*:\s*(.*?)\s*$/);
            if (m) props[m[1].toLowerCase()] = m[2];
        }
        return props;
    };
    const pt = v => {
        const m = String(v || "").match(/(-?[\d.]+)\s*(pt|px|in|cm)?/i);
        return m ? Number(m[1]) * ({pt:1,px:.75,in:72,cm:28.35}[(m[2] || "pt").toLowerCase()] || 1) : 0;
    };
    const walk = (node, style, runs) => {
        if (node.nodeType === 3) { if (node.nodeValue) runs.push({ text: node.nodeValue.replace(/\u00a0/g, " "), style }); return; }
        if (node.nodeType !== 1) return;
        const tag = node.tagName.toLowerCase();
        if (["script", "style", "title"].includes(tag)) return;
        if (tag === "br") { runs.push({ text: "\v", style }); return; }
        const s = { ...style };
        if (["b", "strong"].includes(tag)) s.b = true;
        if (["i", "em"].includes(tag)) s.i = true;
        if (tag === "u") s.u = true;
        const css = cssOf(node);
        if (/^(bold|bolder|[6-9]00)$/i.test(css["font-weight"] || "")) s.b = true;
        if (/italic/i.test(css["font-style"] || "")) s.i = true;
        if (/underline/i.test(css["text-decoration"] || "")) s.u = true;
        for (const child of node.childNodes) walk(child, s, runs);
    };
    // Google Docs exports frequently wrap every paragraph in one or more divs;
    // use semantic paragraph/list elements first and ignore the export's <head> CSS.
    let leaves = [...root.querySelectorAll("p,h1,h2,h3,h4,h5,h6,li")];
    if (!leaves.length) {
        const topBlocks = [...root.children].filter(el => /^(DIV|SECTION|ARTICLE|BLOCKQUOTE)$/.test(el.tagName));
        leaves = topBlocks.length ? topBlocks : [root];
    }
    for (const el of leaves) {
        const tag = el.tagName.toLowerCase();
        const runs = []; walk(el, {}, runs);
        let text = runs.map(r => r.text).join("").replace(/[\r\n]+/g, " ");
        if (tag === "br") text += "\n";
        if (!text.trim()) continue;
        const css = cssOf(el);
        const align = (css["text-align"] || "left").toLowerCase();
        blocks.push({ heading: /^h[1-6]$/.test(tag) ? Number(tag[1]) : 0,
            align: ["center","right","justify"].includes(align) ? align : "left",
            left: pt(css["margin-left"]), first: pt(css["text-indent"]), runs });
    }
    if (!blocks.length) return { text: root.textContent || source, events: [] };
    let text = "", events = [];
    for (const [bi, b] of blocks.entries()) {
        events.push({ at: text.length, heading: b.heading, align: b.align, left:b.left, first:b.first, style: { b:false,i:false,u:false } });
        for (const run of b.runs) {
            events.push({ at: text.length, style: run.style }); text += run.text;
        }
        if (bi < blocks.length - 1) text += "\n";
    }
    return { text, events };
}

async function applyFormat(target, event, current, t) {
    const keys = event.heading !== undefined ? [["Alt", String(event.heading)]] : [];
    for (const [mod, key] of keys) formatKey(target, key, ["Control", mod]);
    if (event.align && event.align !== current.align) {
        const key = { left:"l",center:"e",right:"r",justify:"j" }[event.align];
        formatKey(target, key, ["Control","Shift"]); current.align = event.align;
    }
    const left = Math.max(0, Math.round((event.left || 0) / 36));
    const first = Math.max(0, Math.round((event.first || 0) / 36));
    for (let n = current.left || 0; n < left; n++) formatKey(target, "]", ["Control"]);
    for (let n = left; n < (current.left || 0); n++) formatKey(target, "[", ["Control"]);
    current.left = left;
    for (let n = 0; n < first; n++) formatKey(target, "Tab", []);
    if (event.style) for (const k of ["b","i","u"]) {
        if (Boolean(event.style[k]) !== Boolean(current[k])) {
            formatKey(target, k, ["Control"]); current[k] = Boolean(event.style[k]);
        }
    }
    await sleep(80, t);
}

function formatKey(target, key, modifiers) {
    const code = /^[a-z]$/i.test(key) ? `Key${key.toUpperCase()}` : key === "]" ? "BracketRight" : key === "[" ? "BracketLeft" : key === "Tab" ? "Tab" : `Digit${key}`;
    const keyCode = /^[a-z]$/i.test(key) ? key.toUpperCase().charCodeAt(0) : key === "]" ? 221 : key === "[" ? 219 : key === "Tab" ? 9 : Number(key) + 48;
    const init = { key, code, keyCode, which:keyCode, bubbles:true, cancelable:true, composed:true,
        ctrlKey:modifiers.includes("Control"), altKey:modifiers.includes("Alt"), shiftKey:modifiers.includes("Shift") };
    target.dispatchEvent(new KeyboardEvent("keydown", init));
    target.dispatchEvent(new KeyboardEvent("keyup", init));
}

// Mengembalikan true bila karakter berhasil dimasukkan.
function insert(target, ch) {
    const doc = target.ownerDocument || document;
    const win = doc.defaultView || window;
    const docs = isDocsTarget(target);
    const tag = target.tagName;
    const isField = tag === "INPUT" || tag === "TEXTAREA";

    try {
        target.focus();
    } catch {}

    const init = keyInit(ch);
    let inserted = false;
    let usedFallback = false;

    if (docs) {
        if (ch === "\v") {
            fireKeys(target, { ...keyInit("\n"), shiftKey:true }, true);
        } else if (ch === "\n") {
            if (DOCS_ENTER === "composition")
                composeDocs(target, "\n");
            else if (DOCS_ENTER === "key")
                fireKeys(target, init, true);
        } else {
            composeDocs(target, ch);
        }
        return true; // Docs tidak memberi umpan balik; hasilnya harus dilihat di dokumen
    }

    // Di Google Docs event keyboard buatan tidak berpengaruh untuk huruf biasa,
    // jadi hanya dikirim di tempat lain.
    if (!docs)
        target.dispatchEvent(
            new KeyboardEvent("keydown", init),
        );
    if (!docs)
        target.dispatchEvent(
            new KeyboardEvent("keypress", init),
        );

    if (isField) {
        try {
            inserted = doc.execCommand(
                "insertText",
                false,
                ch,
            );
        } catch {}
        if (!inserted) {
            usedFallback = true;
            if (typeof target.setRangeText === "function") {
                const start =
                    target.selectionStart ??
                    target.value.length;
                const end = target.selectionEnd ?? start;
                target.setRangeText(ch, start, end, "end");
                inserted = true;
            } else {
                target.value = (target.value || "") + ch;
                inserted = true;
            }
        }
    } else {
        try {
            if (ch === "\n") {
                inserted =
                    doc.execCommand("insertParagraph") ||
                    doc.execCommand("insertLineBreak");
            } else {
                inserted = doc.execCommand(
                    "insertText",
                    false,
                    ch,
                );
            }
        } catch {}

        if (!inserted && docs) {
            // Docs tidak menerima execCommand: coba Enter lewat event keyboard,
            // selebihnya dilaporkan sebagai gagal (tidak ada gunanya mengubah DOM iframe).
            if (ch === "\n") fireKeys(target, init, true);
            dbg(
                "execCommand ditolak di Docs untuk",
                JSON.stringify(ch),
            );
            return false;
        }

        if (!inserted) {
            usedFallback = true;
            const sel = win.getSelection();
            if (sel) {
                if (
                    !sel.rangeCount ||
                    !target.contains(sel.anchorNode)
                ) {
                    const r = doc.createRange();
                    r.selectNodeContents(target);
                    r.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(r);
                }
                const r = sel.getRangeAt(0);
                r.deleteContents();
            const node =
                    ch === "\n" || ch === "\v"
                        ? doc.createElement("br")
                        : doc.createTextNode(ch);
                r.insertNode(node);
                r.setStartAfter(node);
                r.collapse(true);
                sel.removeAllRanges();
                sel.addRange(r);
                inserted = true;
            }
        }
    }

    // Event input buatan hanya bila DOM diubah manual; execCommand sudah memicunya sendiri.
    if (usedFallback && inserted) {
        target.dispatchEvent(
            new InputEvent("input", {
                bubbles: true,
                cancelable: true,
                composed: true,
                inputType: "insertText",
                data: ch,
            }),
        );
    }

    if (!docs)
        target.dispatchEvent(
            new KeyboardEvent("keyup", init),
        );
    return inserted;
}

// Mengembalikan true bila penghapusan berhasil.
function deleteChar(target) {
    const doc = target.ownerDocument || document;
    const win = doc.defaultView || window;
    const docs = isDocsTarget(target);
    const tag = target.tagName;

    try {
        target.focus();
    } catch {}

    const bs = {
        key: "Backspace",
        code: "Backspace",
        keyCode: 8,
        which: 8,
        bubbles: true,
        cancelable: true,
        composed: true,
    };

    if (docs) {
        // Docs hanya membaca Backspace dari event keyboard (diuji manual); jangan campur execCommand.
        fireKeys(target, bs, true);
        return true; // tidak ada umpan balik; hasilnya harus dilihat di dokumen
    }

    target.dispatchEvent(new KeyboardEvent("keydown", bs));

    let deleted = false;
    try {
        deleted = doc.execCommand("delete");
    } catch {}

    let usedFallback = false;
    if (!deleted && !docs) {
        usedFallback = true;
        if (tag === "INPUT" || tag === "TEXTAREA") {
            const p =
                target.selectionStart ??
                target.value.length;
            if (p > 0) {
                target.setRangeText("", p - 1, p, "end");
                deleted = true;
            }
        } else {
            const sel = win.getSelection();
            if (sel && sel.rangeCount > 0) {
                try {
                    if (typeof sel.modify === "function") {
                        sel.modify(
                            "extend",
                            "backward",
                            "character",
                        );
                        sel.deleteFromDocument();
                        deleted = true;
                    } else {
                        // Cadangan manual: hapus satu karakter di node teks sebelum kursor.
                        const r = sel.getRangeAt(0);
                        let node = r.startContainer;
                        let off = r.startOffset;
                        if (
                            node.nodeType !== 3 &&
                            off > 0
                        ) {
                            // kursor berada di node elemen: ambil node teks tepat sebelum kursor
                            const prevNode =
                                node.childNodes[off - 1];
                            if (
                                prevNode &&
                                prevNode.nodeType === 3
                            ) {
                                node = prevNode;
                                off = prevNode.length;
                            }
                        }
                        if (
                            r.collapsed &&
                            node.nodeType === 3 &&
                            off > 0
                        ) {
                            const nr = doc.createRange();
                            nr.setStart(node, off - 1);
                            nr.setEnd(node, off);
                            nr.deleteContents();
                            if (
                                node.length === 0 &&
                                node.parentNode
                            ) {
                                const parent =
                                    node.parentNode;
                                const idx =
                                    Array.prototype.indexOf.call(
                                        parent.childNodes,
                                        node,
                                    );
                                parent.removeChild(node);
                                nr.setStart(parent, idx);
                            }
                            nr.collapse(true);
                            sel.removeAllRanges();
                            sel.addRange(nr);
                            deleted = true;
                        }
                    }
                } catch {}
            }
        }
    }

    if (usedFallback && deleted) {
        target.dispatchEvent(
            new InputEvent("input", {
                bubbles: true,
                cancelable: true,
                composed: true,
                inputType: "deleteContentBackward",
            }),
        );
    }

    target.dispatchEvent(new KeyboardEvent("keyup", bs));
    return deleted;
}

// ---------------------------------------------------------------- koordinasi antar frame

// Frame anak yang memegang fokus memberi tahu frame utama agar tidak
// menampilkan pesan "kolom tidak aktif" yang salah.
window.addEventListener("message", (ev) => {
    if (
        window === window.top &&
        ev.data &&
        ev.data.__autoketik === "claimed"
    ) {
        childClaimed = true;
    }
});

// ---------------------------------------------------------------- loop utama

async function run(msg) {
    const t = ++token;
    state = "running";
    childClaimed = false;
    const isTop = window === window.top;

    try {
        const o = msg.options || msg;
        const sourceText = msg.text || "";
        // Do not rely solely on the popup's transient file/source flag. It is lost
        // when the popup closes and older saved HTML can be restored from storage.
        const looksHtml = o.html || /<!doctype\s+html|<html\b|<(?:p|h[1-6]|div|li|span)\b/i.test(sourceText);
        const formatted = looksHtml ? htmlDocument(sourceText) : { text: sourceText, events: [] };
        const chars = Array.from(formatted.text);
        if (looksHtml) {
            for (const event of formatted.events) {
                event.at = Array.from(formatted.text.slice(0, event.at)).length;
            }
        }
        if (!chars.length) {
            state = "idle";
            if (isTop)
                notifyStatus({
                    state: "idle",
                    text: t("typingEmptyText", [], "Teks kosong."),
                });
            return;
        }

        const delaySec = Math.max(0, Number(o.delay) || 0);

        for (let d = delaySec; d > 0 && t === token; d--) {
            if (isTop) {
                notifyStatus({
                    state: "counting",
                    countdown: d,
                    text: t("typingCountdown", [String(d)], `Hitung mundur ${d} detik... Fokuskan kursor ke kolom tujuan.`),
                });
            }
            await sleep(1000, t);
        }

        if (t !== token) return;

        const target = getActiveEditableElement();
        if (!target) {
            state = "idle";
            if (!isTop) return; // frame tanpa fokus: diam saja

            // Beri waktu bagi iframe lintas origin untuk mengambil alih.
            await new Promise((r) => setTimeout(r, 800));
            if (t !== token || childClaimed) return;

            notifyStatus({
                state: "error",
                text: t("typingTargetError", [], "Gagal: Kolom input tidak aktif. Klik kolom teks atau editor di halaman lalu ulangi."),
            });
            return;
        }

        if (!isTop) {
            try {
                window.top.postMessage(
                    { __autoketik: "claimed" },
                    "*",
                );
            } catch {}
        } else if (target.ownerDocument !== document) {
            // Target ada di dalam iframe. Bila iframe itu punya content script sendiri
            // (terjadi di Google Docs), biarkan frame itu yang mengetik agar tidak ganda.
            await new Promise((r) => setTimeout(r, 400));
            if (t !== token) return;
            if (childClaimed) {
                dbg(
                    "frame utama mengalah ke content script di iframe",
                );
                state = "idle";
                return;
            }
        }

        const docsMode = isDocsTarget(target);
        dbg(
            "target:",
            target.tagName,
            "docsMode:",
            docsMode,
            "frame utama:",
            isTop,
        );

        const wr = range(o.wpm, [60, 60]);
        const tr = range(o.typo, [0.03, 0.03]);
        const te = range(o.thinkEvery, [8, 25]);
        const tp = range(o.thinkPause, [1.5, 6]);
        const tw = range(o.typoWords, [1, 3]);
        const td = range(o.typoDelay, [0.8, 2]);

        if (o.seed) {
            let x = Number(o.seed) >>> 0;
            seededBy = t;
            Math.random = () =>
                (x = (x * 1664525 + 1013904223) >>> 0) /
                4294967296;
        }

        const docsModeText = docsMode ? t("typingDocsMode", [], " (mode Google Docs)") : "";
        notifyStatus({
            state: "running",
            text: t("typingStarted", [docsModeText, String(chars.length)], `Mengetik dimulai${docsModeText}... (0/${chars.length})`),
        });

        progress.i = 0;
        progress.total = chars.length;

        const start = performance.now();
        let speed = 1;
        let words = 0;
        let next = rand(...te);
        let prev = "";
        let fails = 0;
        let typoEnabled = true;
        let warnedEnter = false;
        const formatState = { b:false, i:false, u:false, align:"left" };
        let formatIndex = 0;

        const put = (c) => {
            const ok = insert(target, c);
            if (c === "\n") {
                if (!ok && !warnedEnter) {
                    warnedEnter = true;
                    notifyStatus({
                        state: "running",
                        text: t("typingWarnEnter", [], "Peringatan: Enter tidak diterima editor ini."),
                    });
                }
            } else if (ok) {
                fails = 0;
            } else {
                fails++;
            }
            return ok;
        };

        const abortInput = () => {
            token++;
            state = "idle";
            notifyStatus({
                state: "error",
                text: docsMode
                    ? t("typingErrorDocs", [], "Gagal: Google Docs menolak input teks. Buka Console (F12) untuk detail.")
                    : t("typingErrorEditor", [], "Gagal: editor menolak input teks. Buka Console (F12) untuk detail."),
            });
        };

        for (
            let i = 0;
            i < chars.length && t === token;
            i++
        ) {
            while (formatIndex < formatted.events.length && formatted.events[formatIndex].at === i) {
                const ev = formatted.events[formatIndex++];
                await applyFormat(target, ev, formatState, t);
            }
            progress.i = i;
            await waitWhilePaused(t);
            if (t !== token) break;

            if (fails >= 5) {
                abortInput();
                return;
            }

            const waveDuration = Math.max(
                1,
                Number(o.wave) || 120,
            );
            let phase =
                ((performance.now() - start) /
                    1000 /
                    waveDuration) *
                2 *
                Math.PI;
            if (o.start === "slow") phase += Math.PI;
            const wave = (1 + Math.cos(phase)) / 2;
            const wpm = Math.max(
                5,
                wr[0] + (wr[1] - wr[0]) * wave,
            );
            const prob = tr[0] + (tr[1] - tr[0]) * wave;
            const ch = chars[i];

            // Simulasi typo
            if (
                typoEnabled &&
                prob > 0 &&
                /[a-z]/i.test(ch) &&
                Math.random() < prob
            ) {
                const [wrong, n] = typoAt(chars, i);
                let tail = "";
                let wordsN = Math.floor(rand(...tw));
                for (
                    let j = i + n;
                    j < chars.length &&
                    wordsN > 0 &&
                    !/\n/.test(chars[j]);
                    j++
                ) {
                    tail += chars[j];
                    if (/\s/.test(chars[j])) wordsN--;
                }

                for (const c of wrong + tail) {
                    put(c);
                    await sleep(60000 / (wpm * 5), t);
                }

                await sleep(rand(...td) * 1000, t);

                let allDeleted = true;
                for (
                    let b = 0;
                    b < wrong.length + tail.length;
                    b++
                ) {
                    if (!deleteChar(target))
                        allDeleted = false;
                    await sleep(60, t);
                }

                if (!allDeleted && docsMode) {
                    // Cadangan: bila suatu saat penghapusan dilaporkan gagal, hentikan typo agar tidak ada kesalahan tersisa.
                    typoEnabled = false;
                    notifyStatus({
                        state: "running",
                        text: t("typingWarnTypoDisabled", [], "Peringatan: Docs tidak menerima penghapusan, simulasi typo dimatikan. Periksa kata terakhir."),
                    });
                }

                await sleep(200, t);
                i--;
                continue;
            }

            put(ch);

            let d =
                ((60000 / (wpm * 5)) * rand(0.75, 1.3)) /
                speed;
            if (/[A-Z]/.test(ch)) d *= 1.3;
            if ('!?@#$%^&*()_+{}|:"<>~'.includes(ch))
                d += rand(0.12, 0.3) * 1000;
            if (ch === "\n") d += rand(1000, 3000);
            if (
                ".!?".includes(ch) &&
                /\s/.test(chars[i + 1] || "")
            )
                d += rand(400, 1200);
            if (",;:".includes(ch) && Math.random() < 0.5)
                d += rand(150, 450);

            await sleep(d, t);

            if (i % 10 === 0 || i === chars.length - 1) {
                notifyStatus({
                    state: "running",
                    current: i + 1,
                    total: chars.length,
                    text: `Mengetik: ${i + 1}/${chars.length} karakter (${Math.round(((i + 1) / chars.length) * 100)}%)`,
                });
            }

            if (/\s/.test(ch) && prev && !/\s/.test(prev)) {
                words++;
                speed = Math.max(
                    0.8,
                    Math.min(
                        1.25,
                        speed * rand(0.92, 1.08),
                    ),
                );
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
                text: t("typingFinished", [], "Pengetikan selesai!"),
            });
        }
    } catch (err) {
        console.error("[AutoKetik]", err);
        if (t === token) {
            state = "idle";
            notifyStatus({
                state: "error",
                text: `Error: ${err && err.message ? err.message : err}`,
            });
        }
    } finally {
        if (seededBy === t) {
            Math.random = ORIGINAL_RANDOM;
            seededBy = 0;
        }
    }
}

// ---------------------------------------------------------------- pesan dari popup / sidebar

API.runtime.onMessage.addListener(
    (msg, sender, sendResponse) => {
        if (msg.type === "START") {
            run(msg);
            sendResponse({ ok: true });
        } else if (msg.type === "STOP") {
            token++;
            state = "idle";
            if (window === window.top)
                notifyStatus({
                    state: "idle",
                    text: t("typingStopped", [], "Pengetikan dihentikan."),
                });
            sendResponse({ ok: true });
        } else if (msg.type === "PAUSE") {
            if (state === "running") {
                state = "paused";
                notifyStatus({
                    state: "paused",
                    text: t("typingPaused", [String(progress.i), String(progress.total)], `Pengetikan dijeda (${progress.i}/${progress.total}).`),
                });
            }
            sendResponse({ ok: true });
        } else if (msg.type === "RESUME") {
            if (state === "paused") {
                state = "running";
                notifyStatus({
                    state: "running",
                    text: t("typingResumed", [], "Pengetikan dilanjutkan."),
                });
            }
            sendResponse({ ok: true });
        }
    },
);
