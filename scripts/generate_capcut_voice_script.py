"""Generate CapCut-friendly SRT and CSV narration timecodes."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "tutorial"
TIMING_PATH = OUTPUT / "sonomika_tutorial_timing.json"

SECTIONS = [
    ("introduction", "Welcome to Sonomika for TouchDesigner, a real-time tool for creating and performing live visuals."),
    ("grid", "This is the performance grid. Each cell can contain a video or a TouchDesigner effect. The bottom row is the base visual layer. The rows above are effect layers."),
    ("rows", "Right-click a layer label to add or remove effect rows."),
    ("columns", "Columns let you prepare different visual combinations and switch between them while performing. Right-click a column heading to insert, copy, paste, or clear a column."),
    ("cell_base", "When you select a cell, its controls appear on the right. The Base tab contains the main controls for customizing the selected video or effect. You can also load multiple effects into one cell and chain them together."),
    ("cell_menu", "The cell menu lets you reload or relink the file, edit a tox, adjust performance options, copy and paste, or remove the cell."),
    ("settings_intro", "The Settings panel controls the wider performance setup."),
    ("canvas", "Canvas controls the output size."),
    ("sets", "Sets saves and loads complete performances."),
    ("osc", "O S C connects external software, while Grid O S C provides remote control of the performance grid."),
    ("pulse", "Pulse provides timing signals for animation."),
    ("audio", "Audio enables sound-reactive visuals."),
    ("midi", "MIDI connects hardware controllers."),
    ("fade", "Fade controls transitions between cells and columns."),
    ("perf", "Performance balances visual quality and playback speed."),
    ("about", "About contains version and project information."),
    ("closing", "An extensive manual is included and can easily be explored with the help of an AI assistant like ChatGPT. We look forward to seeing what you create."),
]

# Exact audio stream start_time in the current final MP4, measured by ffprobe.
VIDEO_AUDIO_OFFSET = 4.193


def srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def main() -> None:
    timings = json.loads(TIMING_PATH.read_text(encoding="utf-8"))
    text_by_name = dict(SECTIONS)
    rows = []
    srt_blocks = []

    for index, item in enumerate(timings, start=1):
        name = str(item["name"])
        start = float(item["start"]) + VIDEO_AUDIO_OFFSET
        end = float(item["end"]) + VIDEO_AUDIO_OFFSET
        text = text_by_name[name]
        rows.append(
            {
                "section": name,
                "start": srt_time(start).replace(",", "."),
                "end": srt_time(end).replace(",", "."),
                "text": text,
            }
        )
        srt_blocks.append(
            f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n"
        )

    (OUTPUT / "capcut_voice_script.srt").write_text(
        "\n".join(srt_blocks),
        encoding="utf-8-sig",
    )
    with (OUTPUT / "capcut_voice_script.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["section", "start", "end", "text"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(OUTPUT / "capcut_voice_script.srt")
    print(OUTPUT / "capcut_voice_script.csv")


if __name__ == "__main__":
    main()
