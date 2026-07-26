"""Render the approved tutorial narration and section timing manifest."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline


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


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "output" / "tutorial"
    sections_dir = output_dir / "voice_sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    sample_rate = 24000
    section_gap = np.zeros(round(sample_rate * 0.45), dtype=np.float32)
    combined: list[np.ndarray] = []
    manifest: list[dict[str, float | str]] = []
    cursor = 0

    for name, text in SECTIONS:
        chunks = [
            audio
            for _graphemes, _phonemes, audio in pipeline(
                text,
                voice="af_heart",
                speed=1.0,
                split_pattern=r"$^",
            )
        ]
        audio = torch.cat(chunks).cpu().numpy()
        sf.write(sections_dir / f"{name}.wav", audio, sample_rate)
        start = cursor / sample_rate
        end = (cursor + len(audio)) / sample_rate
        manifest.append({"name": name, "start": round(start, 3), "end": round(end, 3)})
        combined.extend((audio, section_gap))
        cursor += len(audio) + len(section_gap)

    full_audio = np.concatenate(combined[:-1])
    sf.write(output_dir / "sonomika_tutorial_voice.wav", full_audio, sample_rate)
    (output_dir / "sonomika_tutorial_timing.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Duration: {len(full_audio) / sample_rate:.2f} seconds")


if __name__ == "__main__":
    main()
