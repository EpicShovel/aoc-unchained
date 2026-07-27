#!/usr/bin/env python3
"""
AoC Chat Color Script Maker
A tiny desktop helper for Age of Conan Unchained chat colors.

Pick a color once, type your message, press Enter. The app saves the
markup (single-quoted, the way AoC parses it) into Age of Conan's Scripts
folder (e.g. chat.txt) and copies /chat.txt to your clipboard.
In game: click the chat box, Ctrl+V, Enter — colored text in your
current channel.

Requires: Python 3.8+, tkinter (stdlib).
"""

import json
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog

__version__ = "1.9.0"

COLORS = [
    ("Red", "#ff0000"),
    ("Green", "#00ff00"),
    ("Blue", "#0000ff"),
    ("Yellow", "#ffff00"),
    ("Cyan", "#00ffff"),
    ("Magenta", "#ff00ff"),
    ("Orange", "#ffa500"),
    ("Purple", "#800080"),
    ("Gold", "#ffd700"),
    ("Pink", "#ff69b4"),
    ("White", "#ffffff"),
    ("Gray", "#aaaaaa"),
]

# ── Theme ──────────────────────────────────────────────────────────────────
BG        = "#0a0a10"
PANEL     = "#12121a"
PANEL_2   = "#1a1a26"
INPUT_BG  = "#08080c"
BORDER    = "#262633"
TEXT      = "#e8e6e3"
MUTED     = "#9b9589"
GOLD      = "#c9a24b"
GOLD_HI   = "#e8c877"
GREEN     = "#7dd87d"
GREEN_BG  = "#2d5a27"
GREEN_HI  = "#3a7032"
WARN      = "#f59e0b"

FONT_UI    = ("Segoe UI", 11)
FONT_UI_B  = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUB   = ("Segoe UI", 10)
FONT_EDIT  = ("Segoe UI", 13)
FONT_MONO  = ("Consolas", 11)
FONT_BIG   = ("Consolas", 15, "bold")


def set_clipboard(text):
    """Copy text to clipboard, preferring pyperclip if available."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except Exception:
        pass
    root = tk._default_root
    if root is None:
        root = tk.Tk()
        root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)


def _app_config_dir():
    """Per-user folder for this app's own settings."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "AoC Chat Color Script Maker")
    os.makedirs(path, exist_ok=True)
    return path


