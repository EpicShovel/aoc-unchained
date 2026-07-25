#!/usr/bin/env python3
"""
AoC Chat Color Script Maker
A tiny desktop helper for Age of Conan Unchained chat colors.

Type or paste your message, apply colors, then save it as a script file
into Age of Conan's Scripts folder (e.g. chat.txt). In-game, type
/chat.txt in any chat channel (global, group, LFG, ...) to show the
colored text.

Requires: Python 3.8+, tkinter (stdlib).
"""

import json
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog

__version__ = "1.0.0"

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


def set_clipboard(text):
    """Copy text to clipboard, preferring pyperclip if available."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except Exception:
        pass

    # Fallback: use Tk clipboard.
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


class AoCChatPaster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"AoC Chat Color Script Maker v{__version__}")
        self.geometry("580x640")
        self.minsize(480, 540)
        self.configure(bg="#0b0b0f")
        self.attributes("-topmost", True)
        self.selected_color = tk.StringVar(value="#ff4500")

        cfg = load_config()
        self.scripts_folder = tk.StringVar(
            value=cfg.get("scripts_folder") or detect_aoc_scripts_folder() or ""
        )
        self.script_name = tk.StringVar(value=cfg.get("script_name") or "chat.txt")

        self._build_ui()
        self._bind_shortcuts()
        self.after(100, lambda: self.entry.focus())

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TFrame", background="#0b0b0f"
        )
        style.configure(
            "TLabel",
            background="#0b0b0f",
            foreground="#9b9589",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Header.TLabel",
            background="#0b0b0f",
            foreground="#c9a24b",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "TButton",
            background="#1e1e28",
            foreground="#e8e6e3",
            font=("Segoe UI", 10),
        )
        style.map("TButton", background=[("active", "#2a2a38")])
        style.configure(
            "Accent.TButton",
            background="#c9a24b",
            foreground="#18140b",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#d4ad5a")],
        )

        main = ttk.Frame(self, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="AoC Chat Color Script Maker", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            main,
            text="Type your message, apply colors, save the script. In-game, type /chat.txt to show the colored text.",
        ).pack(anchor=tk.W, pady=(0, 12))

        # Input area.
        input_frame = tk.Frame(main, bg="#15151c", bd=1, relief=tk.SOLID, highlightbackground="#2a2a36")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.entry = tk.Text(
            input_frame,
            wrap=tk.WORD,
            bg="#15151c",
            fg="#e8e6e3",
            insertbackground="#c9a24b",
            font=("Segoe UI", 12),
            relief=tk.FLAT,
            bd=10,
            height=4,
        )
        self.entry.pack(fill=tk.BOTH, expand=True)
        self.entry.insert("1.0", "Hello Hyboria!")

        # Color toolbar.
        toolbar = tk.Frame(main, bg="#0b0b0f")
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(toolbar, text="Color:", bg="#0b0b0f", fg="#9b9589", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        for name, hex_code in COLORS:
            btn = tk.Button(
                toolbar,
                text=" ",
                bg=hex_code,
                activebackground=hex_code,
                width=2,
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda h=hex_code: self._pick_color(h),
            )
            btn.pack(side=tk.LEFT, padx=1)
            btn.bind("<Enter>", lambda e, h=hex_code: self._show_tooltip(e, h))

        # Custom color picker.
        self.color_btn = tk.Button(
            toolbar,
            text="Custom",
            bg="#ff4500",
            fg="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._choose_custom_color,
        )
        self.color_btn.pack(side=tk.LEFT, padx=(8, 0))

        # Action buttons.
        btn_row = tk.Frame(main, bg="#0b0b0f")
        btn_row.pack(fill=tk.X, pady=(0, 12))

        tk.Button(
            btn_row,
            text="Apply color to selection / all",
            bg="#c9a24b",
            fg="#18140b",
            activebackground="#d4ad5a",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self._apply_color,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_row,
            text="Clear color tags",
            bg="#1e1e28",
            fg="#e8e6e3",
            activebackground="#2a2a38",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._clear_colors,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_row,
            text="Save script & copy command",
            bg="#2d5a27",
            fg="#e8e6e3",
            activebackground="#3a7032",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self._save_script,
        ).pack(side=tk.LEFT)

        # Script destination.
        ttk.Label(main, text="AoC Scripts folder").pack(anchor=tk.W)
        folder_row = tk.Frame(main, bg="#0b0b0f")
        folder_row.pack(fill=tk.X, pady=(0, 10))

        self.folder_entry = tk.Entry(
            folder_row,
            textvariable=self.scripts_folder,
            bg="#08080a",
            fg="#e8e6e3",
            insertbackground="#c9a24b",
            font=("Consolas", 10),
            relief=tk.FLAT,
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        tk.Button(
            folder_row,
            text="Browse...",
            bg="#1e1e28",
            fg="#e8e6e3",
            activebackground="#2a2a38",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._browse_folder,
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Script name.
        ttk.Label(main, text="Script file name").pack(anchor=tk.W)
        name_row = tk.Frame(main, bg="#0b0b0f")
        name_row.pack(fill=tk.X, pady=(0, 10))

        self.name_entry = tk.Entry(
            name_row,
            textvariable=self.script_name,
            bg="#08080a",
            fg="#e8e6e3",
            insertbackground="#c9a24b",
            font=("Consolas", 10),
            relief=tk.FLAT,
        )
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.script_name.trace_add("write", lambda *_: self._update_command())

        # In-game command.
        ttk.Label(main, text="Type this in AoC chat").pack(anchor=tk.W)
        self.command_lbl = tk.Label(
            main,
            text="/chat.txt",
            bg="#08080a",
            fg="#7dd87d",
            font=("Consolas", 12, "bold"),
            anchor=tk.W,
        )
        self.command_lbl.pack(fill=tk.X, ipady=6, pady=(0, 4))

        # Preview and markup output.
        ttk.Label(main, text="Preview").pack(anchor=tk.W)
        self.preview = tk.Label(
            main,
            text="Hello Hyboria!",
            bg="#08080a",
            fg="#e8e6e3",
            font=("Segoe UI", 12),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=500,
        )
        self.preview.pack(fill=tk.X, pady=(0, 12), ipady=8)

        ttk.Label(main, text="AoC markup").pack(anchor=tk.W)
        self.output = tk.Entry(
            main,
            bg="#08080a",
            fg="#e8e6e3",
            insertbackground="#c9a24b",
            font=("Consolas", 10),
            relief=tk.FLAT,
            state="readonly",
        )
        self.output.pack(fill=tk.X, ipady=6)

        self.status = tk.Label(main, text="Ready", bg="#0b0b0f", fg="#c9a24b", anchor=tk.W)
        self.status.pack(fill=tk.X, pady=(8, 0))

        self._update_preview()

    def _bind_shortcuts(self):
        self.entry.bind("<Return>", lambda e: self._save_script())
        self.entry.bind("<Control-Return>", lambda e: self.entry.insert(tk.INSERT, "\n"))

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            title="Select Age of Conan Scripts folder",
            initialdir=self.scripts_folder.get() or os.path.expanduser("~"),
        )
        if folder:
            self.scripts_folder.set(folder)

    def _update_command(self):
        name = self.script_name.get().strip() or "chat.txt"
        self.command_lbl.config(text=f"/{name}")

    def _show_tooltip(self, event, hex_code):
        # Simple tooltip via status bar.
        self.status.config(text=f"Selected color: {hex_code}")
        self.after(800, lambda: self.status.config(text="Ready"))

    def _pick_color(self, hex_code):
        self.selected_color.set(hex_code)
        self.color_btn.config(bg=hex_code)

    def _choose_custom_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color.get(), title="Pick a color")
        if color and color[1]:
            self._pick_color(color[1])

    def _get_markup(self):
        return self.entry.get("1.0", tk.END).rstrip("\n")

    def _update_preview(self):
        markup = self._get_markup()
        self.output.config(state="normal")
        self.output.delete(0, tk.END)
        self.output.insert(0, markup)
        self.output.config(state="readonly")

        # Tk Label doesn't render HTML, so strip tags for a plain-text preview.
        text_only = re.sub(r"<[^>]+>", "", markup)
        self.preview.config(text=text_only if text_only else "(no text)")

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
            wrapped = f'<font color="{hex_code}">{target}</font>'
            self.entry.delete(start, end)
            self.entry.insert(start, wrapped)
        else:
            text = self.entry.get("1.0", tk.END).rstrip("\n")
            text = re.sub(r"<\/?font[^>]*>", "", text)
            self.entry.delete("1.0", tk.END)
            self.entry.insert("1.0", f'<font color="{hex_code}">{text}</font>')

        self._update_preview()

    def _clear_colors(self):
        text = self.entry.get("1.0", tk.END)
        text = re.sub(r"<\/?font[^>]*>", "", text)
        text = text.replace("<br>", "\n")
        self.entry.delete("1.0", tk.END)
        self.entry.insert("1.0", text.rstrip("\n"))
        self._update_preview()

    def _save_script(self, event=None):
        markup = self._get_markup()
        if not markup:
            return

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
                self.status.config(text="No Scripts folder selected — nothing saved")
                return
            self.scripts_folder.set(folder)

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not create folder:\n{exc}")
            return

        path = os.path.join(folder, name)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(markup)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not write:\n{path}\n\n{exc}")
            return

        save_config({
            "scripts_folder": folder,
            "script_name": name,
        })

        command = f"/{name}"
        set_clipboard(command)
        self.status.config(text=f"Saved {name} — pasted command to clipboard: {command}")
        self._update_command()
        self.iconify()


if __name__ == "__main__":
    app = AoCChatPaster()
    app.mainloop()
