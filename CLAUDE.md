# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

始终使用中文回复和沟通，除非用户明确要求使用其他语言。

## Architecture

Single-file Python Pomodoro timer desktop app (`pomodoro.py`, ~550 lines) using **tkinter** for GUI.

### Key files

| File | Purpose |
|------|---------|
| `pomodoro.py` | Main app — tkinter UI, timer logic, persistence, settings dialog |
| `pomodoro_config.json` | Saved settings (work/break durations, sound toggle) |
| `pomodoro_stats.json` | Daily session counts keyed by `YYYY-MM-DD` |
| `番茄钟.bat` | Windows launcher — `start "" python "%~dp0pomodoro.py"` |

### Class structure

- **Theme** — Dark color palette (dark blue/purple base, red/green/blue mode accents)
- **PomodoroApp** — Main application class, owns the `tk.Tk` root window

### App states

Three states for the timer: `idle` (stopped), `running`, `paused`. Three modes (color-coded): `work` (red), `break` (green), `long_break` (blue). Every 4 pomodoros (configurable) triggers a long break.

### UI components

- Timer canvas (arc progress ring with time text + mode label)
- Control buttons (start/resume, pause, reset)
- Stats panel (today's count, total minutes)
- Settings dialog (Toplevel window, modifies config, resets timer)

### Persistence

- `load_config` / `save_config` — JSON config with defaults
- `load_stats` / `save_stats` — JSON stats dict (date → count)
- Both saved on close via `WM_DELETE_WINDOW` protocol

### Windows-specific dependencies

- `winsound.MessageBeep` — notification sound
- `ctypes.windll.user32.FlashWindow` — taskbar flash
- No external pip packages required (stdlib only)

## Commands

```powershell
# Run the app
python pomodoro.py

# Or via batch launcher
.\番茄钟.bat
```

No tests, no build step, no package manager needed.
