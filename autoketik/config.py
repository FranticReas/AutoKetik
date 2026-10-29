"""
autoketik.config - Konfigurasi, struktur data dasar, dan konstanta keyboard.
"""

from dataclasses import dataclass, field
import sys

try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
except ModuleNotFoundError:
    keyboard = None
    Controller = None
    Key = None


def require_pynput():
    if keyboard is None or Controller is None or Key is None:
        raise RuntimeError("python -m pip install -r requirements.txt")


def _build_neighbors():
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    offsets = [0.0, 0.25, 0.75]
    pos = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            pos[ch] = (c + offsets[r], r)
    neighbors = {}
    for a, (ax, ay) in pos.items():
        neighbors[a] = [
            b
            for b, (bx, by) in pos.items()
            if b != a and ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 < 1.6
        ]
    return neighbors


NEIGHBORS = _build_neighbors()

FAST_BIGRAMS = set(
    "th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng "
    "se ha as ou io le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si "
    "om ur ka an ng da ya me ber ter kan nya ang yan men per".split()
)

HARD_CHARS = set('!?@#$%^&*()_+{}|:"<>~')

# Preset ukuran font Google Docs
SIZES = [6, 7, 8, 9, 10, 11, 12, 14, 18, 24, 30, 36, 48, 60, 72, 96]
ALIGN_KEYS = {"left": "l", "center": "e", "right": "r", "justify": "j"}
INDENT_STEP = 36.0  # pt per tekan Tab / Ctrl+]


def snap_size(sz: float) -> int:
    return min(SIZES, key=lambda s: abs(s - sz))


class StopTyping(Exception):
    pass


@dataclass
class Config:
    wpm: tuple = (60.0, 60.0)           # (min, max)
    typo_rate: tuple = (0.03, 0.03)     # (min, max)
    wave_period: float = 120.0          # detik untuk 1 siklus cepat-lambat-cepat
    start_fast: bool = True
    think_every: tuple = (8, 25)        # setiap N kata, berhenti sejenak
    think_pause: tuple = (1.5, 6.0)     # detik
    sentence_pause: tuple = (0.4, 1.4)
    para_pause: tuple = (1.0, 3.5)
    comma_pause: tuple = (0.15, 0.5)
    notice_pause: tuple = (0.8, 2.0)    # jeda "sadar ada typo" sebelum membenarkan typo (detik)
    shift_delay: tuple = (0.12, 0.3)    # jeda tambahan untuk karakter shift/spesial (detik)
    typo_words: tuple = (1, 3)          # rentang jumlah kata yang diketik sebelum sadar typo
    mac: bool = False
    spacing_menu: str = "Custom spacing"  # teks pencarian menu Docs (sesuaikan bahasa UI)
    decimal_comma: bool = False           # True jika Docs memakai koma desimal (1,5)
    resume_delay: int = 5                 # hitung mundur setelah lanjut dari istirahat
    apply_tabs: int = 2                   # jumlah Tab dari field 'After' ke tombol Apply


@dataclass
class Run:
    text: str
    b: bool = False
    i: bool = False
    u: bool = False
    size: float = 0.0  # 0 = tidak diketahui / jangan diubah


@dataclass
class Block:
    heading: int = 0          # 0 = teks normal, 1..6 = Heading
    align: str = "left"
    first: float = 0.0        # indentasi baris pertama (pt)
    left: float = 0.0         # indentasi kiri (pt)
    lst: str = ""             # "", "ul", "ol"
    depth: int = 0            # kedalaman list
    line: float = 0.0         # spasi baris (1.15, 1.5, 2 ...), 0 = tidak diketahui
    before: float = 0.0       # spasi sebelum paragraf (pt)
    after: float = 0.0        # spasi sesudah paragraf (pt)
    runs: list = field(default_factory=list)

    @property
    def text(self):
        return "".join(r.text for r in self.runs)
