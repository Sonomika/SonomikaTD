"""Generate short Kokoro voice samples for the Sonomika tutorial."""

from pathlib import Path

import soundfile as sf
from kokoro import KPipeline


SAMPLE_TEXT = (
    "Welcome to Sonomika for TouchDesigner, a real-time VJ and live visual "
    "performance tool. Sonomika makes it easy to mix videos, generative "
    "visuals, audio-reactive content, and custom tox effects from one "
    "performance interface. There is an extensive manual included with "
    "Sonomika, which you can easily reference or explore with the help of an "
    "AI assistant like ChatGPT. We look forward to seeing what you create "
    "with Sonomika."
)

VOICES = {
    "af_heart": "warm_female",
}


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "output" / "tts_samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a")

    for voice, label in VOICES.items():
        chunks = []
        for _graphemes, _phonemes, audio in pipeline(
            SAMPLE_TEXT,
            voice=voice,
            speed=1.06,
            split_pattern=r"$^",
        ):
            chunks.append(audio)
        if not chunks:
            raise RuntimeError(f"No audio generated for {voice}")

        import torch

        combined = torch.cat(chunks).cpu().numpy()
        path = output_dir / f"sonomika_{label}_{voice}_tight.wav"
        sf.write(path, combined, 24000)
        print(path)


if __name__ == "__main__":
    main()
