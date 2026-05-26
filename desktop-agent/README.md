# Desktop Agent

A small floating AI chatbot for Windows. Press **Ctrl + Shift + \*** anywhere to
toggle a translucent chat window. Tell it to look at your screen and it will,
tell it to click somewhere and it will (with a 1-second preview that **Esc**
cancels).

- **Model**: GPT-4o via the OpenAI Chat Completions API (vision + tool calls).
- **Auth**: reuses the API key stored by `codex login` if present, otherwise
  falls back to the `OPENAI_API_KEY` environment variable.
- **Hotkey**: `Ctrl + Shift + 8` (which is `Ctrl + Shift + *` on US layouts).
  Numpad `*` works too.
- **Vision**: only when you actually ask the agent to look at the screen.
- **Clicks**: auto-execute, with a 1-second cancel window (hold **Esc**).

## Setup

You need Python 3.10+ on Windows.

```bat
cd desktop-agent
run.bat
```

The first run creates a `.venv`, installs deps, and starts the agent. After
that `run.bat` just launches it.

### Credentials

The agent looks for an OpenAI API key in this order:

1. `OPENAI_API_KEY` environment variable.
2. `~/.codex/auth.json` -- the file that `codex login` writes. It checks the
   common field names (`OPENAI_API_KEY`, `openai_api_key`, `api_key`,
   `apiKey`).

> **Note on "Codex login":** when you log in to the Codex CLI with a ChatGPT
> account, the credentials stored are *bearer tokens* the CLI uses against
> OpenAI's backend -- they are **not a usable API key** for the public Chat
> Completions / Responses APIs. So if `codex login` only stored ChatGPT
> tokens and no API key, the agent won't be able to call the model directly.
>
> The simplest fix is to grab an API key from
> <https://platform.openai.com/api-keys> and either:
> - set it as `OPENAI_API_KEY` in your environment, **or**
> - paste it into `~/.codex/auth.json` under an `OPENAI_API_KEY` field.

Vision and clicking both need this -- `codex exec` text-only fallback is not
implemented in this build.

### Choosing the model

There's a model dropdown in the top-right of the chat window. It's
**editable** -- pick a preset or type any model id you have access to (e.g.
a fine-tuned model, `gpt-5` once it's on your account, etc). Press Enter or
Tab away to apply. The change takes effect on your next message.

Presets shown:

- `gpt-4o`            (default - fast, vision-capable)
- `gpt-4o-mini`       (cheap, vision-capable)
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4-turbo`
- `o4-mini`           (reasoning, vision-capable)

> Only **vision-capable** models can do the "look at my screen" feature.
> Non-vision models will still chat normally but will fail when the agent
> tries to send a screenshot.

You can also set the **default** model without touching the UI by exporting
an environment variable before launching:

```bat
set AGENT_MODEL=gpt-4o-mini
run.bat
```

## Using it

1. Start with `run.bat`.
2. The window starts hidden. Press **Ctrl + Shift + \*** to show it.
3. Type a message and hit **Enter** (Shift+Enter for a newline).
4. Examples:
   - "What is the capital of France?" -- plain chat, no screen access.
   - "Look at my screen and tell me what app is focused." -- captures the
     screen, sends it to the model.
   - "Open the Recycle Bin on my desktop." -- model takes a screenshot, finds
     the icon, double-clicks it.
5. While an action is queued you'll see a line like
   `-> about to left click at (812, 430)  [hold ESC to cancel]`. Hold **Esc**
   for ~1s to cancel; otherwise the click runs.
6. **Esc** with the input box empty also hides the window. The agent keeps
   running in the background; the hotkey brings it back.
7. Click **New chat** in the footer to wipe history.

## Files

```
desktop-agent/
  agent/
    __init__.py
    main.py        entry point
    overlay.py     Tk chat window
    hotkey.py      global Ctrl+Shift+* hotkey (Win32)
    llm.py         OpenAI client + auth lookup
    tools.py       tool/function schemas the model can call
    actions.py     executes tool calls + ESC-cancellable preview
    agent.py       per-turn run loop (LLM <-> tools)
    screen.py      screen capture + pyautogui input
  requirements.txt
  run.bat
  README.md
```

## Safety notes

- Every click/type/hotkey/key-press has a 1-second preview. Holding **Esc**
  during that window cancels it.
- Screen captures only happen when the model calls the `screen_capture` tool,
  which it should only do when you ask it to look at the screen.
- All captures and conversation history live in process memory only -- nothing
  is written to disk.
- The model is told to be brief and to only request screenshots when actually
  asked. You can adjust this in `llm.py` (`SYSTEM_PROMPT`).

## Known limitations

- Single-monitor: it captures the primary monitor only. Multi-monitor support
  is a small change in `screen.py`.
- pyautogui input goes through the Windows input queue, which UAC-elevated
  windows refuse -- running the agent as admin lets it click those.
- The hotkey conflicts if some other app has registered Ctrl+Shift+8 globally
  (rare). If it doesn't fire, check the console for
  `failed to register Ctrl+Shift+8`.
- DPI scaling > 100% can shift coordinates by a few pixels. If clicks miss,
  set DPI awareness on the Python interpreter or scale coordinates in
  `actions.py`.
