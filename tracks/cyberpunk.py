"""
cyberpunk — port of the Sonic Pi piece "CyberPunk song" (2024-03-08) by ikemura23,
rendered headlessly with engine/synth.py.

Upstream source: https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-03-08_CyberPunk.rb
Local copy: sources/sonic-pi/2024-03-08_CyberPunk.rb

The piece runs at `use_bpm 40` (one beat = 1.5 s), which is what gives it the slow,
swampy cyberpunk feel. Everything syncs to a 1-beat metronome, so all loops share one
16-beat grid (24 s):

    :amen          `loop_amen_full, beat_stretch: 8` on beats 0-8, then the same
                   sample with `start: 0, finish: 0.75 + 0.125` (first 87.5 %) on
                   beats 8-16
    :drum_splash   `drum_splash_soft` every 8 beats
    :synth1        `:tech_saws`, key :as2, sustain 4, note_slide 0.1, release 0 —
                   block A: key-4 -> key-2 -> key (1.5 / 0.5 / 2 beats), 4 beats rest;
                   block B: key+3 -> key+5 -> key-2 (1.5 / 0.5 / 2 beats), 4 beats rest
    :synth2        `:dsaw` arp through reverb (mix 0.7) + echo (mix 0.3):
                   [as4, as4-5, as4-2, as4-7], one note per 0.125 beat, so the figure
                   repeats every 0.5 beat; release 0.05, sustain 0.1, amp 0.2
    :synth3        starts with `stop` in the source -> never runs, SKIPPED here
    :base          `:fm` bass at amp 0.7, sustain 0.1, release 0.01, 16th-note cells
                   (0.125 beats): 12 x key-4, 4 x key-2, 16 x key, 12 x key+3,
                   4 x key+5, then 16 x key-2 (second pass: 8 x key-2 + 8 rests).
                   Two passes = 16 beats.

LENGTH = 48 s = two full passes of the 16-beat grid (Sonic Pi would loop forever).

Approximations (no SuperCollider here)
    * `beat_stretch: 8` -> resampling the ~2 s Amen break out to 12 s (rate 0.571),
      i.e. the slowed + pitched-down break: that is the sound of this piece;
    * `start:` / `finish:` -> slice bounds into the raw sample before resampling;
    * `:tech_saws` -> 5 polyBLEP saws detuned ±0.13 / ±0.06 semitones, through a
      low-pass around S.cut(115);
    * `:dsaw` -> detuned saw pair; `:fm` -> 2-operator sine FM (divisor 2);
    * `note_slide: 0.1` -> S.glide_freq() 0.1 s glides between the block's notes,
      concatenated into one continuous voice per block (release 0 = hard cut with a
      short anti-click fade).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import synth as S  # noqa: E402

NAME = "cyberpunk"
TITLE = "CyberPunk song (2024-03-08) — ikemura23, Sonic Pi"
SOURCE = "https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-03-08_CyberPunk.rb"

BPM = 40
LENGTH = 48.0


def glide_voice(targets, bpm: float, glide: float = 0.1, detune=(0.0, -0.13, 0.13, -0.06, 0.06),
                attack: float = 0.01, release: float = 0.04, cutoff: float = 115.0) -> np.ndarray:
    """One continuous voice that step-glides through (beats, midi_note) targets."""
    parts, prev = [], None
    for dur_beats, note in targets:
        n = max(int(S.beats(bpm, dur_beats) * S.SR), 16)
        f = S.hz(note)
        parts.append(np.full(n, f) if prev is None else S.glide_freq(prev, f, n, glide))
        prev = f
    curve = np.concatenate(parts)
    n = len(curve)
    sig = np.zeros(n)
    for d in detune:
        sig += S.saw(curve * 2.0 ** (d / 12.0), n)
    sig /= len(detune)
    sig *= S.env(n, attack, release)
    return S.lpf(sig, S.cut(cutoff), q=1.1)


def fm_bass(note, dur_s: float, release: float = 0.01, amp: float = 0.7,
            divisor: float = 2.0, depth: float = 1.0) -> np.ndarray:
    n = max(int(dur_s * S.SR), 16)
    f = S.hz(note)
    t = np.arange(n) / S.SR
    return amp * np.sin(2 * np.pi * f * t + depth * np.sin(2 * np.pi * f * divisor * t)) * \
        S.env(n, 0.003, release, decay=0.05)


def place(buf: np.ndarray, sig: np.ndarray, t_s: float) -> None:
    i = int(t_s * S.SR)
    m = min(len(sig), len(buf) - i)
    if m > 0:
        buf[i:i + m] += sig[:m]


def build(mix):
    beat = S.beats(BPM, 1)          # 1.5 s
    grid = S.beats(BPM, 16)         # 24 s
    key = S.midi("as2")

    passes = int(np.ceil(LENGTH / grid))
    for p in range(passes):
        base = p * grid
        if base >= LENGTH:
            break

        # ---- :amen — slowed Amen break (beat_stretch 8), then its first 87.5 %
        mix.beat_stretch_sample("loop_amen_full", base, 8, BPM, amp=1.15)
        mix.beat_stretch_sample("loop_amen_full", base + S.beats(BPM, 8), 8, BPM,
                                start=0.0, finish=0.875, amp=1.15)
        # ---- :drum_splash
        mix.sample("drum_splash_soft", base, amp=0.5, pan=-0.2)
        mix.sample("drum_splash_soft", base + S.beats(BPM, 8), amp=0.35, pan=0.25)

        # ---- :synth1 — gliding tech_saws blocks
        mix.add(glide_voice([(1.5, key - 4), (0.5, key - 2), (2.0, key)], BPM, cutoff=116),
                base, gain=0.34, pan=-0.12)
        mix.add(glide_voice([(1.5, key + 3), (0.5, key + 5), (2.0, key - 2)], BPM, cutoff=116),
                base + S.beats(BPM, 8), gain=0.34, pan=0.12)

        # ---- :synth2 — dsaw arp, 4 notes per 0.5 beat, reverb 0.7 + echo 0.3
        arp_len = int(grid * S.SR)
        arp = np.zeros(arp_len)
        figure = [S.midi("as4"), S.midi("as4") - 5, S.midi("as4") - 2, S.midi("as4") - 7]
        step = S.beats(BPM, 0.125)
        for k in range(int(grid / step)):
            note = figure[k % len(figure)]
            n = max(int(0.28 * S.SR), 16)
            voice = (0.7 * S.saw(S.hz(note), n) + 0.3 * S.saw(S.hz(note) * 1.004, n, phase0=0.5))
            voice *= S.env(n, 0.004, 0.05) * 0.22
            place(arp, voice, k * step)
        arp = S.reverb(arp, room=0.7, mix=0.7, damp=0.35)
        arp = S.echo(arp, S.beats(BPM, 0.25), feedback=0.42, mix=0.3)
        mix.add(arp, base, gain=0.9, pan=0.0)

        # ---- :base — fm bass, 16th-note cells, two passes
        cells = ([(12, key - 4), (4, key - 2), (16, key), (12, key + 3), (4, key + 5)] +
                 [(16, key - 2)] + [(12, key - 4), (4, key - 2), (16, key), (12, key + 3),
                                    (4, key + 5), (8, key - 2), (8, None)])
        t = base
        for count, note in cells:
            for _ in range(count):
                if note is not None:
                    mix.add(fm_bass(note, step, amp=0.7), t, gain=0.8, pan=0.0)
                t += step
