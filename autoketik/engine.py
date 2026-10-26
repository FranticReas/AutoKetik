"""
autoketik.engine - Mesin pengetikan utama (Typist) dan varian GUI (GUITypist).
"""

import math
import random
import re
import sys
import threading
import time

from .config import (
    Config, StopTyping, require_pynput, Controller, Key,
    NEIGHBORS, FAST_BIGRAMS, HARD_CHARS
)


class Typist:
    """
    Simulasi pengetikan ala manusia dengan kecepatan bergelombang,
    jeda berpikir, jeda spasi, simulasi typo realistis, dan kontrol hotkey.
    """

    def __init__(self, cfg: Config):
        require_pynput()
        self.cfg = cfg
        self.kb = Controller()
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.speed = 1.0     # pengali delay acak (momentum): <1 cepat, >1 lambat
        self.clock = 0.0     # waktu aktif (detik) untuk gelombang WPM
        self.wpm_adj = 0.0   # penyesuaian live (hotkey)
        self.typo_adj = 0.0
        self.prev = ""
        self.words_since_think = 0
        self.next_think = random.randint(*cfg.think_every)

    # ---- kontrol dasar ---------------------------------------------------

    def sleep(self, secs: float):
        self.clock += secs
        end = time.monotonic() + secs
        while True:
            if self.stop.is_set():
                raise StopTyping
            if self.paused.is_set():
                time.sleep(0.1)
                end += 0.1  # waktu jeda tidak dihitung
                continue
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.05, remaining))

    def press(self, key):
        self.kb.press(key)
        self.kb.release(key)

    def hotkey(self, mods, key):
        for m in mods:
            self.kb.press(m)
        try:
            self.press(key)
        finally:
            for m in reversed(mods):
                self.kb.release(m)

    def type_char(self, ch: str):
        if ch == "\n":
            self.press(Key.enter)
        elif ch == "\v":
            self.hotkey((Key.shift,), Key.enter)
        elif ch == "\t":
            self.press(Key.tab)
        else:
            try:
                self.kb.type(ch)
            except Exception:
                self._paste_fallback(ch)

    def _paste_fallback(self, ch: str):
        try:
            import pyperclip
            pyperclip.copy(ch)
            mod = Key.cmd if sys.platform == "darwin" else Key.ctrl
            with self.kb.pressed(mod):
                self.kb.press("v")
                self.kb.release("v")
        except Exception:
            pass

    def backspace(self, n: int):
        for _ in range(n):
            self.sleep(random.uniform(0.04, 0.09))
            self.press(Key.backspace)

    # ---- gelombang WPM & typo -------------------------------------------

    def wave(self) -> float:
        """0..1. 1 = paling cepat, 0 = paling lambat. Halus (cosinus)."""
        phase = 2 * math.pi * self.clock / max(1.0, self.cfg.wave_period)
        if not self.cfg.start_fast:
            phase += math.pi
        return (1 + math.cos(phase)) / 2

    def cur_wpm(self) -> float:
        lo, hi = self.cfg.wpm
        return max(5.0, lo + (hi - lo) * self.wave() + self.wpm_adj)

    def cur_typo(self) -> float:
        lo, hi = self.cfg.typo_rate
        return max(0.0, lo + (hi - lo) * self.wave() + self.typo_adj)

    # ---- model tempo -----------------------------------------------------

    def char_delay(self, prev: str, ch: str) -> float:
        base = 60.0 / (self.cur_wpm() * 5)
        d = base * self.speed * random.lognormvariate(0, 0.28)
        if ch == " ":
            d *= 0.9
        if ch.isupper():
            d *= 1.35
        if ch in HARD_CHARS:
            d = d * 1.35 + random.uniform(*self.cfg.shift_delay)
        if prev and (prev + ch).lower() in FAST_BIGRAMS:
            d *= 0.78
        return max(0.015, d)

    def drift(self):
        """Variasi acak kecil antar kata (momentum), di atas gelombang WPM."""
        self.speed *= random.uniform(0.92, 1.08)
        self.speed += (1.0 - self.speed) * 0.12
        self.speed = min(1.25, max(0.8, self.speed))

    # ---- typo ------------------------------------------------------------

    def typo_prob(self) -> float:
        return self.cur_typo() * (1.5 if self.speed < 0.9 else 1.0)

    @staticmethod
    def make_typo(text: str, i: int):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        kind = random.choices(
            ["neighbor", "transpose", "double", "skip"], [55, 15, 15, 15]
        )[0]
        if kind == "transpose" and not (nxt.isalpha() and nxt.lower() != ch.lower()):
            kind = "neighbor"
        if kind == "neighbor" and ch.lower() not in NEIGHBORS:
            kind = "double"

        if kind == "neighbor":
            w = random.choice(NEIGHBORS[ch.lower()])
            return (w.upper() if ch.isupper() else w), 1, kind
        if kind == "transpose":
            return nxt + ch, 2, kind
        if kind == "double":
            return ch * 2, 1, kind
        return "", 1, "skip"

    def pick_typo_tail(self, text: str, start_pos: int) -> str:
        """Pilih sisa teks (beberapa kata) yang terus diketik sebelum sadar ada typo."""
        cfg = self.cfg
        rem = text[start_pos:]
        limit = len(rem)
        for sep in ("\n", "\v", "\r"):
            idx_sep = rem.find(sep)
            if idx_sep != -1 and idx_sep < limit:
                limit = idx_sep
        valid_rem = rem[:limit]
        if not valid_rem:
            return ""

        min_w, max_w = cfg.typo_words
        target_words = random.randint(min_w, max_w)

        if target_words <= 0:
            k = random.choices([0, 1, 2, 3], [30, 30, 25, 15])[0]
            return valid_rem[:k]

        matches = list(re.finditer(r"\S+", valid_rem))
        if not matches:
            return ""

        starts_in_word = not valid_rem[0].isspace()
        target_idx = target_words if starts_in_word else target_words - 1
        target_idx = min(target_idx, len(matches) - 1)

        m = matches[target_idx]
        start, end = m.span()

        roll = random.random()
        if roll < 0.60 and end < len(valid_rem) and valid_rem[end].isspace():
            cutoff = end + 1
        elif roll < 0.85 and (end - start) > 2:
            partial = random.randint(1, end - start - 1)
            cutoff = start + partial
        else:
            cutoff = end

        return valid_rem[:cutoff]

    # ---- mengetik teks ---------------------------------------------------

    def type_text(self, text: str):
        cfg = self.cfg
        n = len(text)
        i = 0
        no_typo_at = -1

        while i < n:
            ch = text[i]

            # ---------- typo + koreksi ----------
            if i != no_typo_at and ch.isalpha() and random.random() < self.typo_prob():
                wrong, consumed, kind = self.make_typo(text, i)
                tail = self.pick_typo_tail(text, i + consumed)
                if kind == "skip" and not tail:
                    rem_after = text[i + consumed :].split("\n")[0].split("\v")[0]
                    if rem_after:
                        tail = rem_after[:1]

                if len(wrong) + len(tail) == 0:
                    no_typo_at = i
                    continue

                p = self.prev
                for c in wrong + tail:
                    self.sleep(self.char_delay(p, c))
                    self.type_char(c)
                    p = c

                # Jeda sadar ada typo sebelum membenarkan
                self.sleep(random.uniform(*cfg.notice_pause))
                # Hapus kembali kata-kata dan typo sampai posisi kesalahan
                self.backspace(len(wrong) + len(tail))
                # Jeda sejenak sebelum mulai mengetik yang benar
                self.sleep(random.uniform(0.15, 0.35))
                no_typo_at = i
                continue

            # ---------- karakter normal ----------
            self.sleep(self.char_delay(self.prev, ch))
            self.type_char(ch)

            nxt = text[i + 1] if i + 1 < n else "\n"
            if ch == "\n":
                self.sleep(random.uniform(*cfg.para_pause))
            elif ch in ".!?" and nxt.isspace():
                self.sleep(random.uniform(*cfg.sentence_pause))
            elif ch in ",;:" and random.random() < 0.5:
                self.sleep(random.uniform(*cfg.comma_pause))

            # batas kata
            if ch in (" ", "\n") and self.prev not in (" ", "\n", ""):
                self.words_since_think += 1
                self.drift()
                if random.random() < 0.02:
                    self.sleep(random.uniform(0.5, 1.2))
                if self.words_since_think >= self.next_think:
                    pause = random.uniform(*cfg.think_pause)
                    if random.random() < 0.15:
                        pause *= 2
                    self.sleep(pause)
                    self.words_since_think = 0
                    self.next_think = random.randint(*cfg.think_every)

            self.prev = ch
            i += 1

    # ---- spasi baris/paragraf (dialog Custom spacing) -------------------

    def apply_spacing(self, line, before, after):
        M = Key.cmd if self.cfg.mac else Key.ctrl

        def num(v):
            t = f"{v:g}"
            return t.replace(".", ",") if self.cfg.decimal_comma else t

        self.sleep(random.uniform(0.5, 1.0))
        self.hotkey((Key.alt,), "/")
        self.sleep(random.uniform(0.7, 1.1))
        self.kb.type(self.cfg.spacing_menu)
        self.sleep(random.uniform(0.8, 1.2))
        self.press(Key.enter)
        self.sleep(random.uniform(1.0, 1.6))
        for k, val in enumerate((line, before, after)):
            self.hotkey((M,), "a")
            self.sleep(0.1)
            self.kb.type(num(val))
            self.sleep(random.uniform(0.3, 0.5))
            if k < 2:
                self.press(Key.tab)
                self.sleep(random.uniform(0.25, 0.45))
        self.sleep(random.uniform(0.6, 0.9))
        for _ in range(self.cfg.apply_tabs):
            self.press(Key.tab)
            self.sleep(random.uniform(0.15, 0.3))
        self.press(Key.enter)
        self.sleep(random.uniform(0.8, 1.2))

    # ---- istirahat (menunggu F9 manual) ---------------------------------

    def take_break(self, chapters_done):
        print(f"\n[ISTIRAHAT] {chapters_done} bab selesai. Tekan F9 untuk melanjutkan.\a")
        self.paused.set()
        self.sleep(0.1)
        for s in range(self.cfg.resume_delay, 0, -1):
            print(f"Lanjut dalam {s}... (klik dokumen tujuan)  ", end="\r", flush=True)
            self.sleep(1)
        print(" " * 60, end="\r")
        if self.cfg.mac:
            self.hotkey((Key.cmd,), Key.down)
        else:
            self.hotkey((Key.ctrl,), Key.end)
        self.sleep(random.uniform(0.3, 0.8))

    # ---- loop utama ------------------------------------------------------

    def run(self, actions):
        for act in actions:
            if act[0] == "text":
                self.type_text(act[1])
            elif act[0] == "spacing":
                self.apply_spacing(*act[1:])
            elif act[0] == "break":
                self.take_break(act[1])
            else:
                _, mods, key = act
                self.sleep(random.uniform(0.25, 0.7))
                self.hotkey(mods, key)
                self.sleep(random.uniform(0.1, 0.3))


