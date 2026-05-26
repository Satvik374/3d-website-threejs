"""Run loop: take a user message, call the LLM, execute tool calls,
loop until the model produces a plain-text reply (no more tool calls)."""
from __future__ import annotations

import json
from typing import Callable

from .actions import execute_tool_call
from .llm import LLMClient

MAX_STEPS = 12  # Safety cap on tool-call loops per user turn.


def run_turn(
    llm: LLMClient,
    user_text: str,
    log: Callable[[str], None],
    on_assistant_text: Callable[[str], None],
) -> None:
    llm.add_user_message(user_text)

    for _ in range(MAX_STEPS):
        msg = llm.step()

        # If the model produced visible text, surface it to the user.
        if msg.content:
            on_assistant_text(msg.content)

        tool_calls = msg.tool_calls or []
        if not tool_calls:
            return  # Done.

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            result = execute_tool_call(name, args, log)

            # If this was a screen capture, separately add the image to history
            # so the model can "see" it on the next step.
            if name == "screen_capture" and "_screenshot_png" in result:
                png = result.pop("_screenshot_png")
                # Tool result without the raw bytes (only metadata).
                llm.add_tool_result(tc.id, {"status": "ok", "size": result["size"]})
                llm.add_screenshot(png, note="Here is the current screen.")
            else:
                llm.add_tool_result(tc.id, result)

    log("[stopped: max tool-call steps reached]")
