#!/usr/bin/env python3
"""Numeric sanity check of rendered tracks (I can't listen — so measure)."""
import sys, wave
import numpy as np

def load(path):
    with wave.open(path) as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2").reshape(-1, ch).astype(float) / 32768.0
    return x, sr

for path in sys.argv[1:]:
    x, sr = load(path)
    mono = x.mean(axis=1)
    dur = len(mono) / sr
    print(f"\n### {path}  ({dur:.1f}s, {sr} Hz)")
    print("  sec |   rms  | centroid | low(<200) | mid | high(>4k) | peak")
    for s in range(0, int(dur), 4):
        seg = mono[s * sr:(s + 4) * sr]
        if len(seg) < sr:
            break
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1 / sr)
        tot = max(spec.sum(), 1e-9)
        lo = spec[fr < 200].sum() / tot
        hi = spec[fr > 4000].sum() / tot
        cen = (spec * fr).sum() / tot
        print(f"  {s:3d} | {np.sqrt((seg**2).mean()):.4f} | {cen:7.0f} | {lo:8.3f} | {1-lo-hi:5.3f} | {hi:8.3f} | {np.abs(seg).max():.3f}")
    # transient count: energy jumps in 20 ms frames
    fr_len = int(0.02 * sr)
    env = np.array([np.sqrt((mono[i:i + fr_len] ** 2).mean()) for i in range(0, len(mono) - fr_len, fr_len)])
    if env.max() > 0:
        env /= env.max()
        onsets = int(np.sum((env[1:] > 0.25) & (env[:-1] <= 0.25)))
    else:
        onsets = 0
    print(f"  onsets(>25% jump): {onsets} | silent frames: {int(np.sum(env < 0.01))}/{len(env)}")
