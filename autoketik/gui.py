"""
autoketik.gui - Antarmuka grafis (GUI) modern berbasis PySide6.
"""

import os
import sys
import threading
import time

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
        QLineEdit, QTextEdit, QSlider, QProgressBar, QCheckBox, QComboBox,
        QHBoxLayout, QVBoxLayout, QSizePolicy, QFileDialog,
        QMessageBox, QDialog, QButtonGroup, QStackedWidget,
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot
    from PySide6.QtGui import QFont, QTextCursor
except ImportError:
    print(
        "PySide6 belum terinstal.\nSilakan jalankan:\n\n  pip install PySide6",
        file=sys.stderr
    )
    sys.exit(1)

from .config import Config, StopTyping, require_pynput, Key, keyboard
from .parser import parse_html, fetch_gdoc, normalize
from .planner import plan, parse_range
from .engine import GUITypist


# =============================================================================
# Stylesheet Tema
# =============================================================================
DARK_QSS = """
QMainWindow, QDialog { background-color: #0f0f1a; }
QWidget {
    color: #e2e8f0;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}
QFrame#card {
    background-color: #1a1a2e;
    border-radius: 12px;
    border: 1px solid #2a2a4a;
}
QPushButton {
    background-color: #1e1e3a;
    border-radius: 9px;
    padding: 7px 16px;
    border: 1px solid #3a3a6a;
    color: #c0c8e0;
    min-height: 28px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2d2d5a;
    border-color: #7c6aff;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #181830;
    border-color: #5a50dd;
}
QPushButton:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #9b59ff);
    color: #ffffff;
    border-color: #6c63ff;
    font-weight: 600;
}
QPushButton:disabled {
    background-color: #111125;
    color: #3a3a55;
    border-color: #222235;
}
QLineEdit {
    background-color: #1e1e3a;
    border: 1px solid #3a3a6a;
    border-radius: 8px;
    padding: 5px 10px;
    color: #e2e8f0;
}
QLineEdit:focus { border-color: #7c6aff; background-color: #22224a; }
QTextEdit {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    color: #e2e8f0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QSlider::groove:horizontal {
    background: #1e1e3a; height: 6px; border-radius: 3px; border: none;
}
QSlider::handle:horizontal {
    background: #a78bfa;
    width: 16px; height: 16px;
    border-radius: 8px;
    margin: -5px 0;
    border: 2px solid #4c35a0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #a78bfa);
    border-radius: 3px;
}
QProgressBar {
    background: #1e1e3a;
    border-radius: 5px;
    border: none;
    text-align: center;
    color: transparent;
    max-height: 10px;
    min-height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #a78bfa);
    border-radius: 5px;
}
QComboBox {
    background-color: #1e1e3a;
    border: 1px solid #3a3a6a;
    border-radius: 8px;
    padding: 5px 10px;
    color: #e2e8f0;
    min-height: 28px;
}
QComboBox:hover { border-color: #7c6aff; }
QComboBox::drop-down { border: none; padding-right: 10px; }
QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 1px solid #3a3a6a;
    selection-background-color: #2d2d5a;
    color: #e2e8f0;
    outline: none;
    border-radius: 6px;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 2px solid #3a3a6a;
    background: #1e1e3a;
}
QCheckBox::indicator:hover { border-color: #7c6aff; }
QCheckBox::indicator:checked {
    background: #6c63ff;
    border-color: #6c63ff;
}
QScrollBar:vertical { background: #0f0f1a; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical {
    background: #3a3a6a;
    border-radius: 4px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


LIGHT_QSS = """
QMainWindow, QDialog { background-color: #f0f2ff; }
QWidget {
    color: #2d2d5e;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}
QFrame#card {
    background-color: #e4e8ff;
    border-radius: 12px;
    border: 1px solid #c8cef5;
}
QPushButton {
    background-color: #dde1f8;
    border-radius: 9px;
    padding: 7px 16px;
    border: 1px solid #b8c0ea;
    color: #3d3d7a;
    min-height: 28px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #c8cff5;
    border-color: #6c63ff;
    color: #2d2d5e;
}
QPushButton:pressed { background-color: #b8bfed; border-color: #5a50dd; }
QPushButton:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #9b59ff);
    color: #ffffff;
    border-color: #6c63ff;
    font-weight: 600;
}
QPushButton:disabled {
    background-color: #f0f2ff;
    color: #9090b0;
    border-color: #d0d4f0;
}
QLineEdit {
    background-color: #e4e8ff; border: 1px solid #b8c0ea; border-radius: 8px;
    padding: 5px 10px; color: #2d2d5e;
}
QLineEdit:focus { border-color: #6c63ff; background-color: #dde1f8; }
QTextEdit {
    background-color: #e4e8ff; border: 1px solid #b8c0ea; border-radius: 8px;
    color: #2d2d5e; font-family: "Consolas", monospace; font-size: 12px;
}
QSlider::groove:horizontal { background: #c8cff5; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #6c63ff; width: 16px; height: 16px; border-radius: 8px; margin: -5px 0;
    border: 2px solid #4c45cc;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #9b8aff);
    border-radius: 3px;
}
QProgressBar {
    background: #c8cff5; border-radius: 5px; border: none;
    text-align: center; color: transparent; max-height: 10px; min-height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c63ff, stop:1 #9b8aff);
    border-radius: 5px;
}
QComboBox {
    background-color: #dde1f8; border: 1px solid #b8c0ea; border-radius: 8px;
    padding: 5px 10px; color: #2d2d5e; min-height: 28px;
}
QComboBox:hover { border-color: #6c63ff; }
QComboBox::drop-down { border: none; padding-right: 10px; }
QComboBox QAbstractItemView {
    background-color: #f0f2ff; selection-background-color: #c8cff5; color: #2d2d5e;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid #9090b0; background: #dde1f8;
}
QCheckBox::indicator:hover { border-color: #6c63ff; }
QCheckBox::indicator:checked { background: #6c63ff; border-color: #6c63ff; }
QScrollBar:vertical { background: #f0f2ff; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #b8c0ea; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""



# =============================================================================
# Widget Kustom: SegmentedButton (pengganti CTkSegmentedButton)
# =============================================================================
class SegmentedButton(QWidget):
    """Tombol pilihan eksklusif bergaya segmented -- modern pill style."""
    valueChanged = Signal(str)

    def __init__(self, values: list[str], parent=None, height: int = 34, bold: bool = True):
        super().__init__(parent)
        self._values = values
        self._current = values[0] if values else ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        # Wrapper frame sebagai "pill container"
        self.setObjectName("segContainer")
        self.setStyleSheet(
            "QWidget#segContainer {"
            "  background-color: #12122a;"
            "  border-radius: 11px;"
            "  border: 1px solid #3a3a6a;"
            "}"
        )

        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for v in values:
            btn = QPushButton(v)
            btn.setCheckable(True)
            btn.setFixedHeight(height)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if bold:
                f = btn.font()
                f.setBold(True)
                btn.setFont(f)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: transparent;"
                "  border: none;"
                "  border-radius: 8px;"
                "  color: #7070a0;"
                "  font-size: 12px;"
                "  padding: 4px 12px;"
                "}"
                "QPushButton:hover {"
                "  background: rgba(108,99,255,0.15);"
                "  color: #c0b8ff;"
                "}"
                "QPushButton:checked {"
                "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "    stop:0 #6c63ff, stop:1 #9b59ff);"
                "  color: #ffffff;"
                "  font-weight: 700;"
                "}"
            )
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[v] = btn
            btn.clicked.connect(lambda _checked, val=v: self._on_clicked(val))

        if values:
            self._buttons[values[0]].setChecked(True)

    def _on_clicked(self, val: str):
        self._current = val
        self.valueChanged.emit(val)

    def set(self, val: str):
        self._current = val
        if val in self._buttons:
            self._buttons[val].setChecked(True)

    def get(self) -> str:
        return self._current


# =============================================================================
# Signal Object: thread-safe bridge dari worker thread ke UI thread
# =============================================================================
class _UISignals(QObject):
    progress_updated   = Signal(int, int, float, float)   # typed, total, wpm, typo
    status_changed     = Signal(str)
    char_appended      = Signal(str)
    backspace_needed   = Signal(int)
    text_appended      = Signal(str)
    sim_status_changed = Signal(str, str)   # text, color_hex
    controls_reset     = Signal()
    window_restore     = Signal()
    window_minimize    = Signal()
    pause_btn_text     = Signal(str)
    badge_refresh      = Signal()


# =============================================================================
# Kelas Utama Aplikasi
# =============================================================================
class AutoKetikApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoKetik GUI - Human Typing Automation")
        self.resize(900, 850)
        self.setMinimumSize(820, 750)

        # ── State Aplikasi ────────────────────────────────────────────────────
        self.typist: GUITypist | None = None
        self.worker_thread: threading.Thread | None = None
        self.listener = None
        self.is_running = False
        self.stop_requested = False
        self.loaded_data: dict | None = None

        # ── Nilai Konfigurasi (pengganti ctk.*Var) ───────────────────────────
        self.source_type = "file"
        self.wpm_min = 45
        self.wpm_max = 75
        self.typo_min = 1.5     # persen
        self.typo_max = 4.0     # persen
        self.ignore_format = False
        self.auto_minimize = True
        self.countdown_delay = 8
        self.break_enabled = False

        # ── Signal untuk thread-safety (self.after() → emit signal) ──────────
        self._sigs = _UISignals()
        self._sigs.progress_updated.connect(self._update_progress_ui)
        self._sigs.status_changed.connect(self._set_status_text)
        self._sigs.char_appended.connect(self._do_sim_append_char)
        self._sigs.backspace_needed.connect(self._do_sim_backspace)
        self._sigs.text_appended.connect(self._do_sim_append_text)
        self._sigs.sim_status_changed.connect(self._do_set_sim_status)
        self._sigs.controls_reset.connect(self._reset_controls_state)
        self._sigs.window_restore.connect(self._restore_window_if_minimized)
        self._sigs.window_minimize.connect(lambda: QTimer.singleShot(400, self.showMinimized))
        self._sigs.pause_btn_text.connect(lambda t: self.btn_pause.setText(t))
        self._sigs.badge_refresh.connect(self._trigger_badge_refresh)

        # ── Bangun UI & terapkan tema awal ────────────────────────────────────
        self._app = QApplication.instance()
        self._build_ui()
        self._apply_theme("Dark")

    # =========================================================================
    # Tema
    # =========================================================================
    def _apply_theme(self, theme: str):
        if theme == "Dark":
            self._app.setStyleSheet(DARK_QSS)
        elif theme == "Light":
            self._app.setStyleSheet(LIGHT_QSS)
        else:  # System
            self._app.setStyleSheet("")

    # =========================================================================
    # Build UI Utama
    # =========================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(15, 12, 15, 12)
        root.setSpacing(6)

        # ── Header ────────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("card")
        header.setFixedHeight(60)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 6, 14, 6)

        title_box = QWidget()
        tb_lay = QVBoxLayout(title_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(2)

        lbl_title = QLabel("⚡ AutoKetik GUI")
        ft = lbl_title.font()
        ft.setPointSize(15)
        ft.setBold(True)
        lbl_title.setFont(ft)
        tb_lay.addWidget(lbl_title)

        lbl_sub = QLabel("Simulasi pengetikan alami manusia dengan format dokumen")
        lbl_sub.setStyleSheet("color: gray; font-size: 11px;")
        tb_lay.addWidget(lbl_sub)

        h_lay.addWidget(title_box)
        h_lay.addStretch()

        h_lay.addWidget(QLabel("Tema:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        for i in range(self.theme_combo.count()):
            self.theme_combo.setItemData(
            i,
            Qt.AlignmentFlag.AlignCenter,
            Qt.ItemDataRole.TextAlignmentRole,
        )
        self.theme_combo.setFixedWidth(90)
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        h_lay.addWidget(self.theme_combo)

        root.addWidget(header)

        # ── Tab Selector (Segmented Button) ───────────────────────────────────
        self.main_tab_selector = SegmentedButton(
            ["📝 Sumber Dokumen", "⚙️ Kecepatan & Typo", "⏱️ Jeda & Istirahat"],
            height=34
        )
        self.main_tab_selector.valueChanged.connect(self._on_main_tab_changed)
        root.addWidget(self.main_tab_selector)

        # ── Tab Container (QStackedWidget, tinggi tetap) ───────────────────────
        self.tab_stack = QStackedWidget()
        self.tab_stack.setFixedHeight(295)

        self.tab_source = QWidget()
        self.tab_speed = QWidget()
        self.tab_advanced = QWidget()

        self.tab_stack.addWidget(self.tab_source)    # 0
        self.tab_stack.addWidget(self.tab_speed)     # 1
        self.tab_stack.addWidget(self.tab_advanced)  # 2

        self._build_source_tab()
        self._build_speed_tab()
        self._build_advanced_tab()

        root.addWidget(self.tab_stack)

        # ── Bottom Deck ───────────────────────────────────────────────────────
        bottom = QFrame()
        bottom.setObjectName("card")
        bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        b_lay = QVBoxLayout(bottom)
        b_lay.setContentsMargins(12, 8, 12, 8)
        b_lay.setSpacing(5)
        self._build_bottom_deck(b_lay)

        root.addWidget(bottom, stretch=1)

    # =========================================================================
    # Navigasi Tab
    # =========================================================================
    def _on_main_tab_changed(self, val: str):
        if "Sumber" in val:
            self.tab_stack.setCurrentIndex(0)
        elif "Kecepatan" in val:
            self.tab_stack.setCurrentIndex(1)
        elif "Jeda" in val:
            self.tab_stack.setCurrentIndex(2)

    # =========================================================================
    # Tab 1: Sumber Dokumen
    # =========================================================================
    def _build_source_tab(self):
        lay = QVBoxLayout(self.tab_source)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        lbl = QLabel("Pilih Sumber Teks:")
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        lay.addWidget(lbl)

        self.source_selector = SegmentedButton(
            ["📁 File (.txt / .html)", "📋 Clipboard", "🌐 Google Docs URL"],
            height=30
        )
        self.source_selector.valueChanged.connect(self._on_source_tab_changed)
        lay.addWidget(self.source_selector)

        # Stack kartu sumber (tinggi tetap 115px)
        self.source_stack = QStackedWidget()
        self.source_stack.setFixedHeight(115)

        self.card_file = QWidget()
        self.card_clipboard = QWidget()
        self.card_gdocs = QWidget()

        self.source_stack.addWidget(self.card_file)       # 0
        self.source_stack.addWidget(self.card_clipboard)  # 1
        self.source_stack.addWidget(self.card_gdocs)      # 2

        self._build_card_file()
        self._build_card_clipboard()
        self._build_card_gdocs()
        lay.addWidget(self.source_stack)

        # Baris opsi bawah
        sub_row = QWidget()
        sub_lay = QHBoxLayout(sub_row)
        sub_lay.setContentsMargins(0, 4, 0, 0)

        self.chk_no_format = QCheckBox("Abaikan format dokumen (ketik sebagai teks polos murni)")
        self.chk_no_format.stateChanged.connect(self._on_format_changed)
        sub_lay.addWidget(self.chk_no_format)
        sub_lay.addStretch()

        self.lbl_source_summary = QLabel("Belum ada dokumen dimuat.")
        self.lbl_source_summary.setStyleSheet("color: gray; font-size: 11px;")
        sub_lay.addWidget(self.lbl_source_summary)

        lay.addWidget(sub_row)

    def _on_format_changed(self):
        self.ignore_format = self.chk_no_format.isChecked()
        if self.loaded_data:
            self.load_source(quiet=True)

    def _on_source_tab_changed(self, val: str):
        if "File" in val:
            self.source_type = "file"
            self.source_stack.setCurrentIndex(0)
        elif "Clipboard" in val:
            self.source_type = "clipboard"
            self.source_stack.setCurrentIndex(1)
        elif "Google" in val:
            self.source_type = "gdocs"
            self.source_stack.setCurrentIndex(2)

    def _build_card_file(self):
        lay = QVBoxLayout(self.card_file)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(5)

        lbl = QLabel("Pilih file dokumen teks (.txt) atau file .html hasil Download dari Google Docs:")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        f_row = QWidget()
        f_lay = QHBoxLayout(f_row)
        f_lay.setContentsMargins(0, 0, 0, 0)
        f_lay.setSpacing(8)

        self.entry_file = QLineEdit()
        self.entry_file.setPlaceholderText("Klik tombol Browse untuk memilih file dokumen...")
        f_lay.addWidget(self.entry_file, stretch=1)

        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_file)
        f_lay.addWidget(btn_browse)
        lay.addWidget(f_row)

        lbl_tip = QLabel("Tip: File .html otomatis dibaca dengan format heading, tebal, miring, dan spasi.")
        lbl_tip.setStyleSheet("color: gray; font-size: 11px;")
        lay.addWidget(lbl_tip)

    def _build_card_clipboard(self):
        lay = QVBoxLayout(self.card_clipboard)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(5)

        lay.addWidget(QLabel("Teks akan diambil langsung dari clipboard sistem Anda:"))

        c_row = QWidget()
        c_lay = QHBoxLayout(c_row)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(10)

        btn_clip = QPushButton("📋 Muat Teks dari Clipboard Sekarang")
        btn_clip.setFixedWidth(265)
        btn_clip.clicked.connect(lambda: self.load_source(quiet=False))
        c_lay.addWidget(btn_clip)

        lbl_hint = QLabel("(Salin teks dari mana saja, lalu klik tombol ini)")
        lbl_hint.setStyleSheet("color: gray; font-size: 11px;")
        c_lay.addWidget(lbl_hint)
        c_lay.addStretch()
        lay.addWidget(c_row)

        lbl_note = QLabel("Teks clipboard akan diketik sebagai teks polos tanpa format Google Docs.")
        lbl_note.setStyleSheet("color: gray; font-size: 11px;")
        lay.addWidget(lbl_note)

    def _build_card_gdocs(self):
        lay = QVBoxLayout(self.card_gdocs)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(5)

        lay.addWidget(QLabel("Masukkan tautan Google Docs (Viewer publik):"))

        g_row = QWidget()
        g_lay = QHBoxLayout(g_row)
        g_lay.setContentsMargins(0, 0, 0, 0)
        g_lay.setSpacing(8)

        self.entry_url = QLineEdit()
        self.entry_url.setPlaceholderText("https://docs.google.com/document/d/XXXXXXXXX/edit")
        self.entry_url.returnPressed.connect(lambda: self.load_source(quiet=False))
        g_lay.addWidget(self.entry_url, stretch=1)

        btn_load = QPushButton("📥 Muat Dokumen")
        btn_load.setFixedWidth(115)
        btn_load.clicked.connect(lambda: self.load_source(quiet=False))
        g_lay.addWidget(btn_load)
        lay.addWidget(g_row)

        lbl_info = QLabel(
            "Pastikan link disetel: 'Anyone with the link (Siapa saja yang memiliki link) – Viewer'."
        )
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        lbl_info.setWordWrap(True)
        lay.addWidget(lbl_info)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Dokumen",
            "",
            "Semua File yang Didukung (*.txt *.html *.htm);;"
            "Web Page HTML (*.html *.htm);;Text File (*.txt);;Semua File (*.*)"
        )
        if path:
            self.entry_file.setText(path)
            self.load_source(quiet=False)

    # =========================================================================
    # Tab 2: Kecepatan & Typo
    # =========================================================================
    def _build_speed_tab(self):
        lay = QVBoxLayout(self.tab_speed)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        # Preset
        pr = QWidget()
        pr_lay = QHBoxLayout(pr)
        pr_lay.setContentsMargins(0, 0, 0, 0)
        lbl_p = QLabel("Preset Kecepatan:")
        f = lbl_p.font(); f.setBold(True); lbl_p.setFont(f)
        pr_lay.addWidget(lbl_p)
        pr_lay.addStretch()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Santai (40-55 WPM)", "Normal (55-75 WPM)", "Cepat (75-95 WPM)", "Kustom"])
        self.preset_combo.setCurrentText("Normal (55-75 WPM)")
        self.preset_combo.setFixedWidth(175)
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        pr_lay.addWidget(self.preset_combo)
        lay.addWidget(pr)

        # WPM Group
        wpm_grp = QFrame()
        wpm_grp.setObjectName("card")
        wpm_lay = QVBoxLayout(wpm_grp)
        wpm_lay.setContentsMargins(10, 6, 10, 6)
        wpm_lay.setSpacing(4)

        wpm_lay.addWidget(self._make_slider_row(
            "WPM Minimum (Lambat):", 15, 120, self.wpm_min,
            lambda v: self._on_wpm_change("min", v),
            "_lbl_val_min_wpm", "_slider_min_wpm", "WPM"
        ))
        wpm_lay.addWidget(self._make_slider_row(
            "WPM Maksimum (Cepat):", 20, 150, self.wpm_max,
            lambda v: self._on_wpm_change("max", v),
            "_lbl_val_max_wpm", "_slider_max_wpm", "WPM"
        ))

        wave_row = QWidget()
        wv_lay = QHBoxLayout(wave_row)
        wv_lay.setContentsMargins(0, 2, 0, 2)
        wv_lay.setSpacing(8)
        wv_lay.addWidget(QLabel("Periode Siklus (detik):"))
        self.entry_wave = QLineEdit("120.0")
        self.entry_wave.setFixedWidth(65)
        wv_lay.addWidget(self.entry_wave)
        wv_lay.addWidget(QLabel("Mulai dari:"))
        self.seg_start = SegmentedButton(["fast", "slow"], height=28, bold=False)
        self.seg_start.set("fast")
        wv_lay.addWidget(self.seg_start)
        wv_lay.addStretch()
        wpm_lay.addWidget(wave_row)
        lay.addWidget(wpm_grp)

        # Typo Group
        typo_grp = QFrame()
        typo_grp.setObjectName("card")
        typo_lay = QVBoxLayout(typo_grp)
        typo_lay.setContentsMargins(10, 6, 10, 6)
        typo_lay.setSpacing(4)

        # Slider typo diskalakan ×10 (int) agar bisa pakai QSlider
        typo_lay.addWidget(self._make_slider_row(
            "Peluang Typo Min (%):", 0, 80, int(self.typo_min * 10),
            lambda v: self._on_typo_change("min", v / 10.0),
            "_lbl_val_min_typo", "_slider_min_typo", "%", scale=0.1
        ))
        typo_lay.addWidget(self._make_slider_row(
            "Peluang Typo Max (%):", 0, 100, int(self.typo_max * 10),
            lambda v: self._on_typo_change("max", v / 10.0),
            "_lbl_val_max_typo", "_slider_max_typo", "%", scale=0.1
        ))

        t_det = QWidget()
        td_lay = QHBoxLayout(t_det)
        td_lay.setContentsMargins(0, 2, 0, 2)
        td_lay.setSpacing(8)
        td_lay.addWidget(QLabel("Kata sebelum sadar:"))
        self.entry_typo_words = QLineEdit("1-3")
        self.entry_typo_words.setFixedWidth(55)
        td_lay.addWidget(self.entry_typo_words)
        td_lay.addWidget(QLabel("Jeda sadar (detik):"))
        self.entry_typo_delay = QLineEdit("0.8-2.0")
        self.entry_typo_delay.setFixedWidth(65)
        td_lay.addWidget(self.entry_typo_delay)
        td_lay.addStretch()
        typo_lay.addWidget(t_det)
        lay.addWidget(typo_grp)

    def _make_slider_row(
        self, label: str, lo: int, hi: int, val: int,
        callback, lbl_attr: str, slider_attr: str, unit: str, scale: float = 1.0
    ) -> QWidget:
        """Helper: buat baris label + slider + nilai. Simpan widget sebagai attr self."""
        row = QWidget()
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setFixedWidth(175)
        r_lay.addWidget(lbl)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(val)
        r_lay.addWidget(slider, stretch=1)

        if scale == 1.0:
            display = f"{val} {unit}"
        else:
            display = f"{val * scale:.1f}{unit}"
        val_lbl = QLabel(display)
        val_lbl.setFixedWidth(65)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        r_lay.addWidget(val_lbl)

        slider.valueChanged.connect(callback)
        setattr(self, lbl_attr, val_lbl)
        setattr(self, slider_attr, slider)
        return row

    def _on_wpm_change(self, which: str, val: int):
        if which == "min":
            self.wpm_min = val
            self._lbl_val_min_wpm.setText(f"{val} WPM")
            if val > self.wpm_max:
                self.wpm_max = val
                self._slider_max_wpm.blockSignals(True)
                self._slider_max_wpm.setValue(val)
                self._slider_max_wpm.blockSignals(False)
                self._lbl_val_max_wpm.setText(f"{val} WPM")
        else:
            self.wpm_max = val
            self._lbl_val_max_wpm.setText(f"{val} WPM")
            if val < self.wpm_min:
                self.wpm_min = val
                self._slider_min_wpm.blockSignals(True)
                self._slider_min_wpm.setValue(val)
                self._slider_min_wpm.blockSignals(False)
                self._lbl_val_min_wpm.setText(f"{val} WPM")
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText("Kustom")
        self.preset_combo.blockSignals(False)
        self._refresh_eta()

    def _on_typo_change(self, which: str, val: float):
        if which == "min":
            self.typo_min = val
            self._lbl_val_min_typo.setText(f"{val:.1f}%")
            if val > self.typo_max:
                self.typo_max = val
                self._slider_max_typo.blockSignals(True)
                self._slider_max_typo.setValue(int(val * 10))
                self._slider_max_typo.blockSignals(False)
                self._lbl_val_max_typo.setText(f"{val:.1f}%")
        else:
            self.typo_max = val
            self._lbl_val_max_typo.setText(f"{val:.1f}%")
            if val < self.typo_min:
                self.typo_min = val
                self._slider_min_typo.blockSignals(True)
                self._slider_min_typo.setValue(int(val * 10))
                self._slider_min_typo.blockSignals(False)
                self._lbl_val_min_typo.setText(f"{val:.1f}%")

    def _apply_preset(self, preset: str):
        if "Kustom" in preset:
            return
        mapping = {
            "Santai": (40, 55, 1.0, 2.5),
            "Normal": (55, 75, 1.5, 4.0),
            "Cepat":  (75, 95, 2.5, 5.5),
        }
        for key, (wmin, wmax, tmin, tmax) in mapping.items():
            if key in preset:
                self._bulk_set_wpm_typo(wmin, wmax, tmin, tmax)
                break
        self._refresh_eta()

    def _bulk_set_wpm_typo(self, wmin: int, wmax: int, tmin: float, tmax: float):
        """Set semua nilai sekaligus tanpa memicu _on_wpm_change (blockSignals)."""
        self.wpm_min = wmin; self.wpm_max = wmax
        self.typo_min = tmin; self.typo_max = tmax
        for slider, val in [
            (self._slider_min_wpm, wmin),
            (self._slider_max_wpm, wmax),
            (self._slider_min_typo, int(tmin * 10)),
            (self._slider_max_typo, int(tmax * 10)),
        ]:
            slider.blockSignals(True)
            slider.setValue(val)
            slider.blockSignals(False)
        self._lbl_val_min_wpm.setText(f"{wmin} WPM")
        self._lbl_val_max_wpm.setText(f"{wmax} WPM")
        self._lbl_val_min_typo.setText(f"{tmin:.1f}%")
        self._lbl_val_max_typo.setText(f"{tmax:.1f}%")

    # =========================================================================
    # Tab 3: Jeda, Countdown & Istirahat
    # =========================================================================
    def _build_advanced_tab(self):
        lay = QVBoxLayout(self.tab_advanced)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        # Grup countdown
        start_grp = QFrame()
        start_grp.setObjectName("card")
        sg_lay = QVBoxLayout(start_grp)
        sg_lay.setContentsMargins(10, 6, 10, 6)
        sg_lay.setSpacing(4)

        sg_lay.addWidget(self._make_slider_row(
            "Hitung Mundur Mulai (Detik):", 2, 25, self.countdown_delay,
            self._on_countdown_changed,
            "lbl_val_countdown", "slider_countdown", "detik"
        ))

        self.chk_auto_min = QCheckBox("Otomatis minimize GUI saat hitung mundur dimulai")
        self.chk_auto_min.setChecked(True)
        self.chk_auto_min.stateChanged.connect(lambda s: setattr(self, "auto_minimize", bool(s)))
        sg_lay.addWidget(self.chk_auto_min)
        lay.addWidget(start_grp)

        # Grup jeda berpikir
        think_grp = QFrame()
        think_grp.setObjectName("card")
        tg_lay = QVBoxLayout(think_grp)
        tg_lay.setContentsMargins(10, 6, 10, 6)
        tg_lay.setSpacing(4)

        t_row = QWidget()
        t_lay = QHBoxLayout(t_row)
        t_lay.setContentsMargins(0, 0, 0, 0)
        t_lay.setSpacing(8)
        t_lay.addWidget(QLabel("Berpikir tiap N kata:"))
        self.entry_think_every = QLineEdit("8-25")
        self.entry_think_every.setFixedWidth(65)
        t_lay.addWidget(self.entry_think_every)
        t_lay.addWidget(QLabel("Durasi jeda (detik):"))
        self.entry_think_pause = QLineEdit("1.5-6.0")
        self.entry_think_pause.setFixedWidth(65)
        t_lay.addWidget(self.entry_think_pause)
        t_lay.addStretch()
        tg_lay.addWidget(t_row)

        s_row = QWidget()
        s_lay = QHBoxLayout(s_row)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(8)
        s_lay.addWidget(QLabel("Jeda ekstra Shift / Karakter spesial (detik):"))
        self.entry_shift_delay = QLineEdit("0.12-0.3")
        self.entry_shift_delay.setFixedWidth(65)
        s_lay.addWidget(self.entry_shift_delay)
        s_lay.addStretch()
        tg_lay.addWidget(s_row)
        lay.addWidget(think_grp)

        # Grup istirahat
        brk_grp = QFrame()
        brk_grp.setObjectName("card")
        bg_lay = QVBoxLayout(brk_grp)
        bg_lay.setContentsMargins(10, 6, 10, 6)

        b_row = QWidget()
        b_lay = QHBoxLayout(b_row)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(8)
        self.chk_break = QCheckBox("Istirahat otomatis setiap:")
        self.chk_break.stateChanged.connect(lambda s: setattr(self, "break_enabled", bool(s)))
        b_lay.addWidget(self.chk_break)
        self.entry_break_every = QLineEdit("3")
        self.entry_break_every.setFixedWidth(50)
        b_lay.addWidget(self.entry_break_every)
        b_lay.addWidget(QLabel("bab (lanjutkan kembali dengan F9)"))
        b_lay.addStretch()
        bg_lay.addWidget(b_row)
        lay.addWidget(brk_grp)

    def _on_countdown_changed(self, v: int):
        self.countdown_delay = v
        self.lbl_val_countdown.setText(f"{v} detik")

    # =========================================================================
    # Bottom Deck: Tombol Aksi, Progress, Badges, Simulasi
    # =========================================================================
    def _build_bottom_deck(self, lay: QVBoxLayout):
        # ── Tombol Aksi ────────────────────────────────────────────────────────
        btn_row = QWidget()
        b_lay = QHBoxLayout(btn_row)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(4)

        self.btn_start = QPushButton("\u25b6  Mulai Mengetik")
        _bold(self.btn_start, 12)
        self.btn_start.setFixedHeight(40)
        self.btn_start.setStyleSheet(
            "QPushButton{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #22c55e, stop:1 #16a34a);"
            "  border: none; border-radius: 10px;"
            "  color: #ffffff; font-size: 13px; font-weight: 700;"
            "  padding: 0 20px;"
            "}"
            "QPushButton:hover{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #4ade80, stop:1 #22c55e);"
            "}"
            "QPushButton:pressed{ background: #15803d; }"
            "QPushButton:disabled{ background: #808080; color: #d0d0d0; border: 1px solid #707070; }"
        )
        self.btn_start.clicked.connect(lambda: self.start_typing(simulate_only=False))
        b_lay.addWidget(self.btn_start, stretch=1)

        self.btn_sim_only = QPushButton("\U0001f9ea  Tes Simulasi di Layar")
        _bold(self.btn_sim_only)
        self.btn_sim_only.setFixedHeight(40)
        self.btn_sim_only.setStyleSheet(
            "QPushButton{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #7c3aed, stop:1 #a855f7);"
            "  border: none; border-radius: 10px;"
            "  color: #ffffff; font-weight: 600;"
            "  padding: 0 16px;"
            "}"
            "QPushButton:hover{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #9f5af7, stop:1 #c084fc);"
            "}"
            "QPushButton:pressed{ background: #5b21b6; }"
            "QPushButton:disabled{ background: #808080; color: #d0d0d0; border: 1px solid #707070; }"
        )
        self.btn_sim_only.clicked.connect(lambda: self.start_typing(simulate_only=True))
        b_lay.addWidget(self.btn_sim_only)

        self.btn_pause = QPushButton("\u23f8  Pause (F9)")
        self.btn_pause.setFixedHeight(40)
        self.btn_pause.setStyleSheet(
            "QPushButton{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #f97316, stop:1 #ea580c);"
            "  border: none; border-radius: 10px;"
            "  color: #ffffff; font-weight: 600;"
            "}"
            "QPushButton:hover{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #fb923c, stop:1 #f97316);"
            "}"
            "QPushButton:pressed{ background: #c2410c; }"
            "QPushButton:disabled{ background: #808080; color: #d0d0d0; border: 1px solid #707070; }"
        )
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)
        b_lay.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("\u23f9  Berhenti (ESC)")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setStyleSheet(
            "QPushButton{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #ef4444, stop:1 #dc2626);"
            "  border: none; border-radius: 10px;"
            "  color: #ffffff; font-weight: 600;"
            "}"
            "QPushButton:hover{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #f87171, stop:1 #ef4444);"
            "}"
            "QPushButton:pressed{ background: #b91c1c; }"
            "QPushButton:disabled{ background: #808080; color: #d0d0d0; border: 1px solid #707070; }"
        )
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_typing)
        b_lay.addWidget(self.btn_stop)

        self.btn_preview = QPushButton("\U0001f50d  Rincian Format")
        self.btn_preview.setFixedHeight(40)
        self.btn_preview.setStyleSheet(
            "QPushButton{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #3b82f6, stop:1 #2563eb);"
            "  border: none; border-radius: 10px;"
            "  color: #ffffff; font-weight: 600;"
            "}"
            "QPushButton:hover{"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #60a5fa, stop:1 #3b82f6);"
            "}"
            "QPushButton:pressed{ background: #1d4ed8; }"
            "QPushButton:disabled{ background: #808080; color: #d0d0d0; border: 1px solid #707070; }"
        )
        self.btn_preview.clicked.connect(self.open_preview_window)
        b_lay.addWidget(self.btn_preview)

        lay.addWidget(btn_row)

        # ── Progress Bar ────────────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        lay.addWidget(self.progress_bar)

        # ── Status Label ────────────────────────────────────────────────────────
        self.status_label = QLabel(
            "Status: Pilih file, clipboard, atau tautan Google Docs di atas."
        )
        _bold(self.status_label, 10)
        lay.addWidget(self.status_label)

        # ── Badges (Metrik) ─────────────────────────────────────────────────────
        badges_row = QWidget()
        bd_lay = QHBoxLayout(badges_row)
        bd_lay.setContentsMargins(0, 0, 0, 0)
        bd_lay.setSpacing(4)
        self.badge_chars = self._create_badge(bd_lay, "Karakter", "0 / 0 (0%)")
        self.badge_wpm   = self._create_badge(bd_lay, "Kecepatan Aktif", "- WPM")
        self.badge_typo  = self._create_badge(bd_lay, "Typo Aktif", "- %")
        self.badge_eta   = self._create_badge(bd_lay, "Estimasi Waktu", "-")
        lay.addWidget(badges_row)

        # ── Layar Simulasi ──────────────────────────────────────────────────────
        sim = QFrame()
        sim.setObjectName("card")
        sim.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sim_lay = QVBoxLayout(sim)
        sim_lay.setContentsMargins(10, 6, 10, 6)
        sim_lay.setSpacing(4)

        sim_head = QWidget()
        sh_lay = QHBoxLayout(sim_head)
        sh_lay.setContentsMargins(0, 0, 0, 0)
        lbl_sim_h = QLabel("🖥️ Layar Simulasi Auto-Ketik (Live Typing Simulation)")
        _bold(lbl_sim_h, 10)
        sh_lay.addWidget(lbl_sim_h)
        sh_lay.addStretch()
        self.lbl_sim_status = QLabel("● Menunggu Dokumen")
        self.lbl_sim_status.setStyleSheet("color: gray; font-size: 11px; font-weight: bold;")
        sh_lay.addWidget(self.lbl_sim_status)
        sim_lay.addWidget(sim_head)

        self.sim_textbox = QTextEdit()
        self.sim_textbox.setReadOnly(True)
        self.sim_textbox.setFont(QFont("Consolas", 11))
        self.sim_textbox.setPlainText(
            "(Pilih file dokumen, ambil dari clipboard, atau masukkan tautan Google Docs di atas "
            "untuk melihat naskah dan simulasi auto ketiknya di sini...)"
        )
        self.sim_textbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sim_lay.addWidget(self.sim_textbox, stretch=1)
        lay.addWidget(sim, stretch=1)

        # ── Hotkey Strip ────────────────────────────────────────────────────────
        hotkey = QLabel(
            "Tombol Pintas Keyboard:  [Esc] Berhenti   |   [F9] Pause / Lanjut   "
            "|   [F8 / F7] WPM +/-   |   [F10 / F11] Typo +/-"
        )
        hotkey.setStyleSheet("color: gray; font-size: 11px;")
        hotkey.setAlignment(Qt.AlignCenter)
        lay.addWidget(hotkey)

    def _create_badge(self, parent_lay: QHBoxLayout, title: str, initial_val: str) -> QLabel:
        frame = QFrame()
        frame.setObjectName("card")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        frame.setFixedHeight(44)
        f_lay = QVBoxLayout(frame)
        f_lay.setContentsMargins(4, 2, 4, 2)
        f_lay.setSpacing(0)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: gray; font-size: 10px;")
        lbl_t.setAlignment(Qt.AlignCenter)
        f_lay.addWidget(lbl_t)

        lbl_v = QLabel(initial_val)
        _bold(lbl_v, 9)
        lbl_v.setAlignment(Qt.AlignCenter)
        f_lay.addWidget(lbl_v)

        parent_lay.addWidget(frame, stretch=1)
        return lbl_v

    # =========================================================================
    # Memuat & Menampilkan Naskah
    # =========================================================================
    def load_source(self, quiet: bool = False) -> bool:
        try:
            actions, total_chars, total_acts, blocks, plain = self._fetch_actions_and_stats()
            self.loaded_data = {
                "actions": actions,
                "total_chars": total_chars,
                "total_acts": total_acts,
                "blocks": blocks,
                "plain": plain,
            }

            self.badge_chars.setText(f"0 / {total_chars:,} (0%)")
            self._refresh_eta(total_chars)

            source_name = {
                "file": "File Dokumen",
                "clipboard": "Clipboard",
                "gdocs": "Google Docs"
            }.get(self.source_type, "Dokumen")

            self.status_label.setText(
                f"Status: {source_name} siap dimuat ({total_chars:,} karakter, {total_acts} aksi)."
            )

            sample_text = (
                "\n".join(b.text for b in blocks if b.text.strip())
                if blocks else (plain or "")
            )
            preview = sample_text[:400] + ("\n... [dan seterusnya]" if len(sample_text) > 400 else "")
            avg_wpm = (self.wpm_min + self.wpm_max) / 2
            fmt_info = "Dengan Format Dokumen Docs" if (blocks and not self.ignore_format) else "Teks Polos Murni"

            header = (
                f"=== 📄 {source_name.upper()} BERHASIL DIMUAT ===\n"
                f"• Total Karakter: {total_chars:,} | Jumlah Kata: ~{len(sample_text.split()):,}\n"
                f"• Format: {fmt_info} | Estimasi Pengetikan: ~{total_chars / (avg_wpm * 5):.1f} menit\n"
                f"{'-'*75}\n"
                f"Pratinjau Awal Teks:\n{preview}\n\n"
                f">>> Siap! Klik [▶ Mulai Mengetik] atau [🧪 Tes Simulasi di Layar] untuk melihat simulasi ketik di sini."
            )

            self.sim_textbox.setReadOnly(False)
            self.sim_textbox.setPlainText(header)
            self.sim_textbox.setReadOnly(True)

            self.lbl_sim_status.setText("● Siap Diketik")
            self.lbl_sim_status.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
            self.lbl_source_summary.setText(f"✓ {source_name}: {total_chars:,} karakter siap.")
            self.lbl_source_summary.setStyleSheet("color: #2ecc71; font-size: 11px;")
            return True

        except Exception as e:
            self.loaded_data = None
            if not quiet:
                QMessageBox.warning(self, "Perhatian", str(e))
            self.lbl_sim_status.setText("● Gagal Memuat")
            self.lbl_sim_status.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
            self.lbl_source_summary.setText("Belum ada dokumen yang dimuat.")
            self.lbl_source_summary.setStyleSheet("color: gray; font-size: 11px;")
            return False

    def _refresh_eta(self, total_chars: int | None = None):
        if total_chars is None:
            if self.loaded_data:
                total_chars = self.loaded_data.get("total_chars", 0)
            else:
                return
        avg_wpm = (self.wpm_min + self.wpm_max) / 2
        avg_typo = (self.typo_min + self.typo_max) / 2
        self.badge_wpm.setText(f"~{avg_wpm:.0f} WPM")
        self.badge_typo.setText(f"~{avg_typo:.1f}%")
        est = total_chars / (avg_wpm * 5) if avg_wpm > 0 else 0
        self.badge_eta.setText(f"~{int(est * 60)} detik" if est < 1 else f"~{est:.1f} menit")

    # =========================================================================
    # Ekstraksi Aksi Dokumen
    # =========================================================================
    def _fetch_actions_and_stats(self):
        source = self.source_type
        no_format = self.ignore_format
        blocks = None
        plain = None

        if source == "gdocs":
            url = self.entry_url.text().strip()
            if not url:
                raise ValueError("Masukkan tautan Google Docs terlebih dahulu.")
            if no_format:
                plain = fetch_gdoc(url, "txt")
            else:
                raw_html = fetch_gdoc(url, "html")
                blocks = parse_html(raw_html)

        elif source == "file":
            path = self.entry_file.text().strip()
            if not path or not os.path.exists(path):
                raise ValueError("Pilih file dokumen terlebih dahulu.")
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            if path.lower().endswith((".html", ".htm")) and not no_format:
                blocks = parse_html(raw)
            else:
                plain = raw

        else:  # clipboard
            import pyperclip
            plain = pyperclip.paste()
            if not plain or not plain.strip():
                raise ValueError("Isi clipboard kosong. Salin teks terlebih dahulu.")

        if blocks is not None:
            if not blocks:
                raise ValueError("Dokumen HTML kosong atau tidak berisi teks.")
            brk = None
            if self.break_enabled:
                try:
                    brk = parse_range(self.entry_break_every.text(), int)
                except Exception:
                    brk = (3, 3)
            mac = sys.platform == "darwin"
            actions = plan(blocks, base_size=11, mac=mac, break_every=brk)
        else:
            plain = normalize(plain or "")
            if not plain:
                raise ValueError("Teks naskah kosong.")
            actions = [("text", plain)]

        total_chars = sum(len(a[1]) for a in actions if a[0] == "text")
        return actions, total_chars, len(actions), blocks, plain

    # =========================================================================
    # Menjalankan Pengetikan (Thread Terpisah)
    # =========================================================================
    def start_typing(self, simulate_only: bool = False):
        if self.is_running:
            return

        if not self.loaded_data:
            if not self.load_source(quiet=False):
                return

        data = self.loaded_data
        actions = data["actions"]
        total_chars = data["total_chars"]

        if not simulate_only:
            require_pynput()

        try:
            cfg = Config(
                wpm=(float(self.wpm_min), float(self.wpm_max)),
                typo_rate=(self.typo_min / 100.0, self.typo_max / 100.0),
                wave_period=float(self.entry_wave.text()),
                start_fast=self.seg_start.get() == "fast",
                think_every=parse_range(self.entry_think_every.text(), int),
                think_pause=parse_range(self.entry_think_pause.text(), float),
                notice_pause=parse_range(self.entry_typo_delay.text(), float),
                shift_delay=parse_range(self.entry_shift_delay.text(), float),
                typo_words=parse_range(self.entry_typo_words.text(), int),
                mac=sys.platform == "darwin"
            )
        except Exception as e:
            QMessageBox.critical(self, "Pengaturan Tidak Valid", f"Periksa input rentang angka:\n{e}")
            return

        self.is_running = True
        self.stop_requested = False

        self.btn_start.setEnabled(False)
        self.btn_sim_only.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏸  Pause (F9)")
        self.btn_stop.setEnabled(True)
        self.btn_preview.setEnabled(False)
        self.progress_bar.setValue(0)

        self.sim_textbox.setReadOnly(False)
        self.sim_textbox.clear()
        mode = "SIMULASI LAYAR GUI (TANPA KEYBOARD LUAR)" if simulate_only else "PENGETIKAN AKTIF DOKUMEN"
        self.sim_textbox.setPlainText(f"=== {mode} ===\n\n")
        self.sim_textbox.setReadOnly(True)
        self.lbl_sim_status.setText("● Sedang Mengetik...")
        self.lbl_sim_status.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")

        countdown = 0 if simulate_only else self.countdown_delay
        auto_min = False if simulate_only else self.auto_minimize

        self.worker_thread = threading.Thread(
            target=self._run_typing_worker,
            args=(actions, cfg, total_chars, countdown, auto_min, simulate_only),
            daemon=True
        )
        self.worker_thread.start()

    def _run_typing_worker(
        self, actions, cfg, total_chars: int,
        countdown: int, auto_min: bool, simulate_only: bool
    ):
        try:
            if auto_min:
                self._sigs.window_minimize.emit()

            for s in range(countdown, 0, -1):
                if self.stop_requested:
                    self._sigs.status_changed.emit("Dibatalkan sebelum mulai.")
                    self._sigs.controls_reset.emit()
                    return
                self._sigs.status_changed.emit(
                    f"Mulai dalam {s} detik! Klik jendela dokumen tujuan sekarang..."
                )
                time.sleep(1)

            if self.stop_requested:
                self._sigs.status_changed.emit("Dibatalkan.")
                self._sigs.controls_reset.emit()
                return

            self._sigs.status_changed.emit(
                "Sedang menjalankan simulasi di layar GUI... (ESC = Berhenti, F9 = Pause)"
                if simulate_only else
                "Sedang mengetik ke dokumen target... (ESC = Berhenti, F9 = Pause)"
            )

            self.typist = GUITypist(
                cfg,
                on_progress=lambda typed, tot, wpm, typo:
                    self._sigs.progress_updated.emit(typed, tot, wpm, typo),
                on_status=lambda st: self._sigs.status_changed.emit(st),
                on_char=self._sim_append_char,
                on_backspace=self._sim_backspace,
                simulate_only=simulate_only
            )
            self.typist.total_chars = total_chars

            self._start_hotkey_listener()
            self.typist.run(actions)

            self._sigs.status_changed.emit("Pengetikan selesai dengan sempurna! 🎉")
            self._sigs.controls_reset.emit()
            self._sigs.text_appended.emit("\n\n=== [SELESAI: Pengetikan berhasil diselesaikan] ===")
            self._sigs.sim_status_changed.emit("● Selesai", "#2ecc71")

        except StopTyping:
            self._sigs.status_changed.emit("Dihentikan oleh pengguna (ESC).")
            self._sigs.controls_reset.emit()
            self._sigs.text_appended.emit("\n\n=== [DIHENTIKAN OLEH PENGGUNA (ESC)] ===")
            self._sigs.sim_status_changed.emit("● Dihentikan", "#e74c3c")
        except Exception as e:
            self._sigs.status_changed.emit(f"Terjadi kesalahan: {e}")
            self._sigs.controls_reset.emit()
            self._sigs.text_appended.emit(f"\n\n=== [ERROR: {e}] ===")
            self._sigs.sim_status_changed.emit("● Error", "#e74c3c")
        finally:
            self._stop_hotkey_listener()
            self.is_running = False
            self._sigs.window_restore.emit()

    # =========================================================================
    # Simulasi Pengetikan Live — dipanggil dari worker thread → emit signal
    # =========================================================================
    def _sim_append_char(self, ch: str):
        self._sigs.char_appended.emit(ch)

    def _sim_backspace(self, count: int = 1):
        self._sigs.backspace_needed.emit(count)

    # Slots (dieksekusi di main/UI thread)
    @Slot(str)
    def _do_sim_append_char(self, ch: str):
        self.sim_textbox.setReadOnly(False)
        cur = self.sim_textbox.textCursor()
        cur.movePosition(QTextCursor.End)
        cur.insertText("\n" if ch == "\v" else ch)
        self.sim_textbox.setTextCursor(cur)
        self.sim_textbox.ensureCursorVisible()
        self.sim_textbox.setReadOnly(True)

    @Slot(int)
    def _do_sim_backspace(self, count: int):
        self.sim_textbox.setReadOnly(False)
        cur = self.sim_textbox.textCursor()
        cur.movePosition(QTextCursor.End)
        cur.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, count)
        cur.removeSelectedText()
        self.sim_textbox.setTextCursor(cur)
        self.sim_textbox.ensureCursorVisible()
        self.sim_textbox.setReadOnly(True)

    @Slot(str)
    def _do_sim_append_text(self, text: str):
        self.sim_textbox.setReadOnly(False)
        cur = self.sim_textbox.textCursor()
        cur.movePosition(QTextCursor.End)
        cur.insertText(text)
        self.sim_textbox.setTextCursor(cur)
        self.sim_textbox.ensureCursorVisible()
        self.sim_textbox.setReadOnly(True)

    @Slot(str, str)
    def _do_set_sim_status(self, text: str, color: str):
        self.lbl_sim_status.setText(text)
        self.lbl_sim_status.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;"
        )

    # =========================================================================
    # Update UI & Metrik
    # =========================================================================
    @Slot(str)
    def _set_status_text(self, text: str):
        self.status_label.setText(f"Status: {text}")

    @Slot(int, int, float, float)
    def _update_progress_ui(self, typed: int, total: int, wpm: float, typo: float):
        frac = (typed / total) if total > 0 else 0.0
        self.progress_bar.setValue(int(min(1.0, max(0.0, frac)) * 1000))
        pct = int(frac * 100)
        self.badge_chars.setText(f"{typed:,} / {total:,} ({pct}%)")
        self.badge_wpm.setText(f"~{wpm:.0f} WPM")
        self.badge_typo.setText(f"~{typo * 100:.1f}%")
        rem = max(0, total - typed) / (max(10.0, wpm) * 5)
        self.badge_eta.setText(f"~{int(rem * 60)} detik" if rem < 1 else f"~{rem:.1f} menit")

    @Slot()
    def _reset_controls_state(self):
        self.btn_start.setEnabled(True)
        self.btn_sim_only.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸  Pause (F9)")
        self.btn_stop.setEnabled(False)
        self.btn_preview.setEnabled(True)

    @Slot()
    def _restore_window_if_minimized(self):
        try:
            self.showNormal()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    # =========================================================================
    # Kontrol Pause & Stop
    # =========================================================================
    def toggle_pause(self):
        if not self.typist or not self.is_running:
            return
        if self.typist.paused.is_set():
            self.typist.paused.clear()
            self.btn_pause.setText("⏸  Pause (F9)")
            self._set_status_text("Melanjutkan pengetikan...")
            self.lbl_sim_status.setText("● Sedang Mengetik...")
            self.lbl_sim_status.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")
        else:
            self.typist.paused.set()
            self.btn_pause.setText("▶  Lanjut (F9)")
            self._set_status_text("Dijeda. Tekan F9 atau klik Lanjut.")
            self.lbl_sim_status.setText("● Dijeda")
            self.lbl_sim_status.setStyleSheet("color: #e67e22; font-size: 11px; font-weight: bold;")

    def stop_typing(self):
        self.stop_requested = True
        if self.typist:
            self.typist.stop.set()
        self._set_status_text("Menghentikan...")

    # =========================================================================
    # Hotkey Listener Global (pynput) — berjalan di thread pynput
    # =========================================================================
    def _start_hotkey_listener(self):
        if keyboard is None:
            return

        def on_press(key):
            if not self.typist:
                return
            if key == Key.esc:
                self.typist.stop.set()
                return False
            if key == Key.f9:
                if self.typist.paused.is_set():
                    self.typist.paused.clear()
                    self._sigs.status_changed.emit("Melanjutkan pengetikan...")
                    self._sigs.pause_btn_text.emit("⏸  Pause (F9)")
                    self._sigs.sim_status_changed.emit("● Sedang Mengetik...", "#f39c12")
                else:
                    self.typist.paused.set()
                    self._sigs.status_changed.emit("Dijeda. Tekan F9 untuk lanjut.")
                    self._sigs.pause_btn_text.emit("▶  Lanjut (F9)")
                    self._sigs.sim_status_changed.emit("● Dijeda", "#e67e22")
            elif key == Key.f10:
                self.typist.typo_adj += 0.01
                self._sigs.badge_refresh.emit()
            elif key == Key.f11:
                self.typist.typo_adj -= 0.01
                self._sigs.badge_refresh.emit()
            elif key == Key.f8:
                self.typist.wpm_adj += 5
                self._sigs.badge_refresh.emit()
            elif key == Key.f7:
                self.typist.wpm_adj -= 5
                self._sigs.badge_refresh.emit()

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def _stop_hotkey_listener(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    @Slot()
    def _trigger_badge_refresh(self):
        if self.typist:
            self.badge_wpm.setText(f"~{self.typist.cur_wpm():.0f} WPM")
            self.badge_typo.setText(f"~{self.typist.cur_typo() * 100:.1f}%")

    # =========================================================================
    # Jendela Rincian Format
    # =========================================================================
    def open_preview_window(self):
        if not self.loaded_data:
            if not self.load_source(quiet=False):
                return

        data = self.loaded_data
        total_chars = data["total_chars"]
        total_acts  = data["total_acts"]
        blocks      = data["blocks"]
        plain       = data["plain"]

        dlg = QDialog(self)
        dlg.setWindowTitle("Rincian Dokumen & Format")
        dlg.resize(700, 520)
        d_lay = QVBoxLayout(dlg)
        d_lay.setContentsMargins(15, 15, 15, 15)
        d_lay.setSpacing(10)

        avg_wpm = (self.wpm_min + self.wpm_max) / 2
        est_min = total_chars / (avg_wpm * 5) if avg_wpm > 0 else 0

        top = QFrame()
        top.setObjectName("card")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(10, 8, 10, 8)
        info_lbl = QLabel(
            f"Total Karakter: {total_chars:,} | Total Aksi: {total_acts} | "
            f"Estimasi Waktu: ~{est_min:.1f} menit (@ ~{avg_wpm:.0f} WPM)"
        )
        _bold(info_lbl)
        t_lay.addWidget(info_lbl)
        d_lay.addWidget(top)

        txt_box = QTextEdit()
        txt_box.setReadOnly(True)
        txt_box.setFont(QFont("Consolas", 11))

        if blocks:
            lines = [f"=== STRUKTUR PARSING FORMAT GOOGLE DOCS ({len(blocks)} BLOK) ===\n"]
            for k, b in enumerate(blocks, 1):
                tag = f"H{b.heading}" if b.heading else ("LI" if b.lst else "P")
                sizes = sorted({r.size for r in b.runs if r.size})
                flags = "".join(
                    fl for fl, on in (
                        ("B", any(r.b for r in b.runs)),
                        ("I", any(r.i for r in b.runs)),
                        ("U", any(r.u for r in b.runs))
                    ) if on
                )
                snippet = b.text.replace("\v", " / ")[:65]
                lines.append(
                    f"{k:3}. [{tag:<3} {b.align:<7} size={sizes or '-'} flags={flags or '-'}] "
                    f"{snippet!r}"
                )
            txt_box.setPlainText("\n".join(lines))
        else:
            txt_box.setPlainText("=== TEKS POLOS (TANPA FORMAT) ===\n\n" + (plain or ""))

        d_lay.addWidget(txt_box)
        dlg.exec()

    # =========================================================================
    # Window Close Event (pengganti protocol("WM_DELETE_WINDOW", ...))
    # =========================================================================
    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(
                self, "Konfirmasi Keluar",
                "Proses pengetikan sedang berjalan.\nYakin ingin keluar?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_typing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# =============================================================================
# Helper kecil
# =============================================================================
def _bold(widget, pt: int | None = None):
    """Shortcut set font bold (+ukuran opsional) ke widget."""
    f = widget.font()
    f.setBold(True)
    if pt is not None:
        f.setPointSize(pt)
    widget.setFont(f)


# =============================================================================
# Entry Point
# =============================================================================
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = AutoKetikApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
