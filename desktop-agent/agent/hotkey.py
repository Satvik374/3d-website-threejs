"""Global Win32 hotkey registration. Runs a message loop on its own thread."""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WM_HOTKEY = 0x0312

VK_8 = 0x38            # On US layout, Shift+8 == "*"
VK_MULTIPLY = 0x6A     # Numpad "*"


class HotkeyManager:
    """Registers Ctrl+Shift+* (both number-row and numpad) as a global hotkey."""

    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        user32 = ctypes.windll.user32
        # Use NULL hWnd: thread-bound hotkey, dispatched via this thread's queue.
        if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_SHIFT, VK_8):
            print("[hotkey] failed to register Ctrl+Shift+8 (*)")
        if not user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_SHIFT, VK_MULTIPLY):
            # Numpad multiply isn't critical; ignore.
            pass

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                try:
                    self.callback()
                except Exception as e:  # pragma: no cover
                    print(f"[hotkey] callback error: {e}")
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
