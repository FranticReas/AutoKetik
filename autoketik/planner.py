"""
autoketik.planner - Perencana urutan aksi pengetikan dokumen (teks & format).
"""

import random
import re
from .config import snap_size, SIZES, ALIGN_KEYS, INDENT_STEP, Key


def parse_range(s, cast=float):
    """Mengubah format '60' -> (60,60) atau '40-75' -> (40,75)."""
    vals = [cast(p) for p in str(s).split("-") if p.strip() != ""]
    if not vals:
        raise ValueError("Rentang kosong.")
    if len(vals) == 1:
        vals = vals * 2
    return (min(vals), max(vals))


def plan(blocks, base_size: float, mac: bool, base_spacing=(1.15, 0.0, 0.0),
         break_every=None, break_level=1, chapter_re=None):
    """
    Mengubah list Block dokumen menjadi urutan aksi:
    ("text", str) atau ("hot", (modifier...), tombol) atau ("spacing", ...) atau ("break", ...).
    """
    M = Key.cmd if mac else Key.ctrl
    base = snap_size(base_size)
    st = dict(
        style=0, align="left", size=base, b=False, i=False, u=False,
        first=0, left=0, spc=tuple(base_spacing)
    )
    out = []

    def hot(mods, key, n=1):
        for _ in range(n):
            out.append(("hot", tuple(mods), key))

    def text(s):
        if not s:
            return
        if out and out[-1][0] == "text":
            out[-1] = ("text", out[-1][1] + s)
        else:
            out.append(("text", s))

    list_kind = ""
    list_depth = 0
    n = len(blocks)
    chapters_seen = 0
    next_break = random.randint(*break_every) if break_every else None

    for idx, b in enumerate(blocks):
        nxt = blocks[idx + 1] if idx + 1 < n else None
        empty = not b.text.strip()

        # ---------- istirahat setelah N bab ----------
        if break_every and not empty and not b.lst:
            is_chapter = (1 <= b.heading <= break_level) or bool(
                chapter_re and chapter_re.search(b.text.strip())
            )
            if is_chapter:
                if chapters_seen == next_break:
                    out.append(("break", chapters_seen))
                    next_break += random.randint(*break_every)
                chapters_seen += 1

        # ---------- item list ----------
        if b.lst and not empty:
            if list_kind != b.lst:
                if st["style"] != 0:
                    hot((M, Key.alt), "0")
                    st["style"], st["size"] = 0, base
                text("- " if b.lst == "ul" else "1. ")
                list_kind, list_depth = b.lst, 1
            if b.depth > list_depth:
                hot((), Key.tab, b.depth - list_depth)
            elif b.depth < list_depth:
                hot((Key.shift,), Key.tab, list_depth - b.depth)
            list_depth = b.depth

        # ---------- paragraf biasa ----------
        elif not empty:
            list_kind = ""
            if b.heading != st["style"]:
                hot((M, Key.alt), str(b.heading))  # Ctrl+Alt+0..6
                st["style"] = b.heading
                st["size"] = base
                st["spc"] = None
            tgt = (round(b.line or base_spacing[0], 2), round(b.before, 1), round(b.after, 1))
            if st["spc"] != tgt:
                out.append(("spacing",) + tgt)
                st["spc"] = tgt
            if b.align != st["align"]:
                hot((M, Key.shift), ALIGN_KEYS[b.align])
                st["align"] = b.align
            tl = int(b.left / INDENT_STEP + 0.5)
            tf = int(b.first / INDENT_STEP + 0.5)
            if tl != st["left"]:
                hot((M,), "]" if tl > st["left"] else "[", abs(tl - st["left"]))
                st["left"] = tl
            if tf:
                hot((), Key.tab, tf)
            st["first"] = tf

        # ---------- isi teks (run) ----------
        for r in b.runs:
            if not r.text:
                continue
            for k, want in (("b", r.b), ("i", r.i), ("u", r.u)):
                if st[k] != want:
                    hot((M,), k)
                    st[k] = want
            if b.heading == 0 and r.size:
                target = snap_size(r.size)
                if target != st["size"]:
                    steps = SIZES.index(target) - SIZES.index(st["size"])
                    hot((M, Key.shift), "." if steps > 0 else ",", abs(steps))
                    st["size"] = target
            text(r.text)

        # ---------- akhir blok ----------
        if b.lst and not empty:
            if nxt is None:
                pass
            elif nxt.lst == b.lst and nxt.text.strip():
                text("\n")
            else:
                text("\n" * (1 + list_depth))  # keluar dari list
                list_kind, list_depth = "", 0
                st["first"] = st["left"] = 0
                st["style"] = 0
        elif nxt is not None:
            text("\n")
            if b.heading:
                st["style"] = 0
                st["size"] = base
                st["spc"] = None

    return out
