"""Record the approved Sonomika tutorial with synchronized Kokoro narration.

The script captures the full 4K desktop while Sonomika is foregrounded, scales
the result to 1080p, and muxes the pre-rendered narration. It only selects
existing cells/columns and settings pages. Context menus are opened and closed
without choosing destructive actions.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


USER32 = ctypes.windll.user32
USER32.SetProcessDPIAware()
SW_RESTORE = 9
LEFT_DOWN = 0x0002
LEFT_UP = 0x0004
RIGHT_DOWN = 0x0008
RIGHT_UP = 0x0010

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "tutorial"
VOICE = OUTPUT / "sonomika_tutorial_voice.wav"
TIMING = OUTPUT / "sonomika_tutorial_timing.json"
RAW_VIDEO = OUTPUT / "sonomika_tutorial_silent.mp4"
FINAL_VIDEO = OUTPUT / "sonomika_tutorial_1080p.mp4"
FFMPEG = (
    Path(os.environ["LOCALAPPDATA"])
    / "Microsoft/WinGet/Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.0-full_build/bin/ffmpeg.exe"
)


def find_perform_window() -> int:
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        length = USER32.GetWindowTextLengthW(hwnd)
        if length:
            title = ctypes.create_unicode_buffer(length + 1)
            USER32.GetWindowTextW(hwnd, title, length + 1)
            if title.value.startswith("/perform"):
                matches.append(hwnd)
        return True

    USER32.EnumWindows(callback, 0)
    if not matches:
        raise RuntimeError("No open Sonomika /perform window was found.")
    return matches[0]


def click(x: int, y: int, right: bool = False) -> None:
    USER32.SetCursorPos(x, y)
    time.sleep(0.12)
    if right:
        USER32.mouse_event(RIGHT_DOWN, 0, 0, 0, 0)
        time.sleep(0.08)
        USER32.mouse_event(RIGHT_UP, 0, 0, 0, 0)
    else:
        USER32.mouse_event(LEFT_DOWN, 0, 0, 0, 0)
        time.sleep(0.08)
        USER32.mouse_event(LEFT_UP, 0, 0, 0, 0)


def move(x: int, y: int, duration: float = 0.55) -> None:
    start = wintypes.POINT()
    USER32.GetCursorPos(ctypes.byref(start))
    frames = max(1, round(duration * 60))
    for frame in range(1, frames + 1):
        t = frame / frames
        eased = t * t * (3 - 2 * t)
        USER32.SetCursorPos(
            round(start.x + (x - start.x) * eased),
            round(start.y + (y - start.y) * eased),
        )
        time.sleep(duration / frames)


def at(start: float, seconds: float, action, *args) -> None:
    delay = start + seconds - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    action(*args)


def record_walkthrough() -> None:
    if not FFMPEG.exists():
        raise RuntimeError(f"FFmpeg not found at {FFMPEG}")
    if not VOICE.exists() or not TIMING.exists():
        raise RuntimeError("Generate the narration before recording.")

    timing = {item["name"]: item for item in json.loads(TIMING.read_text())}
    narration_duration = max(item["end"] for item in timing.values())
    capture_duration = narration_duration + 6.0

    OUTPUT.mkdir(parents=True, exist_ok=True)
    capture_command = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "lavfi",
        "-i",
        "ddagrab=framerate=30:draw_mouse=1",
        "-t",
        f"{capture_duration:.3f}",
        "-vf",
        "hwdownload,format=bgra,scale=1920:1080:flags=lanczos",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-cq",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(RAW_VIDEO),
    ]
    hwnd = find_perform_window()
    USER32.ShowWindow(hwnd, SW_RESTORE)
    USER32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

    # Close any popup left over from calibration and reset to Column 1 before
    # the recorder starts.
    click(403, 118)
    time.sleep(0.5)

    capture_start = time.monotonic()
    recorder = subprocess.Popen(
        capture_command,
        cwd=ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(0.8)

    # Always start the Sonomika transport before narration.
    click(388, 46)
    move(178, 47)
    narration_start = time.monotonic() + 1.4
    narration_delay = narration_start - capture_start

    # Introduction.
    at(narration_start, 0.0, move, 140, 48)
    at(narration_start, 3.8, move, 388, 46)

    # Grid and layers.
    at(narration_start, timing["grid"]["start"], move, 620, 500)
    at(narration_start, 11.0, move, 403, 720)
    at(narration_start, 15.0, move, 403, 395)

    # Row menu overview. Open it, leave it visible, then close safely.
    at(narration_start, timing["rows"]["start"], click, 75, 395, True)
    at(narration_start, timing["rows"]["end"] - 0.5, click, 403, 395)

    # Switch populated columns while playback continues.
    at(narration_start, timing["columns"]["start"], click, 624, 118)
    at(narration_start, 25.8, click, 843, 118)
    at(narration_start, 29.2, click, 843, 118, True)
    at(narration_start, timing["columns"]["end"] - 0.4, click, 624, 118)

    # Select a TOX cell and show its Base controls.
    at(narration_start, timing["cell_base"]["start"], click, 843, 395)
    at(narration_start, timing["cell_base"]["start"] + 2.8, move, 1810, 1042)
    at(narration_start, timing["cell_base"]["start"] + 6.0, move, 2250, 1280)

    # Cell right-click menu overview.
    at(narration_start, timing["cell_menu"]["start"], click, 843, 395, True)
    menu_start = timing["cell_menu"]["start"]
    at(narration_start, menu_start + 0.6, move, 920, 414)  # Reload
    at(narration_start, menu_start + 1.4, move, 920, 458)  # Relink
    at(narration_start, menu_start + 2.2, move, 920, 498)  # Edit TOX
    at(narration_start, menu_start + 3.1, move, 920, 578)  # Render Scale
    at(narration_start, menu_start + 4.5, move, 920, 740)  # Freeze
    at(narration_start, menu_start + 5.3, move, 920, 778)  # Copy
    at(narration_start, menu_start + 6.2, move, 920, 858)  # Paste
    at(narration_start, menu_start + 7.1, move, 920, 900)  # Delete
    at(narration_start, timing["cell_menu"]["end"] - 0.4, click, 843, 395)

    # Settings tabs: page selection only, no values are changed.
    settings_y = 1162
    settings_tabs = [
        (timing["settings_intro"]["start"] - 0.4, 2780),  # Open Settings on Canvas
        (timing["canvas"]["start"] - 0.4, 2780),
        (timing["sets"]["start"] - 0.4, 2890),
        (timing["osc"]["start"] - 0.4, 2960),
        (timing["osc"]["start"] + 3.5, 3050),  # GrdOSC after OSC is introduced
        (timing["pulse"]["start"] - 0.4, 3148),
        (timing["audio"]["start"] - 0.4, 3233),
        (timing["midi"]["start"] - 0.4, 3305),
        (timing["fade"]["start"] - 0.4, 3374),
        (timing["perf"]["start"] - 0.4, 3441),
        (timing["about"]["start"] - 0.4, 3514),
    ]
    for seconds, x in settings_tabs:
        at(narration_start, seconds, click, x, settings_y)

    # Finish on the live preview, then the Sonomika logo.
    at(narration_start, timing["closing"]["start"], move, 900, 1500)
    at(narration_start, 98.0, move, 142, 48)
    at(narration_start, narration_duration + 1.5, move, 1900, 2080)

    recorder.wait(timeout=20)

    mux_command = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(RAW_VIDEO),
        "-itsoffset",
        f"{narration_delay:.3f}",
        "-i",
        str(VOICE),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(FINAL_VIDEO),
    ]
    subprocess.run(
        mux_command,
        cwd=ROOT,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    print(FINAL_VIDEO)


if __name__ == "__main__":
    try:
        record_walkthrough()
    except Exception as exc:
        print(f"Tutorial recording failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
