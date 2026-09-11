#!/usr/bin/env python3
"""
render.py — render every track in tracks/ to WAV + MP3.

usage:
    python3 render.py                 # render all tracks
    python3 render.py rerezzed acid   # render selected tracks by name
    python3 render.py --list          # show track table
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine import synth as S  # noqa: E402

TRACKS_DIR = os.path.join(ROOT, "tracks")
AUDIO_DIR = os.path.join(ROOT, "audio")


def discover():
    mods = []
    for f in sorted(os.listdir(TRACKS_DIR)):
        if f.endswith(".py") and not f.startswith("_"):
            mods.append(importlib.import_module(f"tracks.{f[:-3]}"))
    return mods


def render(mod) -> dict:
    mix = S.Mix(mod.LENGTH)
    mod.build(mix)
    st = mix.out(getattr(mod, "PEAK", 0.92))
    wav = os.path.join(AUDIO_DIR, f"{mod.NAME}.wav")
    mp3 = os.path.join(AUDIO_DIR, f"{mod.NAME}.mp3")
    S.write_wav(wav, st)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-codec:a", "libmp3lame",
                    "-b:a", "192k", mp3], check=True)
    mono = st.mean(axis=0)
    spec = np.abs(np.fft.rfft(mono[: S.SR * 8] * np.hanning(min(len(mono), S.SR * 8))))
    freqs = np.fft.rfftfreq(min(len(mono), S.SR * 8), 1 / S.SR)
    centroid = float((spec * freqs).sum() / max(spec.sum(), 1e-9))
    return {
        "name": mod.NAME, "title": mod.TITLE, "seconds": len(st[0]) / S.SR,
        "peak": float(np.abs(st).max()), "rms": float(np.sqrt((st ** 2).mean())),
        "centroid_hz": centroid, "mp3_kb": os.path.getsize(mp3) // 1024,
    }


def main():
    args = [a for a in sys.argv[1:]]
    mods = discover()
    if "--list" in args:
        for m in mods:
            print(f"{m.NAME:16s} {getattr(m, 'BPM', '?'):>5} bpm  {getattr(m, 'LENGTH', '?'):>5}s  {m.TITLE}")
        return
    want = [a for a in args if not a.startswith("-")]
    if want:
        mods = [m for m in mods if m.NAME in want]
    if not mods:
        print("no tracks selected")
        return
    os.makedirs(AUDIO_DIR, exist_ok=True)
    for m in mods:
        info = render(m)
        print(f"[{info['name']}] {info['title']}\n"
              f"    {info['seconds']:.1f}s | peak {info['peak']:.3f} | rms {info['rms']:.4f} "
              f"| centroid {info['centroid_hz']:.0f} Hz | mp3 {info['mp3_kb']} KB")


if __name__ == "__main__":
    main()
