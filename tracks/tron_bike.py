"""
tron_bike — port of the Sonic Pi example `magician/tron_bike.rb` by Sam Aaron
(the Tron light-cycle drone), rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/tron_bike.rb
Local copy: sources/sonic-pi/magician__tron_bike.rb

The whole piece is one `live_loop :tron` that fires every 8 beats (8 s at 60 BPM):

    notes = (ring :b1, :b2, :e1, :e2, :b3, :e3)
    n1 = (chord notes.choose, :minor).choose
    n2 = (chord notes.choose, :minor).choose
    p = play n1, amp: 2, release: 8, note_slide: 4, cutoff: 30, cutoff_slide: 4,
               detune: rrand(0, 0.2), synth: :dsaw
    control p, note: n2, cutoff: rrand(80, 120)

inside a `:slicer` (phase 0.25 or 0.125) and a reverb (room 0.5, mix 0.3).

So: a dark detuned-saw drone that starts a minor third/root deep in the B1-E3 range,
glides for four seconds up to another chord tone, with the low-pass opening from
MIDI 30 (≈46 Hz — nearly closed) to a random value in 80..120 MIDI (≈200 Hz - 2 kHz),
then rings for the remaining four seconds.

LENGTH = 36 s (four and a half 8-beat blocks — the loop is endless in Sonic Pi).

Approximations (no SuperCollider here)
    * `:dsaw` -> a pair of saws detuned by ±detune/2 semitones;
    * `note_slide: 4` -> S.glide_freq(f1, f2, n, 4.0); `cutoff_slide: 4` ->
      S.lpf_curve() with a 4 s ramp from S.cut(30) to the random target;
    * `:slicer` -> S.slicer(phase 0.25 or 0.125, wave 1); reverb -> S.reverb;
    * the random `.choose` / `rrand` values are seeded (np.random.default_rng(10)) so the
      render is reproducible — Sonic Pi re-rolls them every run.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import synth as S  # noqa: E402

NAME = "tron_bike"
TITLE = "Tron Bike — Sam Aaron, Sonic Pi example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/tron_bike.rb"

BPM = 60
LENGTH = 36.0
SEED = 10
ROOTS = ["b1", "b2", "e1", "e2", "b3", "e3"]


def build(mix):
    rng = np.random.default_rng(SEED)
    block = 8                                   # 8 beats per loop at 60 BPM = 8 s
    started = False

    for b in range(int(np.ceil(LENGTH / block))):
        t0 = b * block
        if t0 >= LENGTH:
            break

        n1 = float(S.chord(ROOTS[rng.integers(0, len(ROOTS))], "minor")[rng.integers(0, 3)])
        n2 = float(S.chord(ROOTS[rng.integers(0, len(ROOTS))], "minor")[rng.integers(0, 3)])
        detune = float(rng.uniform(0.0, 0.2))
        cutoff_target = float(rng.uniform(80.0, 120.0))
        phase = float(rng.choice([0.25, 0.125]))

        n = int(block * S.SR)
        f_curve = S.glide_freq(S.hz(n1), S.hz(n2), n, 4.0)
        sig = S.saw(f_curve, n) + S.saw(f_curve * 2.0 ** (-detune / 24.0), n, phase0=0.31)
        sig = sig * 0.5

        glide = min(int(4.0 * S.SR), n)
        cut_curve = np.concatenate([np.linspace(S.cut(30), S.cut(cutoff_target), glide),
                                    np.full(n - glide, S.cut(cutoff_target))])
        sig = S.lpf_curve(sig, cut_curve, q=2.0)
        sig *= S.env(n, 0.02, 0.35)

        sig = S.slicer(sig, phase_s=phase, wave=1, amp=1.0)
        sig = S.reverb(sig, room=0.5, mix=0.3)
        mix.add(sig, t0, gain=0.5, pan=float(rng.uniform(-0.1, 0.1)))
        started = True

    del started
