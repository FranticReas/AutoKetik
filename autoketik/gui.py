"""
autoketik.gui - Antarmuka grafis (GUI) modern berbasis CustomTkinter.
"""

import os
import sys
import threading
import time
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    messagebox.showerror(
        "Library Kurang",
        "CustomTkinter belum terinstal.\nSilakan jalankan:\n\npip install customtkinter"
    )
    sys.exit(1)

from .config import Config, StopTyping, require_pynput, Key, keyboard
from .parser import parse_html, fetch_gdoc, normalize
from .planner import plan, parse_range
from .engine import GUITypist


class AutoKetikApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inisialisasi jendela utama
        self.title("AutoKetik GUI - Human Typing Automation")
        self.geometry("900x850")
        self.minsize(820, 750)

        # State aplikasi
        self.typist = None
        self.worker_thread = None
        self.listener = None
        self.is_running = False
        self.stop_requested = False
        self.loaded_data = None  # Cache naskah yang berhasil dimuat

        # Variabel konfigurasi
        self.source_type = ctk.StringVar(value="file")
        self.file_path_var = ctk.StringVar(value="")
        self.gdocs_url_var = ctk.StringVar(value="")
        self.ignore_format_var = ctk.BooleanVar(value=False)
        self.auto_minimize_var = ctk.BooleanVar(value=True)

        # WPM & Gelombang
        self.wpm_min_var = ctk.DoubleVar(value=45.0)
        self.wpm_max_var = ctk.DoubleVar(value=75.0)
        self.wave_period_var = ctk.DoubleVar(value=120.0)
        self.start_speed_var = ctk.StringVar(value="fast")

        # Typo
        self.typo_min_var = ctk.DoubleVar(value=1.5)  # Persen
        self.typo_max_var = ctk.DoubleVar(value=4.0)
        self.typo_words_var = ctk.StringVar(value="1-3")
        self.typo_delay_var = ctk.StringVar(value="0.8-2.0")

        # Jeda & Hitung Mundur
        self.countdown_delay_var = ctk.IntVar(value=8)
        self.think_every_var = ctk.StringVar(value="8-25")
        self.think_pause_var = ctk.StringVar(value="1.5-6.0")
        self.shift_delay_var = ctk.StringVar(value="0.12-0.3")

        # Bab / Istirahat
        self.break_enabled_var = ctk.BooleanVar(value=False)
        self.break_every_var = ctk.StringVar(value="3")

        # Tampilan tema
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Header Bar
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, height=54)
        self.header_frame.pack(fill="x", padx=15, pady=(12, 6))

        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=12, pady=6)

        self.title_label = ctk.CTkLabel(
            title_box,
            text="⚡ AutoKetik GUI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            title_box,
            text="Simulasi pengetikan alami manusia dengan format dokumen",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.subtitle_label.pack(anchor="w")

        # Pilihan Tema di kanan atas
        theme_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        theme_box.pack(side="right", padx=12)

        self.theme_menu = ctk.CTkOptionMenu(
            theme_box,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode,
            width=90,
            height=26
        )
        self.theme_menu.set("Dark")
        self.theme_menu.pack()

        # ----------------------------------------------------------------------
        # Tab Navigasi Kustom (100% Bebas Redraw & Zero-Flicker)
        # ----------------------------------------------------------------------
        tab_nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_nav_frame.pack(fill="x", padx=15, pady=(4, 2))

        self.main_tab_selector = ctk.CTkSegmentedButton(
            tab_nav_frame,
            values=["📝 Sumber Dokumen", "⚙️ Kecepatan & Typo", "⏱️ Jeda & Istirahat"],
            command=self._on_main_tab_changed,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.main_tab_selector.set("📝 Sumber Dokumen")
        self.main_tab_selector.pack(fill="x")

        # Container Tab Utama dengan tinggi tetap 285px
        self.tab_container = ctk.CTkFrame(self, corner_radius=10, height=285)
        self.tab_container.pack(fill="x", padx=15, pady=(2, 4))
        self.tab_container.pack_propagate(False)
        self.tab_container.grid_propagate(False)
        self.tab_container.grid_rowconfigure(0, weight=1)
        self.tab_container.grid_columnconfigure(0, weight=1)

        # Ketiga frame tab ditempatkan di cell yang sama
        self.tab_source = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_speed = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_advanced = ctk.CTkFrame(self.tab_container, fg_color="transparent")

        self.tab_source.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        self.tab_speed.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        self.tab_advanced.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

        # Sembunyikan tab 2 dan 3 sejak awal
        self.tab_speed.grid_remove()
        self.tab_advanced.grid_remove()

        self._build_source_tab()
        self._build_speed_tab()
        self._build_advanced_tab()

        # Bottom Control, Live Simulation, & Status Deck
        self.bottom_frame = ctk.CTkFrame(self, corner_radius=10)
        self.bottom_frame.pack(fill="both", expand=True, padx=15, pady=(4, 12))

        self._build_bottom_deck()

    def _on_main_tab_changed(self, val):
        if "Sumber Dokumen" in val:
            self.tab_source.grid()
            self.tab_speed.grid_remove()
            self.tab_advanced.grid_remove()
        elif "Kecepatan" in val:
            self.tab_speed.grid()
            self.tab_source.grid_remove()
            self.tab_advanced.grid_remove()
        elif "Jeda" in val:
            self.tab_advanced.grid()
            self.tab_source.grid_remove()
            self.tab_speed.grid_remove()

    # --------------------------------------------------------------------------
    # Tab 1: Sumber Dokumen
    # --------------------------------------------------------------------------
    def _build_source_tab(self):
        tab = self.tab_source

        lbl = ctk.CTkLabel(tab, text="Pilih Sumber Teks:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(anchor="w", padx=4, pady=(2, 2))

        self.source_selector = ctk.CTkSegmentedButton(
            tab,
            values=["📁 File (.txt / .html)", "📋 Clipboard", "🌐 Google Docs URL"],
            command=self._on_source_tab_changed
        )
        self.source_selector.set("📁 File (.txt / .html)")
        self.source_selector.pack(fill="x", padx=4, pady=(0, 6))

        # Kontainer tetap dengan tinggi fixed (115px)
        self.source_container = ctk.CTkFrame(tab, corner_radius=8, height=115)
        self.source_container.pack(fill="x", padx=4, pady=2)
        self.source_container.pack_propagate(False)
        self.source_container.grid_propagate(False)
        self.source_container.grid_rowconfigure(0, weight=1)
        self.source_container.grid_columnconfigure(0, weight=1)

        # Pre-create ketiga kartu input di dalam cell grid yang sama
        self.card_file = ctk.CTkFrame(self.source_container, fg_color="transparent")
        self.card_clipboard = ctk.CTkFrame(self.source_container, fg_color="transparent")
        self.card_gdocs = ctk.CTkFrame(self.source_container, fg_color="transparent")

        self.card_file.grid(row=0, column=0, sticky="nsew", padx=8, pady=4)
        self.card_clipboard.grid(row=0, column=0, sticky="nsew", padx=8, pady=4)
        self.card_gdocs.grid(row=0, column=0, sticky="nsew", padx=8, pady=4)

        self.card_clipboard.grid_remove()
        self.card_gdocs.grid_remove()

        self._build_card_file()
        self._build_card_clipboard()
        self._build_card_gdocs()

        # Baris Opsi & Ringkasan Status Sumber Dokumen
        sub_row = ctk.CTkFrame(tab, fg_color="transparent")
        sub_row.pack(fill="x", padx=4, pady=(8, 2))

        self.chk_no_format = ctk.CTkCheckBox(
            sub_row,
            text="Abaikan format dokumen (ketik sebagai teks polos murni)",
            variable=self.ignore_format_var,
            command=lambda: self.load_source(quiet=True) if self.loaded_data else None
        )
        self.chk_no_format.pack(side="left")

        self.lbl_source_summary = ctk.CTkLabel(
            sub_row,
            text="Belum ada dokumen dimuat.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_source_summary.pack(side="right")

    def _on_source_tab_changed(self, val):
        if "File" in val:
            self.source_type.set("file")
            self.card_file.grid()
            self.card_clipboard.grid_remove()
            self.card_gdocs.grid_remove()
        elif "Clipboard" in val:
            self.source_type.set("clipboard")
            self.card_clipboard.grid()
            self.card_file.grid_remove()
            self.card_gdocs.grid_remove()
        elif "Google Docs" in val:
            self.source_type.set("gdocs")
            self.card_gdocs.grid()
            self.card_file.grid_remove()
            self.card_clipboard.grid_remove()

    def _build_card_file(self):
        lbl = ctk.CTkLabel(
            self.card_file,
            text="Pilih file dokumen teks (.txt) atau file .html hasil Download dari Google Docs:",
            font=ctk.CTkFont(size=12)
        )
        lbl.pack(anchor="w", padx=4, pady=(6, 3))

        f_row = ctk.CTkFrame(self.card_file, fg_color="transparent")
        f_row.pack(fill="x", padx=4, pady=3)

        self.entry_file = ctk.CTkEntry(
            f_row,
            textvariable=self.file_path_var,
            placeholder_text="Klik tombol Browse untuk memilih file dokumen..."
        )
        self.entry_file.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(
            f_row,
            text="Browse...",
            width=90,
            command=self._browse_file
        )
        btn_browse.pack(side="right")

        self.file_info_lbl = ctk.CTkLabel(
            self.card_file,
            text="Tip: File .html otomatis dibaca dengan format heading, tebal, miring, dan spasi.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.file_info_lbl.pack(anchor="w", padx=4, pady=(1, 4))

    def _build_card_clipboard(self):
        lbl = ctk.CTkLabel(
            self.card_clipboard,
            text="Teks akan diambil langsung dari clipboard sistem Anda:",
            font=ctk.CTkFont(size=12)
        )
        lbl.pack(anchor="w", padx=4, pady=(6, 3))

        c_row = ctk.CTkFrame(self.card_clipboard, fg_color="transparent")
        c_row.pack(fill="x", padx=4, pady=3)

        btn_check_clip = ctk.CTkButton(
            c_row,
            text="📋 Muat Teks dari Clipboard Sekarang",
            command=lambda: self.load_source(quiet=False),
            width=260
        )
        btn_check_clip.pack(side="left")

        lbl_hint = ctk.CTkLabel(
            c_row,
            text="(Salin teks dari mana saja, lalu klik tombol ini)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        lbl_hint.pack(side="left", padx=10)

        lbl_clip_note = ctk.CTkLabel(
            self.card_clipboard,
            text="Teks clipboard akan diketik sebagai teks polos tanpa format Google Docs.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        lbl_clip_note.pack(anchor="w", padx=4, pady=(1, 4))

    def _build_card_gdocs(self):
        lbl = ctk.CTkLabel(
            self.card_gdocs,
            text="Masukkan tautan Google Docs (Viewer publik):",
            font=ctk.CTkFont(size=12)
        )
        lbl.pack(anchor="w", padx=4, pady=(6, 3))

        g_row = ctk.CTkFrame(self.card_gdocs, fg_color="transparent")
        g_row.pack(fill="x", padx=4, pady=3)

        self.entry_url = ctk.CTkEntry(
            g_row,
            textvariable=self.gdocs_url_var,
            placeholder_text="https://docs.google.com/document/d/XXXXXXXXX/edit"
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_url.bind("<Return>", lambda e: self.load_source(quiet=False))

        btn_load_gdocs = ctk.CTkButton(
            g_row,
            text="📥 Muat Dokumen",
            width=115,
            command=lambda: self.load_source(quiet=False)
        )
        btn_load_gdocs.pack(side="right")

        lbl_info = ctk.CTkLabel(
            self.card_gdocs,
            text="Pastikan link disetel: 'Anyone with the link (Siapa saja yang memiliki link) – Viewer'.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        lbl_info.pack(anchor="w", padx=4, pady=(1, 4))

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Pilih File Dokumen",
            filetypes=[
                ("Semua File yang Didukung", "*.txt;*.html;*.htm"),
                ("Web Page HTML (*.html;*.htm)", "*.html;*.htm"),
                ("Text File (*.txt)", "*.txt"),
                ("Semua File (*.*)", "*.*")
            ]
        )
        if path:
            self.file_path_var.set(path)
            self.load_source(quiet=False)

    # --------------------------------------------------------------------------
    # Tab 2: Kecepatan & Typo
    # --------------------------------------------------------------------------
    def _build_speed_tab(self):
        tab = self.tab_speed

        preset_frame = ctk.CTkFrame(tab, fg_color="transparent")
        preset_frame.pack(fill="x", padx=4, pady=(4, 2))

        ctk.CTkLabel(preset_frame, text="Preset Kecepatan:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            values=["Santai (40-55 WPM)", "Normal (55-75 WPM)", "Cepat (75-95 WPM)", "Kustom"],
            command=self._apply_preset,
            width=175
        )
        self.preset_menu.set("Normal (55-75 WPM)")
        self.preset_menu.pack(side="right")

        wpm_group = ctk.CTkFrame(tab, corner_radius=8)
        wpm_group.pack(fill="x", padx=4, pady=3)

        # Min WPM
        row_min = ctk.CTkFrame(wpm_group, fg_color="transparent")
        row_min.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_min, text="WPM Minimum (Lambat):", width=160, anchor="w").pack(side="left")
        self.lbl_val_min_wpm = ctk.CTkLabel(row_min, text=f"{int(self.wpm_min_var.get())} WPM", width=60, anchor="e")
        self.lbl_val_min_wpm.pack(side="right")
        self.slider_min_wpm = ctk.CTkSlider(
            row_min,
            from_=15,
            to=120,
            variable=self.wpm_min_var,
            command=lambda v: self._on_wpm_change("min", v)
        )
        self.slider_min_wpm.pack(side="left", fill="x", expand=True, padx=8)

        # Max WPM
        row_max = ctk.CTkFrame(wpm_group, fg_color="transparent")
        row_max.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_max, text="WPM Maksimum (Cepat):", width=160, anchor="w").pack(side="left")
        self.lbl_val_max_wpm = ctk.CTkLabel(row_max, text=f"{int(self.wpm_max_var.get())} WPM", width=60, anchor="e")
        self.lbl_val_max_wpm.pack(side="right")
        self.slider_max_wpm = ctk.CTkSlider(
            row_max,
            from_=20,
            to=150,
            variable=self.wpm_max_var,
            command=lambda v: self._on_wpm_change("max", v)
        )
        self.slider_max_wpm.pack(side="left", fill="x", expand=True, padx=8)

        # Wave & Start
        wave_row = ctk.CTkFrame(wpm_group, fg_color="transparent")
        wave_row.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkLabel(wave_row, text="Periode Siklus (detik):", width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(wave_row, textvariable=self.wave_period_var, width=65).pack(side="left")
        ctk.CTkLabel(wave_row, text="Mulai dari:", width=70, anchor="e").pack(side="left", padx=(15, 5))
        ctk.CTkSegmentedButton(
            wave_row,
            values=["fast", "slow"],
            variable=self.start_speed_var
        ).pack(side="left")

        # Typo
        typo_group = ctk.CTkFrame(tab, corner_radius=8)
        typo_group.pack(fill="x", padx=4, pady=3)

        t_row_min = ctk.CTkFrame(typo_group, fg_color="transparent")
        t_row_min.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(t_row_min, text="Peluang Typo Min (%):", width=160, anchor="w").pack(side="left")
        self.lbl_val_min_typo = ctk.CTkLabel(t_row_min, text=f"{self.typo_min_var.get():.1f}%", width=60, anchor="e")
        self.lbl_val_min_typo.pack(side="right")
        self.slider_min_typo = ctk.CTkSlider(
            t_row_min,
            from_=0.0,
            to=8.0,
            variable=self.typo_min_var,
            command=lambda v: self._on_typo_change("min", v)
        )
        self.slider_min_typo.pack(side="left", fill="x", expand=True, padx=8)

        t_row_max = ctk.CTkFrame(typo_group, fg_color="transparent")
        t_row_max.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(t_row_max, text="Peluang Typo Max (%):", width=160, anchor="w").pack(side="left")
        self.lbl_val_max_typo = ctk.CTkLabel(t_row_max, text=f"{self.typo_max_var.get():.1f}%", width=60, anchor="e")
        self.lbl_val_max_typo.pack(side="right")
        self.slider_max_typo = ctk.CTkSlider(
            t_row_max,
            from_=0.0,
            to=10.0,
            variable=self.typo_max_var,
            command=lambda v: self._on_typo_change("max", v)
        )
        self.slider_max_typo.pack(side="left", fill="x", expand=True, padx=8)

        t_detail_row = ctk.CTkFrame(typo_group, fg_color="transparent")
        t_detail_row.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkLabel(t_detail_row, text="Kata sebelum sadar:").pack(side="left")
        ctk.CTkEntry(t_detail_row, textvariable=self.typo_words_var, width=55).pack(side="left", padx=(4, 15))
        ctk.CTkLabel(t_detail_row, text="Jeda sadar (detik):").pack(side="left")
        ctk.CTkEntry(t_detail_row, textvariable=self.typo_delay_var, width=65).pack(side="left", padx=4)

    def _on_wpm_change(self, which, val):
        if which == "min":
            self.lbl_val_min_wpm.configure(text=f"{int(val)} WPM")
            if val > self.wpm_max_var.get():
                self.wpm_max_var.set(val)
                self.lbl_val_max_wpm.configure(text=f"{int(val)} WPM")
        else:
            self.lbl_val_max_wpm.configure(text=f"{int(val)} WPM")
            if val < self.wpm_min_var.get():
                self.wpm_min_var.set(val)
                self.lbl_val_min_wpm.configure(text=f"{int(val)} WPM")
        self.preset_menu.set("Kustom")
        self._refresh_eta()

    def _on_typo_change(self, which, val):
        if which == "min":
            self.lbl_val_min_typo.configure(text=f"{val:.1f}%")
            if val > self.typo_max_var.get():
                self.typo_max_var.set(val)
                self.lbl_val_max_typo.configure(text=f"{val:.1f}%")
        else:
            self.lbl_val_max_typo.configure(text=f"{val:.1f}%")
            if val < self.typo_min_var.get():
                self.typo_min_var.set(val)
                self.lbl_val_min_typo.configure(text=f"{val:.1f}%")

    def _apply_preset(self, preset):
        if "Santai" in preset:
            self.wpm_min_var.set(40)
            self.wpm_max_var.set(55)
            self.typo_min_var.set(1.0)
            self.typo_max_var.set(2.5)
        elif "Normal" in preset:
            self.wpm_min_var.set(55)
            self.wpm_max_var.set(75)
            self.typo_min_var.set(1.5)
            self.typo_max_var.set(4.0)
        elif "Cepat" in preset:
            self.wpm_min_var.set(75)
            self.wpm_max_var.set(95)
            self.typo_min_var.set(2.5)
            self.typo_max_var.set(5.5)

        self.lbl_val_min_wpm.configure(text=f"{int(self.wpm_min_var.get())} WPM")
        self.lbl_val_max_wpm.configure(text=f"{int(self.wpm_max_var.get())} WPM")
        self.lbl_val_min_typo.configure(text=f"{self.typo_min_var.get():.1f}%")
        self.lbl_val_max_typo.configure(text=f"{self.typo_max_var.get():.1f}%")
        self._refresh_eta()

    # --------------------------------------------------------------------------
    # Tab 3: Jeda, Countdown, & Istirahat
    # --------------------------------------------------------------------------
    def _build_advanced_tab(self):
        tab = self.tab_advanced

        start_group = ctk.CTkFrame(tab, corner_radius=8)
        start_group.pack(fill="x", padx=4, pady=3)

        delay_row = ctk.CTkFrame(start_group, fg_color="transparent")
        delay_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(delay_row, text="Hitung Mundur Mulai (Detik):", width=180, anchor="w").pack(side="left")
        self.lbl_val_countdown = ctk.CTkLabel(delay_row, text=f"{self.countdown_delay_var.get()} detik", width=65, anchor="e")
        self.lbl_val_countdown.pack(side="right")
        self.slider_countdown = ctk.CTkSlider(
            delay_row,
            from_=2,
            to=25,
            variable=self.countdown_delay_var,
            command=lambda v: self.lbl_val_countdown.configure(text=f"{int(v)} detik")
        )
        self.slider_countdown.pack(side="left", fill="x", expand=True, padx=8)

        min_row = ctk.CTkFrame(start_group, fg_color="transparent")
        min_row.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkCheckBox(
            min_row,
            text="Otomatis minimize GUI saat hitung mundur dimulai",
            variable=self.auto_minimize_var
        ).pack(side="left")

        think_group = ctk.CTkFrame(tab, corner_radius=8)
        think_group.pack(fill="x", padx=4, pady=3)

        t_row = ctk.CTkFrame(think_group, fg_color="transparent")
        t_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(t_row, text="Berpikir tiap N kata:").pack(side="left")
        ctk.CTkEntry(t_row, textvariable=self.think_every_var, width=65).pack(side="left", padx=(4, 15))
        ctk.CTkLabel(t_row, text="Durasi jeda (detik):").pack(side="left")
        ctk.CTkEntry(t_row, textvariable=self.think_pause_var, width=65).pack(side="left", padx=4)

        s_row = ctk.CTkFrame(think_group, fg_color="transparent")
        s_row.pack(fill="x", padx=10, pady=(1, 4))
        ctk.CTkLabel(s_row, text="Jeda ekstra Shift / Karakter spesial (detik):").pack(side="left")
        ctk.CTkEntry(s_row, textvariable=self.shift_delay_var, width=65).pack(side="left", padx=4)

        break_group = ctk.CTkFrame(tab, corner_radius=8)
        break_group.pack(fill="x", padx=4, pady=3)

        b_row = ctk.CTkFrame(break_group, fg_color="transparent")
        b_row.pack(fill="x", padx=10, pady=(3, 4))
        ctk.CTkCheckBox(
            b_row,
            text="Istirahat otomatis setiap:",
            variable=self.break_enabled_var
        ).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(b_row, textvariable=self.break_every_var, width=50).pack(side="left", padx=4)
        ctk.CTkLabel(b_row, text="bab (lanjutkan kembali dengan F9)").pack(side="left")

    # --------------------------------------------------------------------------
    # Bottom Deck: Kontrol, Live Simulation, Status & Metrik
    # --------------------------------------------------------------------------
    def _build_bottom_deck(self):
        # Action Buttons
        btn_row = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(8, 4))

        self.btn_start = ctk.CTkButton(
            btn_row,
            text="▶ Mulai Mengetik",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219955",
            height=34,
            command=lambda: self.start_typing(simulate_only=False)
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_sim_only = ctk.CTkButton(
            btn_row,
            text="🧪 Tes Simulasi di Layar",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#7d3c98",
            height=34,
            width=150,
            command=lambda: self.start_typing(simulate_only=True)
        )
        self.btn_sim_only.pack(side="left", padx=3)

        self.btn_pause = ctk.CTkButton(
            btn_row,
            text="⏸ Pause (F9)",
            font=ctk.CTkFont(size=12),
            fg_color="#d35400",
            hover_color="#ba4a00",
            height=34,
            width=105,
            state="disabled",
            command=self.toggle_pause
        )
        self.btn_pause.pack(side="left", padx=3)

        self.btn_stop = ctk.CTkButton(
            btn_row,
            text="⏹ Berhenti (ESC)",
            font=ctk.CTkFont(size=12),
            fg_color="#c0392b",
            hover_color="#a93226",
            height=34,
            width=115,
            state="disabled",
            command=self.stop_typing
        )
        self.btn_stop.pack(side="left", padx=3)

        self.btn_preview = ctk.CTkButton(
            btn_row,
            text="🔍 Rincian Format",
            font=ctk.CTkFont(size=12),
            fg_color="#2980b9",
            hover_color="#2471a3",
            height=34,
            width=115,
            command=self.open_preview_window
        )
        self.btn_preview.pack(side="left", padx=(3, 0))

        # Progress Bar & Status Text
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, height=10)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=12, pady=(6, 2))

        status_strip = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        status_strip.pack(fill="x", padx=12, pady=(2, 2))

        self.status_label = ctk.CTkLabel(
            status_strip,
            text="Status: Pilih file, clipboard, atau tautan Google Docs di atas.",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.status_label.pack(side="left")

        # Badges Row (Metrik)
        metrics_row = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        metrics_row.pack(fill="x", padx=12, pady=(2, 4))

        self.badge_chars = self._create_badge(metrics_row, "Karakter", "0 / 0 (0%)")
        self.badge_wpm = self._create_badge(metrics_row, "Kecepatan Aktif", "- WPM")
        self.badge_typo = self._create_badge(metrics_row, "Typo Aktif", "- %")
        self.badge_eta = self._create_badge(metrics_row, "Estimasi Waktu", "-")

        # Layar Simulasi Pengetikan Real-Time
        sim_container = ctk.CTkFrame(self.bottom_frame, corner_radius=8)
        sim_container.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        sim_head = ctk.CTkFrame(sim_container, fg_color="transparent", height=26)
        sim_head.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            sim_head,
            text="🖥️ Layar Simulasi Auto-Ketik (Live Typing Simulation)",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        self.lbl_sim_status = ctk.CTkLabel(
            sim_head,
            text="● Menunggu Dokumen",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        )
        self.lbl_sim_status.pack(side="right", padx=6)

        # Textbox Simulasi
        self.sim_textbox = ctk.CTkTextbox(
            sim_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            height=130
        )
        self.sim_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.sim_textbox.insert(
            "1.0",
            "(Pilih file dokumen, ambil dari clipboard, atau masukkan tautan Google Docs di atas "
            "untuk melihat naskah dan simulasi auto ketiknya di sini...)"
        )
        self.sim_textbox.configure(state="disabled")

        # Reminder strip
        hotkey_strip = ctk.CTkLabel(
            self.bottom_frame,
            text="Tombol Pintas Keyboard:  [Esc] Berhenti   |   [F9] Pause / Lanjut   |   [F8 / F7] WPM +/-   |   [F10 / F11] Typo +/-",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hotkey_strip.pack(pady=(0, 4))

    def _create_badge(self, parent, title, initial_val):
        frame = ctk.CTkFrame(parent, corner_radius=6, height=38)
        frame.pack(side="left", fill="x", expand=True, padx=3)

        lbl_t = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=10), text_color="gray")
        lbl_t.pack(pady=(1, 0))

        lbl_v = ctk.CTkLabel(frame, text=initial_val, font=ctk.CTkFont(size=11, weight="bold"))
        lbl_v.pack(pady=(0, 2))
        return lbl_v

    # --------------------------------------------------------------------------
    # Memuat & Menampilkan Naskah ke Layar Simulasi
    # --------------------------------------------------------------------------
    def load_source(self, quiet=False):
        try:
            actions, total_chars, total_acts, blocks, plain = self._fetch_actions_and_stats()
            self.loaded_data = {
                "actions": actions,
                "total_chars": total_chars,
                "total_acts": total_acts,
                "blocks": blocks,
                "plain": plain
            }

            self.badge_chars.configure(text=f"0 / {total_chars:,} (0%)")
            self._refresh_eta(total_chars)

            source_name = {
                "file": "File Dokumen",
                "clipboard": "Clipboard",
                "gdocs": "Google Docs"
            }.get(self.source_type.get(), "Dokumen")

            self.status_label.configure(
                text=f"Status: {source_name} siap dimuat ({total_chars:,} karakter, {total_acts} aksi)."
            )

            sample_text = ""
            if blocks:
                sample_text = "\n".join(b.text for b in blocks if b.text.strip())
            else:
                sample_text = plain or ""

            preview_snippet = sample_text[:400] + ("\n... [dan seterusnya]" if len(sample_text) > 400 else "")
            avg_wpm = (self.wpm_min_var.get() + self.wpm_max_var.get()) / 2
            format_info = "Dengan Format Dokumen Docs" if (blocks and not self.ignore_format_var.get()) else "Teks Polos Murni"

            header = (
                f"=== 📄 {source_name.upper()} BERHASIL DIMUAT ===\n"
                f"• Total Karakter: {total_chars:,} | Jumlah Kata: ~{len(sample_text.split()):,}\n"
                f"• Format: {format_info} | Estimasi Pengetikan: ~{total_chars / (avg_wpm * 5):.1f} menit\n"
                f"{'-'*75}\n"
                f"Pratinjau Awal Teks:\n{preview_snippet}\n\n"
                f">>> Siap! Klik [▶ Mulai Mengetik] atau [🧪 Tes Simulasi di Layar] untuk melihat simulasi ketik di sini."
            )

            self.sim_textbox.configure(state="normal")
            self.sim_textbox.delete("1.0", "end")
            self.sim_textbox.insert("1.0", header)
            self.sim_textbox.configure(state="disabled")

            self.lbl_sim_status.configure(text="● Siap Diketik", text_color="#2ecc71")
            self.lbl_source_summary.configure(
                text=f"✓ {source_name}: {total_chars:,} karakter siap.",
                text_color="#2ecc71"
            )
            return True

        except Exception as e:
            self.loaded_data = None
            if not quiet:
                messagebox.showwarning("Perhatian", str(e))
            self.lbl_sim_status.configure(text="● Gagal Memuat", text_color="#e74c3c")
            self.lbl_source_summary.configure(text="Belum ada dokumen yang dimuat.", text_color="gray")
            return False

    def _refresh_eta(self, total_chars=None):
        if total_chars is None:
            if self.loaded_data:
                total_chars = self.loaded_data.get("total_chars", 0)
            else:
                return
        avg_wpm = (self.wpm_min_var.get() + self.wpm_max_var.get()) / 2
        avg_typo = (self.typo_min_var.get() + self.typo_max_var.get()) / 2
        self.badge_wpm.configure(text=f"~{avg_wpm:.0f} WPM")
        self.badge_typo.configure(text=f"~{avg_typo:.1f}%")

        est_mins = total_chars / (avg_wpm * 5) if avg_wpm > 0 else 0
        if est_mins < 1:
            eta_str = f"~{int(est_mins * 60)} detik"
        else:
            eta_str = f"~{est_mins:.1f} menit"
        self.badge_eta.configure(text=eta_str)

    # --------------------------------------------------------------------------
    # Ekstraksi Aksi Dokumen
    # --------------------------------------------------------------------------
    def _fetch_actions_and_stats(self):
        source = self.source_type.get()
        no_format = self.ignore_format_var.get()
        blocks = None
        plain = None

        if source == "gdocs":
            url = self.gdocs_url_var.get().strip()
            if not url:
                raise ValueError("Masukkan tautan Google Docs terlebih dahulu.")
            if no_format:
                plain = fetch_gdoc(url, "txt")
            else:
                raw_html = fetch_gdoc(url, "html")
                blocks = parse_html(raw_html)

        elif source == "file":
            path = self.file_path_var.get().strip()
            if not path or not os.path.exists(path):
                raise ValueError("Pilih file dokumen terlebih dahulu.")
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
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
            if self.break_enabled_var.get():
                try:
                    brk = parse_range(self.break_every_var.get(), int)
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
        total_actions = len(actions)
        return actions, total_chars, total_actions, blocks, plain

    # --------------------------------------------------------------------------
    # Menjalankan Pengetikan (Thread Terpisah)
    # --------------------------------------------------------------------------
    def start_typing(self, simulate_only=False):
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
            wpm = (float(self.wpm_min_var.get()), float(self.wpm_max_var.get()))
            typo_rate = (float(self.typo_min_var.get()) / 100.0, float(self.typo_max_var.get()) / 100.0)
            cfg = Config(
                wpm=wpm,
                typo_rate=typo_rate,
                wave_period=float(self.wave_period_var.get()),
                start_fast=self.start_speed_var.get() == "fast",
                think_every=parse_range(self.think_every_var.get(), int),
                think_pause=parse_range(self.think_pause_var.get(), float),
                notice_pause=parse_range(self.typo_delay_var.get(), float),
                shift_delay=parse_range(self.shift_delay_var.get(), float),
                typo_words=parse_range(self.typo_words_var.get(), int),
                mac=sys.platform == "darwin"
            )
        except Exception as e:
            messagebox.showerror("Pengaturan Tidak Valid", f"Periksa input rentang angka:\n{e}")
            return

        self.is_running = True
        self.stop_requested = False

        self.btn_start.configure(state="disabled")
        self.btn_sim_only.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸ Pause (F9)")
        self.btn_stop.configure(state="normal")
        self.btn_preview.configure(state="disabled")
        self.progress_bar.set(0.0)

        self.sim_textbox.configure(state="normal")
        self.sim_textbox.delete("1.0", "end")
        mode_title = "SIMULASI LAYAR GUI (TANPA KEYBOARD LUAR)" if simulate_only else "PENGETIKAN AKTIF DOKUMEN"
        self.sim_textbox.insert("1.0", f"=== {mode_title} ===\n\n")
        self.sim_textbox.configure(state="disabled")
        self.lbl_sim_status.configure(text="● Sedang Mengetik...", text_color="#f39c12")

        countdown = 0 if simulate_only else int(self.countdown_delay_var.get())
        auto_min = False if simulate_only else self.auto_minimize_var.get()

        self.worker_thread = threading.Thread(
            target=self._run_typing_worker,
            args=(actions, cfg, total_chars, countdown, auto_min, simulate_only),
            daemon=True
        )
        self.worker_thread.start()

    def _run_typing_worker(self, actions, cfg, total_chars, countdown, auto_min, simulate_only):
        try:
            if auto_min:
                self.after(400, self.iconify)

            for s in range(countdown, 0, -1):
                if self.stop_requested:
                    self._post_status("Dibatalkan sebelum mulai.", reset_controls=True)
                    return
                self._post_status(f"Mulai dalam {s} detik! Klik jendela dokumen tujuan sekarang...")
                time.sleep(1)

            if self.stop_requested:
                self._post_status("Dibatalkan.", reset_controls=True)
                return

            if simulate_only:
                self._post_status("Sedang menjalankan simulasi di layar GUI... (ESC = Berhenti, F9 = Pause)")
            else:
                self._post_status("Sedang mengetik ke dokumen target... (ESC = Berhenti, F9 = Pause)")

            self.typist = GUITypist(
                cfg,
                on_progress=lambda typed, tot, wpm, typo: self.after(0, self._update_progress_ui, typed, tot, wpm, typo),
                on_status=lambda st: self.after(0, self._set_status_text, st),
                on_char=self._sim_append_char,
                on_backspace=self._sim_backspace,
                simulate_only=simulate_only
            )
            self.typist.total_chars = total_chars

            self._start_hotkey_listener()
            self.typist.run(actions)

            self._post_status("Pengetikan selesai dengan sempurna! 🎉", reset_controls=True)
            self._sim_append_text("\n\n=== [SELESAI: Pengetikan berhasil diselesaikan] ===")
            self.after(0, lambda: self.lbl_sim_status.configure(text="● Selesai", text_color="#2ecc71"))

        except StopTyping:
            self._post_status("Dihentikan oleh pengguna (ESC).", reset_controls=True)
            self._sim_append_text("\n\n=== [DIHENTIKAN OLEH PENGGUNA (ESC)] ===")
            self.after(0, lambda: self.lbl_sim_status.configure(text="● Dihentikan", text_color="#e74c3c"))
        except Exception as e:
            self._post_status(f"Terjadi kesalahan: {e}", reset_controls=True)
            self._sim_append_text(f"\n\n=== [ERROR: {e}] ===")
            self.after(0, lambda: self.lbl_sim_status.configure(text="● Error", text_color="#e74c3c"))
        finally:
            self._stop_hotkey_listener()
            self.is_running = False
            self.after(0, self._restore_window_if_minimized)

    # --------------------------------------------------------------------------
    # Simulasi Pengetikan Live (Thread-Safe Ke CTkTextbox)
    # --------------------------------------------------------------------------
    def _sim_append_char(self, ch):
        def update():
            self.sim_textbox.configure(state="normal")
            if ch == "\v":
                self.sim_textbox.insert("end", "\n")
            else:
                self.sim_textbox.insert("end", ch)
            self.sim_textbox.see("end")
            self.sim_textbox.configure(state="disabled")
        self.after(0, update)

    def _sim_backspace(self, count=1):
        def update():
            self.sim_textbox.configure(state="normal")
            try:
                self.sim_textbox.delete(f"end-{count+1}c", "end-1c")
                self.sim_textbox.see("end")
            except Exception:
                pass
            self.sim_textbox.configure(state="disabled")
        self.after(0, update)

    def _sim_append_text(self, text):
        def update():
            self.sim_textbox.configure(state="normal")
            self.sim_textbox.insert("end", text)
            self.sim_textbox.see("end")
            self.sim_textbox.configure(state="disabled")
        self.after(0, update)

    # --------------------------------------------------------------------------
    # Update UI & Metrik
    # --------------------------------------------------------------------------
    def _post_status(self, text, reset_controls=False):
        self.after(0, self._set_status_text, text)
        if reset_controls:
            self.after(0, self._reset_controls_state)

    def _set_status_text(self, text):
        self.status_label.configure(text=f"Status: {text}")

    def _update_progress_ui(self, typed, total, wpm, typo):
        frac = (typed / total) if total > 0 else 0.0
        self.progress_bar.set(min(1.0, max(0.0, frac)))

        pct = int(frac * 100)
        self.badge_chars.configure(text=f"{typed:,} / {total:,} ({pct}%)")
        self.badge_wpm.configure(text=f"~{wpm:.0f} WPM")
        self.badge_typo.configure(text=f"~{typo * 100:.1f}%")

        rem_chars = max(0, total - typed)
        avg_wpm = max(10.0, wpm)
        rem_mins = rem_chars / (avg_wpm * 5)
        if rem_mins < 1:
            eta_str = f"~{int(rem_mins * 60)} detik"
        else:
            eta_str = f"~{rem_mins:.1f} menit"
        self.badge_eta.configure(text=eta_str)

    def _reset_controls_state(self):
        self.btn_start.configure(state="normal")
        self.btn_sim_only.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸ Pause (F9)")
        self.btn_stop.configure(state="disabled")
        self.btn_preview.configure(state="normal")

    def _restore_window_if_minimized(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # Kontrol Pause & Stop
    # --------------------------------------------------------------------------
    def toggle_pause(self):
        if not self.typist or not self.is_running:
            return
        if self.typist.paused.is_set():
            self.typist.paused.clear()
            self.btn_pause.configure(text="⏸ Pause (F9)")
            self._set_status_text("Melanjutkan pengetikan...")
            self.lbl_sim_status.configure(text="● Sedang Mengetik...", text_color="#f39c12")
        else:
            self.typist.paused.set()
            self.btn_pause.configure(text="▶ Lanjut (F9)")
            self._set_status_text("Dijeda. Tekan F9 atau klik Lanjut.")
            self.lbl_sim_status.configure(text="● Dijeda", text_color="#e67e22")

    def stop_typing(self):
        self.stop_requested = True
        if self.typist:
            self.typist.stop.set()
        self._set_status_text("Menghentikan...")

    # --------------------------------------------------------------------------
    # Listener Hotkey Global (pynput)
    # --------------------------------------------------------------------------
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
                    self.after(0, self._set_status_text, "Melanjutkan pengetikan...")
                    self.after(0, lambda: self.btn_pause.configure(text="⏸ Pause (F9)"))
                    self.after(0, lambda: self.lbl_sim_status.configure(text="● Sedang Mengetik...", text_color="#f39c12"))
                else:
                    self.typist.paused.set()
                    self.after(0, self._set_status_text, "Dijeda. Tekan F9 untuk lanjut.")
                    self.after(0, lambda: self.btn_pause.configure(text="▶ Lanjut (F9)"))
                    self.after(0, lambda: self.lbl_sim_status.configure(text="● Dijeda", text_color="#e67e22"))
            elif key == Key.f10:
                self.typist.typo_adj += 0.01
                self.after(0, self._trigger_badge_refresh)
            elif key == Key.f11:
                self.typist.typo_adj -= 0.01
                self.after(0, self._trigger_badge_refresh)
            elif key == Key.f8:
                self.typist.wpm_adj += 5
                self.after(0, self._trigger_badge_refresh)
            elif key == Key.f7:
                self.typist.wpm_adj -= 5
                self.after(0, self._trigger_badge_refresh)

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

    def _trigger_badge_refresh(self):
        if self.typist:
            self.badge_wpm.configure(text=f"~{self.typist.cur_wpm():.0f} WPM")
            self.badge_typo.configure(text=f"~{self.typist.cur_typo() * 100:.1f}%")

    # --------------------------------------------------------------------------
    # Jendela Rincian Format
    # --------------------------------------------------------------------------
    def open_preview_window(self):
        if not self.loaded_data:
            if not self.load_source(quiet=False):
                return

        data = self.loaded_data
        total_chars = data["total_chars"]
        total_acts = data["total_acts"]
        blocks = data["blocks"]
        plain = data["plain"]

        w = ctk.CTkToplevel(self)
        w.title("Rincian Dokumen & Format")
        w.geometry("700x520")
        w.transient(self)

        top_info = ctk.CTkFrame(w, corner_radius=8)
        top_info.pack(fill="x", padx=15, pady=(15, 10))

        avg_wpm = (self.wpm_min_var.get() + self.wpm_max_var.get()) / 2
        est_min = total_chars / (avg_wpm * 5)

        info_text = (
            f"Total Karakter: {total_chars:,} | Total Aksi: {total_acts} | "
            f"Estimasi Waktu: ~{est_min:.1f} menit (@ ~{avg_wpm:.0f} WPM)"
        )
        ctk.CTkLabel(top_info, text=info_text, font=ctk.CTkFont(size=12, weight="bold")).pack(padx=10, pady=8)

        txt_box = ctk.CTkTextbox(w, font=ctk.CTkFont(family="Consolas", size=12))
        txt_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        if blocks:
            txt_box.insert("end", f"=== STRUKTUR PARSING FORMAT GOOGLE DOCS ({len(blocks)} BLOK) ===\n\n")
            for k, b in enumerate(blocks, 1):
                tag = f"H{b.heading}" if b.heading else ("LI" if b.lst else "P")
                sizes = sorted({r.size for r in b.runs if r.size})
                flags = "".join(
                    f for f, on in (("B", any(r.b for r in b.runs)),
                                    ("I", any(r.i for r in b.runs)),
                                    ("U", any(r.u for r in b.runs))) if on
                )
                snippet = b.text.replace("\v", " / ")[:65]
                line = (
                    f"{k:3}. [{tag:<3} {b.align:<7} size={sizes or '-'} flags={flags or '-'}] "
                    f"{snippet!r}\n"
                )
                txt_box.insert("end", line)
        else:
            txt_box.insert("end", "=== TEKS POLOS (TANPA FORMAT) ===\n\n")
            txt_box.insert("end", plain)

        txt_box.configure(state="disabled")

    def _on_close(self):
        if self.is_running:
            if messagebox.askyesno("Konfirmasi Keluar", "Proses pengetikan sedang berjalan.\nYakin ingin keluar?"):
                self.stop_typing()
                self.destroy()
        else:
            self.destroy()


def main():
    app = AutoKetikApp()
    app.mainloop()


if __name__ == "__main__":
    main()
