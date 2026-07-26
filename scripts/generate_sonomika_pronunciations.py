"""Generate short Kokoro pronunciation tests for the Sonomika brand name."""

from pathlib import Path

import soundfile as sf
import torch
from kokoro import KPipeline


VARIANTS = {
    "sonomeka": "Welcome to Sonomeka for TouchDesigner.",
}


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "output" / "tts_samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    for label, text in VARIANTS.items():
        chunks = [
            audio
            for _graphemes, _phonemes, audio in pipeline(
                text,
                voice="af_heart",
                speed=1.04,
                split_pattern=r"$^",
            )
        ]
        path = output_dir / f"sonomika_pronunciation_{label}.wav"
        sf.write(path, torch.cat(chunks).cpu().numpy(), 24000)
        print(path)


if __name__ == "__main__":
    main()
