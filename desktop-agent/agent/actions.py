"""Execute model tool calls with a 1-second preview that ESC can cancel."""
from __future__ import annotations

import ctypes
import json
import time
from typing import Any, Callable

from . import screen

VK_ESCAPE = 0x1B
PREVIEW_SECONDS = 1.0


def _esc_pressed() -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)


def _wait_with_cancel(seconds: float, on_tick: Callable[[float], None] | None = None) -> bool:
    """Sleep up to `seconds`. Return True if cancelled by ESC."""
    end = time.time() + seconds
    # Drain any prior ESC press.
    ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE)
    while time.time() < end:
        if _esc_pressed():
            return True
        if on_tick:
            on_tick(end - time.time())
        time.sleep(0.03)
    return False


def execute_tool_call(
    name: str,
    arguments: dict[str, Any],
    log: Callable[[str], None],
) -> dict[str, Any]:
    """Run a tool call. Returns a JSON-serialisable result for the model."""

    if name == "screen_capture":
        log("[capturing screen]")
        png, size = screen.capture_primary()
        return {"_screenshot_png": png, "size": size}

    if name in ("click", "double_click"):
        x = int(arguments["x"])
        y = int(arguments["y"])
        btn = arguments.get("button", "left")
        verb = "double-click" if name == "double_click" else f"{btn} click"
        log(f"-> about to {verb} at ({x}, {y})  [hold ESC to cancel]")
        cancelled = _wait_with_cancel(PREVIEW_SECONDS)
        if cancelled:
            log("   cancelled")
            return {"status": "cancelled_by_user"}
        if name == "click":
            screen.click(x, y, btn)
        else:
            screen.double_click(x, y)
        return {"status": "ok"}

    if name == "type_text":
        text = str(arguments["text"])
        log(f'-> typing "{text}"  [hold ESC to cancel]')
        if _wait_with_cancel(PREVIEW_SECONDS):
            log("   cancelled")
            return {"status": "cancelled_by_user"}
        screen.type_text(text)
        return {"status": "ok"}

    if name == "press_key":
        key = str(arguments["key"])
        log(f"-> pressing {key}  [hold ESC to cancel]")
        if _wait_with_cancel(PREVIEW_SECONDS):
            log("   cancelled")
            return {"status": "cancelled_by_user"}
        screen.press(key)
        return {"status": "ok"}

    if name == "hotkey":
        keys = list(arguments.get("keys", []))
        log(f"-> hotkey {'+'.join(keys)}  [hold ESC to cancel]")
        if _wait_with_cancel(PREVIEW_SECONDS):
            log("   cancelled")
            return {"status": "cancelled_by_user"}
        screen.hotkey(*keys)
        return {"status": "ok"}

    if name == "scroll":
        direction = arguments.get("direction", "down")
        amount = int(arguments.get("amount", 3))
        delta = amount if direction == "up" else -amount
        log(f"-> scrolling {direction} {amount}")
        screen.scroll(delta * 100)  # pyautogui scroll units
        return {"status": "ok"}

    return {"status": "error", "error": f"unknown tool {name!r}"}
