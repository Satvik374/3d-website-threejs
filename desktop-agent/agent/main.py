"""Entry point: wires up the LLM, hotkey, and chat overlay."""
from __future__ import annotations

import os
import sys
import traceback

from .agent import run_turn
from .hotkey import HotkeyManager
from .llm import CodexAuthMissing, LLMClient
from .overlay import ChatOverlay

# Models that show up in the dropdown. The combobox is editable, so the user
# can also type any other model name (e.g. "gpt-5", a fine-tuned model id).
# Only vision-capable models work for screen-look features.
MODEL_PRESETS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4-turbo",
    "o4-mini",
]

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "gpt-4o")


def main() -> int:
    try:
        llm = LLMClient(model=DEFAULT_MODEL)
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

    def handle_model_change(model: str) -> None:
        llm.set_model(model)

    overlay = ChatOverlay(
        on_send=handle_send,
        on_reset=handle_reset,
        on_model_change=handle_model_change,
        models=MODEL_PRESETS,
        current_model=DEFAULT_MODEL,
    )

    hotkey = HotkeyManager(callback=overlay.toggle)
    hotkey.start()

    overlay.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
