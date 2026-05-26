"""LLM client. Tries to find credentials from ~/.codex/auth.json (set up by
`codex login`) or from the OPENAI_API_KEY environment variable, then talks to
OpenAI's Chat Completions API with vision + tool calls.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Iterable

from openai import OpenAI

from .tools import TOOL_SCHEMAS


SYSTEM_PROMPT = """You are a desktop assistant running on the user's Windows machine.

Behave like a concise chat assistant for normal questions. When the user asks
you to LOOK at the screen, FIND something on screen, CLICK, TYPE, or otherwise
interact with the desktop, use your tools.

Tools you can call:
- screen_capture(): take a screenshot. Call this BEFORE clicking/typing if you
  need to see what's on screen. The result will be sent back to you as an
  image.
- click(x, y, button="left"): click at pixel coordinates of the most recent
  screenshot.
- double_click(x, y): double-click.
- type_text(text): type a literal string at the current focus.
- press_key(key): press one key like "enter", "esc", "tab", "win".
- hotkey(keys): chord of keys, e.g. ["ctrl", "c"].
- scroll(direction, amount): "up" or "down", amount in clicks.

Coordinate system: (0,0) is the top-left of the captured screenshot. Use the
exact pixel size of the screenshot you received.

Be brief. When you are about to act, say one short sentence describing the
plan, then call the tool. After the user's task is done, just confirm.

Only request a screenshot when the user actually asks you to look at, find,
click, or otherwise interact with the screen.
"""


def _load_api_key() -> str | None:
    """Look for an OpenAI API key. Order of preference:
    1. OPENAI_API_KEY env var.
    2. ~/.codex/auth.json (key field if codex login stored one).
    3. ~/.codex/config.toml fallback (older versions).
    """
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]

    auth_path = Path.home() / ".codex" / "auth.json"
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for field in ("OPENAI_API_KEY", "openai_api_key", "api_key", "apiKey"):
            if data.get(field):
                return data[field]
        # Some installs nest credentials.
        if isinstance(data.get("credentials"), dict):
            for field in ("OPENAI_API_KEY", "openai_api_key", "api_key"):
                if data["credentials"].get(field):
                    return data["credentials"][field]

    return None


class CodexAuthMissing(RuntimeError):
    pass


class LLMClient:
    """Thin wrapper around OpenAI Chat Completions with vision + tools."""

    def __init__(self, model: str = "gpt-4o"):
        key = _load_api_key()
        if not key:
            raise CodexAuthMissing(
                "No OpenAI credentials found.\n"
                "Either:\n"
                "  1) Run `codex login` and make sure your auth.json contains an API key, OR\n"
                "  2) Set the OPENAI_API_KEY environment variable.\n"
                "(ChatGPT-only login tokens cannot be used directly with the Responses API.)"
            )
        self.client = OpenAI(api_key=key)
        self.model = model
        self.history: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.history = []

    def _build_messages(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

    def add_user_message(self, text: str) -> None:
        self.history.append({"role": "user", "content": [{"type": "text", "text": text}]})

    def add_screenshot(self, png_bytes: bytes, note: str = "Here is the current screen.") -> None:
        b64 = base64.b64encode(png_bytes).decode("ascii")
        self.history.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": note},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        )

    def add_tool_result(self, tool_call_id: str, payload: dict[str, Any]) -> None:
        self.history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(payload),
            }
        )

    def step(self):
        """Send the current history and return the assistant message object.

        The returned object has `.content` (text or None) and `.tool_calls`
        (list of openai tool calls or None).
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(),
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        # Persist the assistant turn so subsequent tool results line up.
        self.history.append(msg.model_dump(exclude_none=True))
        return msg
