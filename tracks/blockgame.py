"""
blockgame — port of the Sonic Pi "Algomancer" example `algomancer/blockgame.rb`
by DJ_Dave, rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/algomancer/blockgame.rb
Local copy: sources/sonic-pi/algomancer__blockgame.rb

A 130 BPM electro / game-loop piece built on a 16-beat grid (≈7.4 s), all loops synced
to a 1-beat metronome:

    :kick    `bd_tek` (amp 1.5, cutoff 130) on the 16th-note pattern
             "x--x--x---x--x--" (one bar = 4 beats)
    :clap    3 stacked `drum_snare_hard` (rates 2.5 / 2.2 / 2.0, starts 0 / 0.02 / 0.04,
             pans 0 / ±0.2, amp 0.75) every 2 beats, inside echo (mix 0.2) + reverb
             (mix 0.2, room 0.5)
    :hhc1    `drum_cymbal_closed` (rate 2.5, finish 0.5, pan ±0.3, amp 0.75) on the
             32nd-note pattern "x-x-x-x-x-x-x-x-xxx-x-x-x-x-x-x-" (one bar), through
             reverb (mix 0.2) and a pan slicer (mix 0.2)
    :hhc2    `drum_cymbal_closed` (rate 1.2, start 0.01, finish 0.5, amp 1.25) on the
             off-beat of every beat
    :crash   `drum_splash_soft` (rates 1.5 / 1.3, finish 0.25, amp 0.1) at beats
             14.5, 15.5 and 16.0 of each cycle, inside reverb (mix 0.7)
    :arp     `:beep` notes from scale g4 major_pentatonic shuffled, one per 0.75 beat
             (amp 0.6, release 0.25, attack 0.01, cutoff 130) with a pan sweep
             -0.7 .. 0.7 mirrored over 64 steps, inside echo (phase 1 beat) and
             reverb (mix 0.7)
    :synthbass  `:tech_saws` playing g3 for 6 beats, d3 for 2 and e3 for 8 (cutoff 60,
             amp 0.75, sustained) through a pan slicer (mix 0.4) + reverb (mix 0.75)

LENGTH = 44 s ≈ six passes of the 16-beat grid.

Approximations (no SuperCollider here)
    * `:beep` -> two-partial sine blip; `:tech_saws` -> 7 detuned saws through
      S.cut(60); `:panslicer` -> S.slicer amplitude gating applied to the group;
    * echo/reverb mixes are applied to each drum/arp group rather than per hit;
    * `.choose` / `.shuffle` are seeded (np.random.default_rng(7)) for reproducibility.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import synth as S  # noqa: E402

NAME = "blockgame"
TITLE = "Blockgame — DJ_Dave, Sonic Pi 'Algomancer' example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/algomancer/blockgame.rb"

BPM = 130
LENGTH = 44.0
SEED = 7

KICK_PAT = "x--x--x---x--x--"
HAT_PAT = "x-x-x-x-x-x-x-x-xxx-x-x-x-x-x-x-"


def place(buf, sig, t_s):
    i = int(t_s * S.SR)
    m = min(len(sig), len(buf) - i)
    if m > 0:
        buf[i:i + m] += sig[:m]


def beep(note, dur: float, amp: float = 0.6, cutoff: float = 130.0) -> np.ndarray:
    n = max(int(dur * S.SR), 16)
    f = S.hz(note)
    sig = S.sine(f, n) + 0.22 * S.sine(2.0 * f, n)
    sig *= S.env(n, 0.01, 0.25)
    return S.lpf(sig, S.cut(cutoff), q=0.9) * amp


def tech_saws(note, dur_s: float, cutoff: float = 60.0, amp: float = 0.75,
              detunes=(0.0, -0.14, 0.14, -0.07, 0.07, -0.21, 0.21)) -> np.ndarray:
    n = max(int(dur_s * S.SR), 32)
    f = S.hz(note)
    sig = np.zeros(n)
    for d in detunes:
        sig += S.saw(f * 2.0 ** (d / 12.0), n, phase0=abs(d) * 0.7)
    sig /= len(detunes)
    sig *= S.env(n, 0.02, 0.06)
    return S.lpf(sig, S.cut(cutoff), q=1.2) * amp


def build(mix):
    rng = np.random.default_rng(SEED)
    beat = S.beats(BPM, 1)
    grid = S.beats(BPM, 16)                      # 16-beat cycle ≈ 7.4 s
    cycles = int(np.ceil(LENGTH / grid))

    kick = np.zeros(int(LENGTH * S.SR))
    clap = np.zeros(int(LENGTH * S.SR))
    hats = np.zeros(int(LENGTH * S.SR))
    arp = np.zeros(int(LENGTH * S.SR))
    crash = np.zeros(int(LENGTH * S.SR))
    bass = np.zeros(int(LENGTH * S.SR))
    arp_notes = S.scale("g4", "major_pentatonic")
    order = list(rng.permutation(np.asarray(arp_notes, dtype=float)))

    for c in range(cycles):
        base = c * grid
        if base >= LENGTH:
            break

        # ---- :kick — 16th pattern on one bar
        step = S.beats(BPM, 0.25)
        for k, ch in enumerate(KICK_PAT):
            if ch == "x":
                t = base + k * step
                if t < LENGTH:
                    mix.sample("bd_tek", t, amp=1.4, lpf_hz=S.cut(130))

        # ---- :clap — stacked snares every 2 beats
        for t in (base, base + S.beats(BPM, 2), base + S.beats(BPM, 4),
                  base + S.beats(BPM, 6), base + S.beats(BPM, 8), base + S.beats(BPM, 10),
                  base + S.beats(BPM, 12), base + S.beats(BPM, 14)):
            if t >= LENGTH:
                break
            place(clap, S.resample(S.SAMPLES.get("drum_snare_hard"), 2.5) * 0.5, t)
            place(clap, S.resample(S.SAMPLES.get("drum_snare_hard"), 2.2)[int(0.02 * S.SR):] * 0.35,
                  t)
            place(clap, S.resample(S.SAMPLES.get("drum_snare_hard"), 2.0)[int(0.04 * S.SR):] * 0.3,
                  t)

        # ---- :hhc1 + :hhc2 — closed hats
        hstep = S.beats(BPM, 0.125)
        for k, ch in enumerate(HAT_PAT):
            if ch == "x":
                t = base + k * hstep
                if t < LENGTH:
                    pan = rng.choice([-0.3, 0.3])
                    place(hats, S.resample(S.SAMPLES.get("drum_cymbal_closed"), 2.5)[:int(0.05 * S.SR)] * 0.5,
                          t)
                    del pan
        for b in range(16):
            t = base + S.beats(BPM, b) + S.beats(BPM, 0.5)
            if t < LENGTH:
                seg = S.resample(S.SAMPLES.get("drum_cymbal_closed"), 1.2)
                seg = seg[int(0.01 * S.SR):int(0.5 * len(seg))]
                place(hats, seg * 0.85, t)

        # ---- :crash — splash at 14.5, 15.5, 16.0 beats of the cycle
        for b in (14.5, 15.5, 16.0):
            t = base + S.beats(BPM, b)
            if t < LENGTH:
                for rate in (1.5, 1.3):
                    seg = S.resample(S.SAMPLES.get("drum_splash_soft"), rate)
                    place(crash, seg[:int(0.25 * len(seg))] * 0.35, t)

        # ---- :arp — beep blips every 0.75 beat, pan sweep mirrored
        astep = S.beats(BPM, 0.75)
        for k in range(int(16 / 0.75)):
            t = base + k * astep
            if t >= LENGTH:
                break
            note = order[(c * 64 + k) % len(order)]
            pan = -0.7 + 1.4 * ((k % 64) / 63.0) if (k // 64) % 2 == 0 else \
                0.7 - 1.4 * ((k % 64) / 63.0)
            mix.add(beep(note, 0.3), t, gain=0.34, pan=float(np.clip(pan, -0.7, 0.7)))

        # ---- :synthbass — g3 x6 beats, d3 x2, e3 x8 through slicer + reverb
        place(bass, tech_saws("g3", S.beats(BPM, 6)), base)
        place(bass, tech_saws("d3", S.beats(BPM, 2)), base + S.beats(BPM, 6))
        place(bass, tech_saws("e3", S.beats(BPM, 8)), base + S.beats(BPM, 8))

    # ---- group FX, mirroring the with_fx wrappers in the source
    clap_bus = S.reverb(S.echo(clap, beat, feedback=0.45, mix=0.2), room=0.5, mix=0.2)
    hats_bus = S.slicer(S.reverb(hats, room=0.5, mix=0.2), phase_s=beat, wave=1, amp=0.2)
    crash_bus = S.reverb(crash, room=0.7, mix=0.7)
    bass_bus = S.reverb(S.slicer(bass, phase_s=beat, wave=1, amp=0.4), room=0.75, mix=0.75)
    arp_bus = S.reverb(S.echo(arp, beat, feedback=0.5, mix=0.5), room=0.7, mix=0.7)

    for bus, gain in ((clap_bus, 1.15), (hats_bus, 1.6), (crash_bus, 1.2),
                      (bass_bus, 0.55), (arp_bus, 1.4)):
        mix.add(bus[: int(LENGTH * S.SR)], 0.0, gain=gain)
