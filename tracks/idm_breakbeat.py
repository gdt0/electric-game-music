"""
idm_breakbeat — port of the Sonic Pi example `magician/idm_breakbeat.rb` by Sam Aaron
(a slicing IDM breakbeat loop), rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/idm_breakbeat.rb
Local copy: sources/sonic-pi/magician__idm_breakbeat.rb

The whole piece is one live loop that re-rolls itself every pass:

    live_loop :idm_bb do
      n = [1,2,4,8,16].choose                     # slice division
      sample :drum_heavy_kick, amp: 2
      sample :ambi_drone,      rate: [0.25,0.5,0.125,1].choose, amp: 0.25 if one_in(8)
      sample :ambi_lunar_land, rate: [0.5,0.125,1,-1,-0.5].choose, amp: 0.25 if one_in(8)
      sample :loop_amen, attack: 0, release: 0.05,
             start: 1 - (1.0 / n), rate: [1,1,1,1,1,1,-1].choose
      sleep sample_duration(:loop_amen) / n
    end

So: a kick every pass, then the *last 1/n* of the Amen break — sometimes backwards — and
the loop rests for exactly that slice's duration, which means the slice duration is what
drives the whole rhythm: n=1 → the whole break over its full length, n=16 → a 16th-note
machine-gun of fragments.

LENGTH = 40 s (the loop is endless in Sonic Pi). LOOP_BEATS = 8.

Approximations (no SuperCollider here)
    * `sample_duration(:loop_amen)` -> the real length of samples/loop_amen.flac;
    * `start:` -> a slice bound into the raw sample, `rate: -1` -> a reversed fragment;
    * `release: 0.05` -> a 50 ms anti-click fade on every fragment;
    * `one_in(8)` / `.choose` are seeded (np.random.default_rng(3)) for reproducibility.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import synth as S  # noqa: E402

NAME = "idm_breakbeat"
TITLE = "IDM Breakbeat — Sam Aaron, Sonic Pi example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/idm_breakbeat.rb"

BPM = 60
LENGTH = 40.0
LOOP_BEATS = 8
SEED = 3


def build(mix):
    rng = np.random.default_rng(SEED)
    amen = S.SAMPLES.get("loop_amen")
    amen_dur = len(amen) / S.SR          # what Sonic Pi calls sample_duration(:loop_amen)
    t = 0.0

    while t < LENGTH:
        n = int(rng.choice([1, 2, 4, 8, 16]))

        mix.sample("drum_heavy_kick", t, amp=1.6)

        if rng.integers(8) == 0:
            mix.add(S.resample(S.SAMPLES.get("ambi_drone"),
                               float(rng.choice([0.25, 0.5, 0.125, 1.0]))),
                    t, gain=0.25, pan=0.0)
        if rng.integers(8) == 0:
            mix.add(S.resample(S.SAMPLES.get("ambi_lunar_land"),
                               float(rng.choice([0.5, 0.125, 1.0, -1.0, -0.5]))),
                    t, gain=0.25, pan=0.0)

        rate = float(rng.choice([1, 1, 1, 1, 1, 1, -1]))
        start = 1.0 - (1.0 / n)
        frag = amen[int(start * len(amen)):]
        if rate < 0:
            frag = frag[::-1]
            rate = -rate
        if abs(rate - 1.0) > 1e-9:
            frag = S.resample(frag, rate)
        frag = frag * S.env(len(frag), 0.0005, 0.05)
        mix.add(frag, t, gain=0.9, pan=float(rng.uniform(-0.25, 0.25)))

        t += amen_dur / n