def load_config():
    try:
        with open(os.path.join(_app_config_dir(), "config.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(os.path.join(_app_config_dir(), "config.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except Exception:
        pass


def detect_aoc_scripts_folder():
    """Best-effort detection of Age of Conan's Scripts folder."""
    candidates = []
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.environ.get(env)
        if not root:
            continue
        for sub in (
            os.path.join(root, "Funcom", "Age of Conan", "Scripts"),
            os.path.join(root, "Age of Conan Unchained", "Scripts"),
            os.path.join(root, "Steam", "steamapps", "common", "Age of Conan", "Scripts"),
        ):
            candidates.append(sub)
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def enable_dpi_awareness():
    """Sharp rendering on high-DPI displays."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class Tooltip:
    """Small popup hint shown after hovering a widget for a moment."""

    DELAY_MS = 350

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        self._after_id = None
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)
        frame = tk.Frame(tip, bg=GOLD, padx=1, pady=1)
        frame.pack()
        tk.Label(
            frame, text=self.text,
            bg=PANEL_2, fg=TEXT, font=FONT_SUB,
            padx=9, pady=5, justify=tk.LEFT, wraplength=300,
        ).pack()
        self.tip = tip

    def _hide(self, event=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class AoCChatPaster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"AoC Chat Color Script Maker v{__version__}")
        self.geometry("560x600")
        self.minsize(480, 520)
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        self.selected_color = tk.StringVar(value="#ff4500")

        cfg = load_config()
        self.scripts_folder = tk.StringVar(
            value=cfg.get("scripts_folder") or detect_aoc_scripts_folder() or ""
        )
        self.script_name = tk.StringVar(value=cfg.get("script_name") or "chat.txt")
        self.auto_color_var = tk.BooleanVar(value=cfg.get("auto_color", True))
        self.swatch_btns = {}
        self._last_status = "Ready"

        self._build_statusbar()
        self._build_ui()
        self._bind_shortcuts()
        self._pick_color(self.selected_color.get())
        self.after(100, lambda: self.entry.focus())

    # ── UI construction ────────────────────────────────────────────────────

    def _mk_button(self, parent, text, command, bg=PANEL_2, fg=TEXT, hi="#2a2a3a", bold=True):
        btn = tk.Label(
            parent, text=text, bg=bg, fg=fg,
            font=("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10),
            padx=10, pady=5, cursor="hand2",
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=hi))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _mk_section(self, parent, text):
        row = tk.Frame(parent, bg=BG)
        tk.Label(row, text=text.upper(), bg=BG, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Frame(row, bg=BORDER, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=6)
        return row

    def _build_ui(self):
        # Scrollable container: canvas + inner frame, mouse wheel scrolls it.
        self.scroll_canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.scroll_canvas.yview,
                           bg=PANEL_2, troughcolor=BG, activebackground=GOLD,
                           relief=tk.FLAT, bd=0, width=12)
        self.scroll_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main = tk.Frame(self.scroll_canvas, bg=BG, padx=12, pady=10)
        win_id = self.scroll_canvas.create_window((0, 0), window=main, anchor=tk.NW)

        def on_frame_configure(event=None):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

        def on_canvas_configure(event):
            self.scroll_canvas.itemconfigure(win_id, width=event.width)

        main.bind("<Configure>", on_frame_configure)
        self.scroll_canvas.bind("<Configure>", on_canvas_configure)

        def on_wheel(event):
            self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

        # Wheel events go to the widget under the cursor; bind globally.
        self.bind_all("<MouseWheel>", on_wheel)

        # ── Header: slim gradient band ──
        header = tk.Canvas(main, height=40, bg=BG, highlightthickness=0, bd=0)
        header.pack(fill=tk.X, pady=(0, 4))

        def paint_header(event=None):
            header.delete("all")
            w = header.winfo_width() or 536
            steps = 40
            for i in range(steps):
                t = i / (steps - 1)
                r1, g1, b1 = (0x38, 0x1a, 0x08)
                r2, g2, b2 = (0x66, 0x4d, 0x1c)
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                x0 = int(w * i / steps)
                x1 = int(w * (i + 1) / steps) + 1
                header.create_rectangle(x0, 0, x1, 40, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
            header.create_rectangle(0, 38, w, 40, fill=GOLD, outline="")
            header.create_text(12, 20, anchor=tk.W, text="AoC CHAT COLOR",
                               font=("Segoe UI", 14, "bold"), fill=GOLD_HI)
            header.create_text(w - 10, 20, anchor=tk.E, text=f"v{__version__}",
                               font=FONT_SUB, fill=MUTED)

        header.bind("<Configure>", paint_header)

        sub_row = tk.Frame(main, bg=BG)
        sub_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            sub_row, text="made by EpicShovel",
            bg=BG, fg="#b06bff", font=("Segoe UI", 9, "bold"), anchor=tk.E,
        ).pack(side=tk.RIGHT)
        tk.Label(
            sub_row,
            text="Pick a color, type, press Enter — /chat.txt is copied. Ctrl+V it in game chat.",
            bg=BG, fg=MUTED, font=FONT_SUB, anchor=tk.W, justify=tk.LEFT,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Message input ──
        self.input_frame = tk.Frame(main, bg=BORDER, padx=1, pady=1)
        self.input_frame.pack(fill=tk.X, pady=(0, 8))

        self.entry = tk.Text(
            self.input_frame,
            wrap=tk.WORD,
            bg=INPUT_BG, fg=TEXT,
            insertbackground=GOLD,
            selectbackground=GOLD, selectforeground="#18140b",
            font=FONT_EDIT, relief=tk.FLAT, bd=8, height=2,
        )
        self.entry.pack(fill=tk.X)
        self.entry.insert("1.0", "Hello Hyboria!")
        self.entry.bind("<FocusIn>", lambda e: self.input_frame.config(bg=GOLD))
        self.entry.bind("<FocusOut>", lambda e: self.input_frame.config(bg=BORDER))
        Tooltip(self.entry, "Type your message here.\nPress Enter to save it and copy the /command.")

        # ── Color picker + auto-color ──
        toolbar = tk.Frame(main, bg=BG)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        for name, hex_code in COLORS:
            cell = tk.Frame(toolbar, bg=BG, padx=1, pady=1)
            cell.pack(side=tk.LEFT)
            btn = tk.Label(
                cell, text="  ", bg=hex_code, width=2, cursor="hand2",
                relief=tk.FLAT, bd=0, font=("Segoe UI", 9),
            )
            btn.pack()
            btn.bind("<Button-1>", lambda e, h=hex_code: self._pick_color(h))
            Tooltip(btn, f"{name} {hex_code}\nClick to color your messages this way.")
            self.swatch_btns[hex_code] = (cell, btn)

        self.color_btn = self._mk_button(toolbar, "Custom…", self._choose_custom_color)
        self.color_btn.pack(side=tk.LEFT, padx=(8, 0))
        Tooltip(self.color_btn, "Pick any color with the color dialog.")

        self.auto_cb = tk.Checkbutton(
            toolbar,
            text="Always use selected color (no Apply needed)",
            variable=self.auto_color_var,
            bg=BG, fg=MUTED, selectcolor=PANEL_2,
            activebackground=BG, activeforeground=TEXT,
            font=FONT_SUB,
            command=self._update_preview,
        )
        self.auto_cb.pack(side=tk.RIGHT)
        Tooltip(self.auto_cb,
                "On: everything you type is sent in the selected color automatically.\n"
                "Off: colors are only added where you press Apply.")

        # ── Action buttons ──
        btn_row = tk.Frame(main, bg=BG)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        apply_btn = self._mk_button(btn_row, "Apply color", self._apply_color,
                        bg=GOLD, fg="#18140b", hi=GOLD_HI)
        apply_btn.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(apply_btn,
                "Wraps the highlighted text in color tags.\n"
                "Nothing highlighted? The whole message is wrapped.")
        clear_btn = self._mk_button(btn_row, "Clear tags", self._clear_colors)
        clear_btn.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(clear_btn, "Removes all <font> color tags from the message.")
        save_btn = self._mk_button(btn_row, "Save & copy /command", self._save_script,
                        bg=GREEN_BG, fg=TEXT, hi=GREEN_HI)
        save_btn.pack(side=tk.LEFT)
        Tooltip(save_btn,
                "Writes the script into your AoC Scripts folder\n"
                "and copies the /command to your clipboard.")

        # ── Script destination ──
        folder_row = tk.Frame(main, bg=BG)
        folder_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(folder_row, text="Scripts:", bg=BG, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.folder_entry = tk.Entry(
            folder_row, textvariable=self.scripts_folder,
            bg=INPUT_BG, fg=TEXT, insertbackground=GOLD,
            font=("Consolas", 9), relief=tk.FLAT, bd=6,
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        Tooltip(self.folder_entry,
                "Age of Conan's Scripts folder — the game reads .txt chat scripts from here.")
        browse_btn = self._mk_button(folder_row, "Browse…", self._browse_folder)
        browse_btn.pack(side=tk.LEFT, padx=(6, 0))
        Tooltip(browse_btn, "Pick the Scripts folder with a dialog.")
        open_btn = self._mk_button(folder_row, "Open", self._open_folder)
        open_btn.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(open_btn, "Open the Scripts folder in Explorer.")

        # ── Script name + in-game command on one row ──
        name_row = tk.Frame(main, bg=BG)
        name_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(name_row, text="File:", bg=BG, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.name_entry = tk.Entry(
            name_row, textvariable=self.script_name, width=14,
            bg=INPUT_BG, fg=TEXT, insertbackground=GOLD,
            font=("Consolas", 9), relief=tk.FLAT, bd=6,
        )
        self.name_entry.pack(side=tk.LEFT)
        self.script_name.trace_add("write", lambda *_: self._update_command())
        Tooltip(self.name_entry,
                "The file name IS the in-game command:\nchat.txt is run by typing /chat.txt in game chat.")

        cmd_frame = tk.Frame(name_row, bg=BORDER, padx=1, pady=1)
        cmd_frame.pack(side=tk.RIGHT)
        self.command_lbl = tk.Label(
            cmd_frame, text="/chat.txt",
            bg=INPUT_BG, fg=GREEN, font=("Consolas", 12, "bold"), anchor=tk.W, padx=8, pady=3,
        )
        self.command_lbl.pack()
        Tooltip(self.command_lbl,
                "Paste this in the game chat (Ctrl+V) and press Enter\n"
                "to show your colored message.")

        self.saved_lbl = tk.Label(
            main, text="Not saved yet",
            bg=BG, fg=MUTED, font=("Consolas", 8),
            anchor=tk.W, wraplength=520, justify=tk.LEFT,
        )
        self.saved_lbl.pack(fill=tk.X, pady=(0, 8))

        # ── Preview ──
        prev_frame = tk.Frame(main, bg=BORDER, padx=1, pady=1)
        prev_frame.pack(fill=tk.X, pady=(0, 8))
        self.preview = tk.Label(
            prev_frame, text="Hello Hyboria!",
            bg=INPUT_BG, fg=TEXT, font=FONT_EDIT,
            anchor=tk.W, justify=tk.LEFT, wraplength=520, padx=8, pady=6,
        )
        self.preview.pack(fill=tk.X)
        Tooltip(self.preview, "How your message will look in game.")

        # ── Markup output (the readonly-background bug lived here) ──
        markup_head = tk.Frame(main, bg=BG)
        markup_head.pack(fill=tk.X, pady=(0, 2))
        tk.Label(markup_head, text="MARKUP", bg=BG, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.counter_lbl = tk.Label(markup_head, text="0 chars", bg=BG, fg=MUTED, font=FONT_SUB)
        self.counter_lbl.pack(side=tk.RIGHT)
        Tooltip(self.counter_lbl,
                "Length of the generated markup.\nVery long messages wrap in the game chat window.")

        self.output = tk.Entry(
            main,
            bg=INPUT_BG, fg=GREEN, insertbackground=GOLD,
            readonlybackground=INPUT_BG,   # <-- the white-on-white fix
            font=("Consolas", 9), relief=tk.FLAT, bd=6,
            state="readonly",
        )
        self.output.pack(fill=tk.X)
        Tooltip(self.output, "The exact text written into the script file.")

        self._update_preview()

    def _build_statusbar(self):
        """Fixed status bar at the bottom of the window (outside the scroll area)."""
        status_frame = tk.Frame(self, bg=PANEL, padx=1, pady=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status = tk.Label(
            status_frame, text="Ready", bg=PANEL, fg=GOLD,
            font=FONT_SUB, anchor=tk.W, padx=8, pady=4,
        )
        self.status.pack(fill=tk.X)

    def _bind_shortcuts(self):
        self.entry.bind("<Return>", lambda e: self._save_script())
        self.entry.bind("<Control-Return>", lambda e: self.entry.insert(tk.INSERT, "\n"))
        self.entry.bind("<KeyRelease>", lambda e: self._update_preview())

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_status(self, text):
        self._last_status = text
        self.status.config(text=text)

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            title="Select Age of Conan Scripts folder",
            initialdir=self.scripts_folder.get() or os.path.expanduser("~"),
        )
        if folder:
            self.scripts_folder.set(folder)

    def _open_folder(self):
        folder = self.scripts_folder.get().strip()
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        else:
            self._set_status("Set a valid Scripts folder first")

    def _update_command(self):
        name = self.script_name.get().strip() or "chat.txt"
        self.command_lbl.config(text=f"/{name}")

    def _pick_color(self, hex_code):
        self.selected_color.set(hex_code)
        for h, (cell, btn) in self.swatch_btns.items():
            cell.config(bg="#ffffff" if h == hex_code else BG)
        self._update_preview()

    def _choose_custom_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color.get(), title="Pick a color")
        if color and color[1]:
            self._pick_color(color[1])

    def _get_markup(self):
        return self.entry.get("1.0", tk.END).rstrip("\n")

    def _effective_markup(self):
        """Markup that will be saved: auto-color wraps plain text on the fly.

        AoC markup must use SINGLE quotes — double quotes are not parsed.
        """
        markup = self._get_markup()
        if markup and self.auto_color_var.get() and "<font" not in markup.lower():
            markup = f"<font color='{self.selected_color.get()}'>{markup}</font>"
        return markup

    def _update_preview(self):
        markup = self._effective_markup()
        self.output.config(state="normal")
        self.output.delete(0, tk.END)
        self.output.insert(0, markup)
        self.output.config(state="readonly")

        n = len(markup)
        self.counter_lbl.config(
            text=f"{n} chars",
            fg=WARN if n > 900 else MUTED,
        )

        text_only = re.sub(r"<[^>]+>", "", markup)
        fg = TEXT
        if self.auto_color_var.get() and "<font" not in self._get_markup().lower():
            fg = self.selected_color.get()
        self.preview.config(text=text_only if text_only else "(no text)", fg=fg)

    def _apply_color(self):
        hex_code = self.selected_color.get()
        try:
            sel = self.entry.tag_ranges(tk.SEL)
        except tk.TclError:
            sel = ()

        if sel:
            start, end = sel
            target = self.entry.get(start, end)
            target = re.sub(r"<\/?font[^>]*>", "", target)
            wrapped = f"<font color='{hex_code}'>{target}</font>"
            self.entry.delete(start, end)
            self.entry.insert(start, wrapped)
        else:
            text = self.entry.get("1.0", tk.END).rstrip("\n")
            text = re.sub(r"<\/?font[^>]*>", "", text)
            self.entry.delete("1.0", tk.END)
            self.entry.insert("1.0", f"<font color='{hex_code}'>{text}</font>")

        self._update_preview()

    def _clear_colors(self):
        text = self.entry.get("1.0", tk.END)
        text = re.sub(r"<\/?font[^>]*>", "", text)
        text = text.replace("<br>", "\n")
        self.entry.delete("1.0", tk.END)
        self.entry.insert("1.0", text.rstrip("\n"))
        self._update_preview()

    def _save_script(self, event=None):
        """Save the script; returns (path, command) on success, (None, None) otherwise."""
        markup = self._effective_markup()
        if not markup:
            self._set_status("Nothing to save — type a message first")
            return None, None

        folder = self.scripts_folder.get().strip()
        name = self.script_name.get().strip()
        if not name:
            name = "chat.txt"
            self.script_name.set(name)
        if not name.lower().endswith(".txt"):
            name += ".txt"
            self.script_name.set(name)
        # AoC script names are one token; keep it filesystem-safe.
        name = re.sub(r'[<>:"/\\|?*\s]+', "_", name)

        if not folder:
            folder = filedialog.askdirectory(
                title="Select Age of Conan Scripts folder",
                initialdir=os.path.expanduser("~"),
            )
            if not folder:
                self._set_status("No Scripts folder selected — nothing saved")
                return None, None
            self.scripts_folder.set(folder)

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not create folder:\n{exc}")
            return None, None

        path = os.path.join(folder, name)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(markup)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not write:\n{path}\n\n{exc}")
            return None, None

        save_config({
            "scripts_folder": folder,
            "script_name": name,
            "auto_color": bool(self.auto_color_var.get()),
        })

        command = f"/{name}"
        set_clipboard(command)
        self.saved_lbl.config(text=f"Saved: {path}")
        self._set_status(f"Saved {name} — {command} copied; Ctrl+V it in game chat")
        self._update_command()
        return path, command


if __name__ == "__main__":
    enable_dpi_awareness()
    app = AoCChatPaster()
    app.mainloop()
