"""Screen capture + raw input helpers."""
from __future__ import annotations

import io
from typing import Tuple

import mss
import pyautogui
from PIL import Image

# Don't fail-safe at corner: the agent might legitimately move there.
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


def capture_primary(max_dim: int = 1920) -> Tuple[bytes, Tuple[int, int]]:
    """Capture the primary monitor.

    Returns (png_bytes, (width, height)) where width/height match the bytes
    that are actually sent (i.e. after downscaling).
    """
    with mss.mss() as sct:
        # monitors[1] is the primary monitor (monitors[0] is the union of all).
        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        sct_img = sct.grab(mon)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), img.size


def click(x: int, y: int, button: str = "left") -> None:
    pyautogui.click(x=x, y=y, button=button)


def double_click(x: int, y: int) -> None:
    pyautogui.doubleClick(x=x, y=y)


def type_text(text: str) -> None:
    pyautogui.typewrite(text, interval=0.01)


def press(key: str) -> None:
    pyautogui.press(key)


def hotkey(*keys: str) -> None:
    pyautogui.hotkey(*keys)


def scroll(amount: int) -> None:
    """Positive = up, negative = down."""
    pyautogui.scroll(amount)
