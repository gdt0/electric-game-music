"""
jungle — port of the Sonic Pi example `illusionist/jungle.rb` by Sam Aaron
(distorted Amen-break jungle loop), rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/illusionist/jungle.rb
Local copy: sources/sonic-pi/illusionist__jungle.rb

The piece is a 4-beat loop at 50 BPM, played entirely inside four FX:

    with_fx :lpf, cutoff: 90 do                  # 1.5 kHz ceiling
      with_fx :reverb, mix: 0.5 do
        with_fx :compressor, pre_amp: 40 do
          with_fx :distortion, distort: 0.4 do
            live_loop :jungle do
              use_random_seed 667                # re-seeded every pass -> same 4 bars
              4.times do
                sample :loop_amen, beat_stretch: 1,
                       rate: [1, 1, 1, -1].choose / 2.0, finish: 0.5, amp: 0.5
                sample :loop_amen, beat_stretch: 1
                sleep 1
              end
            end

So each beat carries a chopped, half-speed (sometimes reversed) first half of the Amen
break stacked with the full break stretched to one beat — a thick, distorted, filtered
jungle groove.

LENGTH = 48 s (ten passes of the 4-beat loop). LOOP_BEATS = 4.

Approximations (no SuperCollider here)
    * `beat_stretch: 1` -> resampling the break to exactly one beat (1.2 s at 50 BPM);
    * `rate: -1` -> a reversed fragment, `finish: 0.5` -> the first half of the buffer;
    * `:distortion` -> tanh drive, `:compressor` -> S.compress, `:reverb`/`:lpf` -> the
      matching engine effects (cutoff 90 is a MIDI note -> S.cut(90) ≈ 1.5 kHz);
    * `use_random_seed 667` inside the loop body is reproduced literally: the rng is
      re-created for every pass, so all passes are identical.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import synth as S  # noqa: E402

NAME = "jungle"
TITLE = "Jungle — Sam Aaron, Sonic Pi example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/illusionist/jungle.rb"

BPM = 50
LENGTH = 48.0
LOOP_BEATS = 4
SEED = 667


def distorted(x: np.ndarray, drive: float = 3.2) -> np.ndarray:
    """Sonic Pi :distortion (distort: 0.4) -> soft saturation."""
    return np.tanh(x * drive) / np.tanh(drive)


def build(mix):
    beat = S.beats(BPM, 1)                  # 1.2 s
    cycle = S.beats(BPM, 4)                 # 4.8 s
    amen = S.SAMPLES.get("loop_amen")
    stretched = S.resample(amen, rate=(len(amen) / S.SR) / beat)   # beat_stretch: 1

    passes = int(np.ceil(LENGTH / cycle))
    for p in range(passes):
        base = p * cycle
        if base >= LENGTH:
            break

        rng = np.random.default_rng(SEED)   # `use_random_seed 667` inside the loop body
        buf = np.zeros(int(cycle * S.SR))
        for step in range(4):
            rate = float(rng.choice([1, 1, 1, -1])) / 2.0
            chopped = stretched[: int(0.5 * len(stretched))]        # finish: 0.5
            if rate < 0:
                chopped = chopped[::-1]
                rate = -rate
            chopped = S.resample(chopped, rate) * 0.5               # rate 0.5 -> 2x longer
            full = stretched.copy()

            t = base + step * beat
            i = int(t * S.SR)
            for seg in (chopped, full):
                m = min(len(seg), len(buf) - (i - int(base * S.SR)))
                if m > 0:
                    j = i - int(base * S.SR)
                    buf[j:j + m] += seg[:m]

        # ---- the FX chain the loop sits inside
        bus = S.lpf(buf, S.cut(90), q=0.8)
        bus = distorted(bus)
        bus = S.compress(bus, threshold=0.5, ratio=8.0)
        bus = S.reverb(bus, room=0.6, mix=0.5, damp=0.5)
        mix.add(bus, base, gain=1.15, pan=0.0)
