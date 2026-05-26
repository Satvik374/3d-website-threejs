"""Entry point: wires up the LLM, hotkey, and chat overlay."""
from __future__ import annotations

import sys
import traceback

from .agent import run_turn
from .hotkey import HotkeyManager
from .llm import CodexAuthMissing, LLMClient
from .overlay import ChatOverlay


def main() -> int:
    try:
        llm = LLMClient(model="gpt-4o")
    except CodexAuthMissing as e:
        # Show a tiny error window instead of silently dying.
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Desktop Agent - missing credentials", str(e))
        return 1

    overlay: ChatOverlay  # forward ref

    def handle_send(text: str) -> None:
        try:
            run_turn(
                llm,
                text,
                log=overlay.append_tool,
                on_assistant_text=overlay.append_assistant,
            )
        except Exception as e:
            tb = traceback.format_exc()
            overlay.append_status(f"error: {e}")
            print(tb, file=sys.stderr)

    def handle_reset() -> None:
        llm.reset()

    overlay = ChatOverlay(on_send=handle_send, on_reset=handle_reset)

    hotkey = HotkeyManager(callback=overlay.toggle)
    hotkey.start()

    overlay.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