class GUITypist(Typist):
    """
    Subclass Typist dengan hook progress, status, dan animasi pengetikan real-time untuk GUI.
    """

    def __init__(self, cfg, on_progress=None, on_status=None, on_char=None, on_backspace=None, simulate_only=False):
        super().__init__(cfg)
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_char = on_char
        self.on_backspace = on_backspace
        self.simulate_only = simulate_only
        self.total_chars = 0
        self.chars_typed = 0
        self._last_progress_time = 0.0

    def _notify_progress(self, force=False):
        now = time.monotonic()
        if (force or now - self._last_progress_time >= 0.15) and self.on_progress:
            self._last_progress_time = now
            self.on_progress(self.chars_typed, self.total_chars, self.cur_wpm(), self.cur_typo())

    def type_char(self, ch: str):
        if not self.simulate_only:
            super().type_char(ch)
        if self.on_char:
            self.on_char(ch)

    def backspace(self, n: int):
        for _ in range(n):
            self.sleep(random.uniform(0.04, 0.09))
            if not self.simulate_only:
                self.press(Key.backspace)
            if self.on_backspace:
                self.on_backspace(1)

    def type_text(self, text: str):
        cfg = self.cfg
        n = len(text)
        i = 0
        no_typo_at = -1

        while i < n:
            ch = text[i]

            # ---------- typo + koreksi ----------
            if i != no_typo_at and ch.isalpha() and random.random() < self.typo_prob():
                wrong, consumed, kind = self.make_typo(text, i)
                tail = self.pick_typo_tail(text, i + consumed)
                if kind == "skip" and not tail:
                    rem_after = text[i + consumed :].split("\n")[0].split("\v")[0]
                    if rem_after:
                        tail = rem_after[:1]

                if len(wrong) + len(tail) == 0:
                    no_typo_at = i
                    continue

                p = self.prev
                for c in wrong + tail:
                    self.sleep(self.char_delay(p, c))
                    self.type_char(c)
                    p = c

                # Jeda sadar ada typo sebelum membenarkan
                self.sleep(random.uniform(*cfg.notice_pause))
                # Hapus kembali kata-kata dan typo sampai posisi kesalahan
                self.backspace(len(wrong) + len(tail))
                # Jeda sejenak sebelum mulai mengetik yang benar
                self.sleep(random.uniform(0.15, 0.35))
                no_typo_at = i
                continue

            # ---------- karakter normal ----------
            self.sleep(self.char_delay(self.prev, ch))
            self.type_char(ch)

            self.chars_typed += 1
            self._notify_progress()

            nxt = text[i + 1] if i + 1 < n else "\n"
            if ch == "\n":
                self.sleep(random.uniform(*cfg.para_pause))
            elif ch in ".!?" and nxt.isspace():
                self.sleep(random.uniform(*cfg.sentence_pause))
            elif ch in ",;:" and random.random() < 0.5:
                self.sleep(random.uniform(*cfg.comma_pause))

            # batas kata
            if ch in (" ", "\n") and self.prev not in (" ", "\n", ""):
                self.words_since_think += 1
                self.drift()
                if random.random() < 0.02:
                    self.sleep(random.uniform(0.5, 1.2))
                if self.words_since_think >= self.next_think:
                    pause = random.uniform(*cfg.think_pause)
                    if random.random() < 0.15:
                        pause *= 2
                    self.sleep(pause)
                    self.words_since_think = 0
                    self.next_think = random.randint(*cfg.think_every)

            self.prev = ch
            i += 1

        self._notify_progress(force=True)

    def take_break(self, chapters_done):
        if self.on_status:
            self.on_status(f"[ISTIRAHAT] Bab {chapters_done} selesai. Tekan F9 untuk melanjutkan!")
        self.paused.set()
        self.sleep(0.1)
        for s in range(self.cfg.resume_delay, 0, -1):
            if self.on_status:
                self.on_status(f"Melanjutkan dalam {s} detik... (klik jendela tujuan)")
            self.sleep(1)
        if not self.simulate_only:
            if self.cfg.mac:
                self.hotkey((Key.cmd,), Key.down)
            else:
                self.hotkey((Key.ctrl,), Key.end)
        self.sleep(random.uniform(0.3, 0.8))
        if self.on_status:
            self.on_status("Sedang mengetik...")
