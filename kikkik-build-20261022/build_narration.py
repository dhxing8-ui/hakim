from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)
TEXT_FILE = ROOT / "narration.txt"
RAW_MP3 = OUT / "kikkik_voice_raw.mp3"
FINAL_MP3 = OUT / "kikkik_voice_natural.mp3"
WORD_SRT = OUT / "kikkik_word_timing.srt"
META = OUT / "voice_info.txt"
VOICE = "ko-KR-SunHiNeural"
RATE = "-4%"
PITCH = "-1Hz"
VOLUME = "+0%"

async def synthesize() -> None:
    text = TEXT_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("Narration text is empty")

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME,
    )
    submaker = edge_tts.SubMaker()

    with RAW_MP3.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    WORD_SRT.write_text(submaker.get_srt(), encoding="utf-8")

async def main() -> None:
    await synthesize()
    if RAW_MP3.stat().st_size < 100_000:
        raise RuntimeError("Generated narration is unexpectedly small")

    # Keep the neural TTS stream unchanged here. Final EQ, loudness mastering,
    # video mixing, and exact subtitle retiming are applied after download.
    shutil.copyfile(RAW_MP3, FINAL_MP3)

    META.write_text(
        "\n".join([
            f"voice={VOICE}",
            f"rate={RATE}",
            f"pitch={PITCH}",
            f"volume={VOLUME}",
            f"audio_bytes={FINAL_MP3.stat().st_size}",
            "status=natural Korean neural narration generated successfully",
        ]) + "\n",
        encoding="utf-8",
    )
    print(META.read_text(encoding="utf-8"))

if __name__ == "__main__":
    asyncio.run(main())
