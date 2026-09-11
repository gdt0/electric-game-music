"""
tron_bike.py — faithful port of the Sonic Pi example ``tron_bike`` by Sam Aaron
(sources/sonic-pi/magician__tron_bike.rb, upstream
etc/examples/magician/tron_bike.rb):

    use_random_seed 10
    notes = (ring :b1, :b2, :e1, :e2, :b3, :e3)

    live_loop :tron do
      with_synth :dsaw do
        with_fx(:slicer, phase: [0.25, 0.125].choose) do
          with_fx(:reverb, room: 0.5, mix: 0.3) do
            n1 = (chord notes.choose, :minor).choose
            n2 = (chord notes.choose, :minor).choose
            p = play n1, amp: 2, release: 8, note_slide: 4,
                      cutoff: 30, cutoff_slide: 4, detune: rrand(0, 0.2)
            control p, note: n2, cutoff: rrand(80, 120)
          end
        end
      end
      sleep 8
    end

Determinism
-----------
Sonic Pi's ``use_random_seed 10`` becomes ``np.random.default_rng(10)`` so the
render is reproducible.  Per 8-beat loop iteration the rng draws, in source
order: the slicer phase (``[0.25, 0.125].choose``), the two chord roots
(``notes.choose`` twice), the dsaw detune (``rrand(0, 0.2)``) and the control
target cutoff (``rrand(80, 120)``).

Approximations
--------------
* tempo       — Sonic Pi default 60 BPM, so ``sleep 8`` == 8.0 s and the 8-beat
                note is 8 s of sound.
* ``:dsaw``   — two polyBLEP saws per voice detuned by ±detune/2 semitones
                (``f * 2**(±detune/24)``); one saw sits left, one right in the
                stereo field like the synth's detuned twin pair.
* voices      — the source plays one random chord tone per pick; here each
                block stacks the whole minor triad (3 tones × 2 detuned saws)
                and every tone portamento-glides from its chord-1 degree to the
                matching chord-2 degree, so ``control p, note: n2`` moves the
                whole harmony with the same voice (no re-trigger).
* note_slide  — ``S.glide_freq(f1, f2, n, 4)``: pitch slides over the first
                4 s of the block, then holds.
* cutoff_slide — ``cutoff:`` is a MIDI NOTE NUMBER: the low-pass glides
                ``S.cut(30)`` (≈46 Hz, very dark) up to ``S.cut(rrand 80..120)``
                in MIDI space over 4 s, applied with ``S.lpf_curve(q≈2)``.
                Filtering happens on the synth voice, before the FX chain,
                exactly like Sonic Pi's synth-level cutoff.
* release 8   — Sonic Pi's default ``sustain:`` is 0, so each note is a swell:
                10 ms attack, then an exponential 8 s fade (``S.env``).
* FX order    — slicer wraps reverb in the source, so audio runs
                voice -> reverb(room 0.5, mix 0.3) -> slicer(phase, wave 1).
                The reverb is re-rended per iteration like Sonic Pi's per-loop
                FX instances; the two detuned chains use decorrelated reverb.
* length      — the live_loop runs forever; we render four full 8-beat cycles
                plus a 4 s outro swell of the fifth chord so the file ends on a
                natural fade at LENGTH instead of a truncation click.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from engine import synth as S  # noqa: E402

NAME = "tron_bike"
TITLE = "Tron Bike — Sam Aaron's Sonic Pi light-cycle drone"
BPM = 60.0                                    # Sonic Pi default bpm
LENGTH = 36.0
PEAK = 0.9

NOTES = ("b1", "b2", "e1", "e2", "b3", "e3")  # (ring :b1, :b2, :e1, :e2, :b3, :e3)
BLOCK_BEATS = 8                               # `sleep 8`
BLOCK_S = S.beats(BPM, BLOCK_BEATS)           # 8.0 s
SLIDE_S = 4.0                                 # note_slide: 4 / cutoff_slide: 4
CUTOFF_CLOSED = 30.0                          # cutoff: 30  (MIDI note number!)
DETUNE_RANGE = (0.0, 0.2)                     # detune: rrand(0, 0.2)
CUTOFF_OPEN_RANGE = (80.0, 120.0)             # control cutoff: rrand(80, 120)
PHASES = (0.25, 0.125)                        # slicer phase: [0.25,0.125].choose
FILTER_Q = 2.0
CHAIN_GAIN = 0.85
PAN = 0.55                                    # :dsaw stereo spread of the twins
SEED = 10                                     # use_random_seed 10

# Four full `sleep 8` iterations plus a 4 s outro swell of the fifth chord.
_BLOCKS = tuple((i * BLOCK_S, BLOCK_S) for i in range(4)) + ((4 * BLOCK_S, BLOCK_S / 2),)


def _cutoff_curve(cut_hi_midi: float, n: int) -> np.ndarray:
    """cutoff_slide 4: MIDI cutoff glides 30 -> cut_hi over 4 s, then holds."""
    ng = min(int(SLIDE_S * S.SR), n)
    midi = np.concatenate([np.linspace(CUTOFF_CLOSED, cut_hi_midi, ng),
                           np.full(n - ng, cut_hi_midi)])
    # S.cut() is scalar-only; same maths, vectorised (cutoff: is a MIDI note).
    return np.clip(440.0 * 2.0 ** ((midi - 69.0) / 12.0), 20.0, S.SR * 0.45)


def _block_voice(c1, c2, detune: float, cut_hi: float, n: int):
    """One continuous voice: triad c1 portamento-glides to triad c2."""
    cutoff = _cutoff_curve(cut_hi, n)
    up = np.zeros(n)
    dn = np.zeros(n)
    for m1, m2 in zip(c1, c2):
        f = S.glide_freq(S.hz(m1), S.hz(m2), n, SLIDE_S)  # note_slide: 4
        up += S.saw(f * 2.0 ** (detune / 24.0), n)        # :dsaw twin saws,
        dn += S.saw(f * 2.0 ** (-detune / 24.0), n)       # ±detune/2 semitones
    return up, dn, cutoff


def build(mix: S.Mix):
    rng = np.random.default_rng(SEED)                     # use_random_seed 10
    for i, (t0, dur_s) in enumerate(_BLOCKS):
        phase = float(S.pick(PHASES, rng))                # [0.25,0.125].choose
        root1 = str(S.pick(NOTES, rng))                   # notes.choose -> chord 1
        root2 = str(S.pick(NOTES, rng))                   # notes.choose -> chord 2
        detune = float(rng.uniform(*DETUNE_RANGE))        # rrand(0, 0.2)
        cut_hi = float(rng.uniform(*CUTOFF_OPEN_RANGE))   # rrand(80, 120)
        c1, c2 = S.chord(root1, "minor"), S.chord(root2, "minor")

        n = int(dur_s * S.SR)
        up, dn, cutoff = _block_voice(c1, c2, detune, cut_hi, n)
        e = S.env(n, attack=0.01, release=dur_s)          # release swell (sustain 0)
        # FX nesting of the source: slicer wraps reverb -> voice->reverb->slicer.
        for chain, pan, seed in ((up, -PAN, 11), (dn, PAN, 12)):
            v = S.lpf_curve(chain * e, cutoff, q=FILTER_Q)
            v = S.reverb(v, room=0.5, mix=0.3, seed=seed)
            v = S.slicer(v, phase_s=phase, wave=1)
            mix.add(v, t0, gain=CHAIN_GAIN, pan=pan)
        print(f"[tron_bike] block {i}: t={t0:4.1f}s dur={dur_s:.1f}s "
              f"slicer_phase={phase}s {root1}m{list(c1)} -> {root2}m{list(c2)} "
              f"detune={detune:.3f} cutoff 30->{cut_hi:.0f} (midi)")


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    m = S.Mix(LENGTH)
    build(m)
    S.write_wav(os.path.join(root, "audio", f"{NAME}.wav"), m.out(PEAK))
