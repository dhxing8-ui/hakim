from __future__ import annotations

import asyncio
import subprocess
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
    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH, volume=VOLUME)
    submaker = edge_tts.SubMaker()
    with RAW_MP3.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
    WORD_SRT.write_text(submaker.get_srt(), encoding="utf-8")

def master_audio() -> None:
    audio_filter = (
        "highpass=f=70,lowpass=f=12000,"
        "equalizer=f=180:t=q:w=0.9:g=1.3,"
        "equalizer=f=3200:t=q:w=1.1:g=0.8,"
        "acompressor=threshold=-18dB:ratio=2:attack=18:release=180:makeup=1.5,"
        "loudnorm=I=-16:TP=-1.5:LRA=9"
    )
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(RAW_MP3),
        "-af", audio_filter, "-codec:a", "libmp3lame", "-b:a", "192k", str(FINAL_MP3)
    ], check=True)

def duration_seconds(path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())

async def main() -> None:
    await synthesize()
    if RAW_MP3.stat().st_size < 100_000:
        raise RuntimeError("Generated narration is unexpectedly small")
    master_audio()
    duration = duration_seconds(FINAL_MP3)
    META.write_text(
        f"voice={VOICE}\nrate={RATE}\npitch={PITCH}\nvolume={VOLUME}\nduration_seconds={duration:.3f}\n",
        encoding="utf-8"
    )
    print(META.read_text(encoding="utf-8"))

if __name__ == "__main__":
    asyncio.run(main())
