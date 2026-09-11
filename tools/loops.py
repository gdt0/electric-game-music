#!/usr/bin/env python3
"""
loops.py — render every track as a **seamless, exactly-barred loop** for game use.

How the seam works
------------------
Each track is rendered for `loop_seconds + TAIL` seconds. Everything that happens after
the loop's end (reverb tails, echo spill, drum decay) is then added back onto the start of
the loop — so the last sample flows into the first sample exactly the way the music
continues, and playing the file on repeat is gapless in content (only the mp3 encoder's
own padding differs, which is why a .wav is written too).

Per track the loop length comes from the module constant `LOOP_BEATS` (its natural pattern
cycle in beats); tracks without one use the table below.

Outputs
-------
    loops/<name>.mp3        loop audio (committed)
    loops/<name>.wav        same audio, PCM (regenerated locally, gitignored)
    loops/manifest.json     name, title, bpm, loop_beats, loop_seconds, sample count,
                            seam continuity metric, file paths, upstream source

usage:
    python3 tools/loops.py                  # every track that exists
    python3 tools/loops.py jungle acid      # selected tracks
    python3 tools/loops.py --check          # verify seam quality of existing loops
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import synth as S  # noqa: E402
from tools.arduino_songs import parse_ino  # noqa: E402
from tracks import _chiptune as C  # noqa: E402

LOOPS_DIR = os.path.join(ROOT, "loops")
TAIL = 3.0                      # seconds of FX tail folded back onto the loop start

# natural pattern cycle (in beats) for tracks that predate the LOOP_BEATS constant
LOOP_BEATS_FALLBACK = {
    "rerezzed": 8, "tron_bike": 8, "blockgame": 16, "time_machine": 16,
    "acid": 18, "dark_neon": 16, "cyberpunk": 16, "cyberpunk_2": 16,
}
# song-form tracks: the loop is the whole tune, whose length comes from the parsed .ino
CHIPTUNE = {"vampire_killer": "vampirekiller", "bloody_tears": "bloodytears",
            "doom_e1m1": "doom"}


def track_modules():
    mods = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tracks", "*.py"))):
        base = os.path.basename(path)[:-3]
        if base.startswith("_"):
            continue
        try:
            mods.append(importlib.import_module(f"tracks.{base}"))
        except Exception as e:                                    # noqa: BLE001
            print(f"  ! cannot import tracks.{base}: {e}")
    return mods


def loop_beats_of(mod) -> float | None:
    if hasattr(mod, "LOOP_BEATS"):
        return float(mod.LOOP_BEATS)
    if mod.NAME in LOOP_BEATS_FALLBACK:
        return float(LOOP_BEATS_FALLBACK[mod.NAME])
    if mod.NAME in CHIPTUNE:
        _, events = parse_ino(C.ino_path(CHIPTUNE[mod.NAME]))
        return float(sum(b for _, b in events))
    return None


def render_loop(mod) -> dict | None:
    beats = loop_beats_of(mod)
    if not beats:
        print(f"  - {mod.NAME}: no loop length known — skipped")
        return None

    loop_s = beats * 60.0 / mod.BPM
    total = loop_s + TAIL
    original_length = mod.LENGTH
    mod.LENGTH = total                                  # tracks read LENGTH at build time
    try:
        mix = S.Mix(total)
        mod.build(mix)
        st = mix.out()
    finally:
        mod.LENGTH = original_length

    n = int(round(loop_s * S.SR))
    core = st[:, :n].copy()
    tail = st[:, n:]
    if len(tail):
        m = min(tail.shape[1], n)
        core[:, :m] += tail[:, :m]                      # fold the FX tail onto the start

    peak = float(np.abs(core).max()) or 1.0
    core = core / peak * 0.92

    os.makedirs(LOOPS_DIR, exist_ok=True)
    wav = os.path.join(LOOPS_DIR, f"{mod.NAME}.wav")
    mp3 = os.path.join(LOOPS_DIR, f"{mod.NAME}.mp3")
    S.write_wav(wav, core.astype(np.float32))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-codec:a", "libmp3lame",
                    "-b:a", "192k", mp3], check=True)

    seam = max(abs(float(core[0, 0] - core[0, -1])), abs(float(core[1, 0] - core[1, -1])))
    diffs = np.abs(np.diff(core, axis=1))
    typical = float(np.percentile(diffs, 99.5)) or 1e-9
    return {
        "name": mod.NAME, "title": mod.TITLE, "source": mod.SOURCE, "bpm": mod.BPM,
        "loop_beats": beats, "loop_seconds": round(loop_s, 4),
        "samples": n, "seam_jump_ratio": round(seam / typical, 3),
        "rms": round(float(np.sqrt((core ** 2).mean())), 4),
        "file_mp3": f"loops/{mod.NAME}.mp3", "file_wav": f"loops/{mod.NAME}.wav",
    }


def check_existing() -> None:
    manifest = json.load(open(os.path.join(LOOPS_DIR, "manifest.json")))
    print(f"{'loop':18s} {'beats':>6s} {'seconds':>9s} {'samples':>9s} {'seam':>7s} {'rms':>7s}")
    for e in manifest["loops"]:
        print(f"{e['name']:18s} {e['loop_beats']:>6.2f} {e['loop_seconds']:>9.2f} "
              f"{e['samples']:>9d} {e['seam_jump_ratio']:>7.2f} {e['rms']:>7.4f}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--check" in sys.argv:
        check_existing()
        return

    entries = []
    for mod in track_modules():
        if args and mod.NAME not in args:
            continue
        info = render_loop(mod)
        if info:
            print(f"  ✓ {info['name']:18s} {info['loop_beats']:>6.2f} beats "
                  f"{info['loop_seconds']:>7.2f} s  seam {info['seam_jump_ratio']:>5.2f}x "
                  f"rms {info['rms']:.3f}")
            entries.append(info)

    manifest_path = os.path.join(LOOPS_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        old = {e["name"]: e for e in json.load(open(manifest_path))["loops"]}
    else:
        old = {}
    for e in entries:
        old[e["name"]] = e
    out = {"generated_by": "tools/loops.py", "tail_folded_seconds": TAIL,
           "loops": [old[k] for k in sorted(old)]}
    os.makedirs(LOOPS_DIR, exist_ok=True)
    with open(manifest_path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nmanifest: {manifest_path} ({len(out['loops'])} loops)")


if __name__ == "__main__":
    main()
