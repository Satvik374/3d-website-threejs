"""Translucent always-on-top chat overlay (plain Tk, no extra deps)."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

BG = "#1e1e1e"
BG_INPUT = "#2a2a2a"
FG = "#e6e6e6"
FG_DIM = "#9aa0a6"
FG_USER = "#82b1ff"
FG_TOOL = "#ffd54f"
ACCENT = "#7c4dff"


class ChatOverlay:
    """Small floating chat window. Methods that touch Tk must run on the Tk thread;
    `enqueue` is provided for cross-thread callers."""

    def __init__(
        self,
        on_send: Callable[[str], None],
        on_reset: Callable[[], None],
        on_model_change: Callable[[str], None] | None = None,
        models: list[str] | None = None,
        current_model: str = "gpt-4o",
    ):
        self.on_send = on_send
        self.on_reset = on_reset
        self.on_model_change = on_model_change or (lambda _m: None)
        self._models = models or ["gpt-4o"]
        self._queue: queue.Queue = queue.Queue()
        self._visible = False

        self.root = tk.Tk()
        self.root.title("Desktop Agent")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        # Initial size + position (right side of screen).
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 420, 560
        self.root.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 80}")
        self.root.minsize(320, 400)

        # Header (title + model selector)
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(
            header,
            text="Desktop Agent",
            bg=BG,
            fg=FG,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        # Editable combobox: user can pick a preset OR type any model name.
        self.model_var = tk.StringVar(value=current_model)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Agent.TCombobox",
            fieldbackground=BG_INPUT,
            background=BG_INPUT,
            foreground=FG,
            arrowcolor=FG_DIM,
            bordercolor=BG_INPUT,
            lightcolor=BG_INPUT,
            darkcolor=BG_INPUT,
        )
        self.model_combo = ttk.Combobox(
            header,
            textvariable=self.model_var,
            values=self._models,
            width=14,
            style="Agent.TCombobox",
            font=("Segoe UI", 9),
        )
        self.model_combo.pack(side="right")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)
        self.model_combo.bind("<Return>", self._on_model_changed)
        self.model_combo.bind("<FocusOut>", self._on_model_changed)

        hint = tk.Frame(self.root, bg=BG)
        hint.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(
            hint,
            text="Ctrl+Shift+*  toggle  |  Esc cancel",
            bg=BG,
            fg=FG_DIM,
            font=("Segoe UI", 8),
        ).pack(side="right")

        # Transcript
        self.text = tk.Text(
            self.root,
            bg=BG,
            fg=FG,
            insertbackground=FG,
            wrap="word",
            relief="flat",
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.text.pack(fill="both", expand=True, padx=10, pady=4)
        self.text.tag_configure("user", foreground=FG_USER, font=("Segoe UI", 10, "bold"))
        self.text.tag_configure("assistant", foreground=FG)
        self.text.tag_configure("tool", foreground=FG_TOOL, font=("Consolas", 9))
        self.text.tag_configure("status", foreground=FG_DIM, font=("Segoe UI", 9, "italic"))
        self.text.configure(state="disabled")

        # Input row
        input_frame = tk.Frame(self.root, bg=BG)
        input_frame.pack(fill="x", padx=10, pady=(4, 8))

        self.entry = tk.Text(
            input_frame,
            bg=BG_INPUT,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 10),
            height=2,
            padx=8,
            pady=6,
        )
        self.entry.pack(side="left", fill="both", expand=True)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Shift-Return>", lambda e: None)

        send_btn = tk.Button(
            input_frame,
            text="Send",
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT,
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._submit,
        )
        send_btn.pack(side="right", padx=(8, 0), ipadx=10, ipady=4)

        # Footer with reset
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=10, pady=(0, 6))
        tk.Button(
            footer,
            text="New chat",
            bg=BG,
            fg=FG_DIM,
            activebackground=BG,
            activeforeground=FG,
            relief="flat",
            font=("Segoe UI", 8, "underline"),
            cursor="hand2",
            command=self._reset,
        ).pack(side="left")

        # Globals
        self.root.bind_all("<Escape>", self._on_escape)

        # Hide on close (X) instead of quitting.
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        # Start hidden; the hotkey shows it.
        self.root.withdraw()

        # Pump cross-thread messages.
        self.root.after(50, self._pump)

        self.append_status("Press Ctrl+Shift+* to toggle. Type a message to start.")

    # --- public, thread-safe API ---
    def enqueue(self, fn: Callable[[], None]) -> None:
        self._queue.put(fn)

    def show(self) -> None:
        self.enqueue(self._show)

    def hide(self) -> None:
        self.enqueue(self._hide)

    def toggle(self) -> None:
        self.enqueue(self._toggle)

    def append_user(self, text: str) -> None:
        self.enqueue(lambda: self._append("You: ", text + "\n", "user", "assistant"))

    def append_assistant(self, text: str) -> None:
        self.enqueue(lambda: self._append("Agent: ", text + "\n", "assistant", "assistant"))

    def append_tool(self, text: str) -> None:
        self.enqueue(lambda: self._append("", text + "\n", "tool", "tool"))

    def append_status(self, text: str) -> None:
        self.enqueue(lambda: self._append("", text + "\n", "status", "status"))

    def run(self) -> None:
        self.root.mainloop()

    # --- internal ---
    def _pump(self) -> None:
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn()
                except Exception as e:
                    print(f"[overlay] error: {e}")
        except queue.Empty:
            pass
        self.root.after(40, self._pump)

    def _show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.entry.focus_force()
        self._visible = True

    def _hide(self) -> None:
        self.root.withdraw()
        self._visible = False

    def _toggle(self) -> None:
        if self._visible:
            self._hide()
        else:
            self._show()

    def _append(self, prefix: str, body: str, prefix_tag: str, body_tag: str) -> None:
        self.text.configure(state="normal")
        if prefix:
            self.text.insert("end", prefix, prefix_tag)
        self.text.insert("end", body, body_tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def _on_return(self, event):
        if event.state & 0x0001:  # Shift held -> newline
            return None
        self._submit()
        return "break"

    def _submit(self) -> None:
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return
        self.entry.delete("1.0", "end")
        self.append_user(text)
        # Hand off to caller on a worker thread.
        threading.Thread(target=self.on_send, args=(text,), daemon=True).start()

    def _reset(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.append_status("Conversation reset.")
        self.on_reset()

    def _on_model_changed(self, _event=None):
        new_model = self.model_var.get().strip()
        if not new_model:
            return
        try:
            self.on_model_change(new_model)
            self.append_status(f"model -> {new_model}")
        except Exception as e:
            self.append_status(f"failed to switch model: {e}")
        # Drop focus so subsequent typing goes to the chat input.
        self.entry.focus_set()

    def _on_escape(self, _event=None):
        # ESC inside the text widget shouldn't close; only hide the overlay.
        if self._visible:
            # Don't fight ESC during action-cancel; only hide if input is empty.
            if not self.entry.get("1.0", "end").strip():
                self._hide()
