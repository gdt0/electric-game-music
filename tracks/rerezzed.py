"""
rerezzed — port of the Sonic Pi example `sorcerer/rerezzed.rb` by Sam Aaron
(Daft Punk, "Tron: Legacy" — Rerezzed), rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/sorcerer/rerezzed.rb

Faithful parts
    * the idea: a single held `dsaw` voice that step-glides (note_slide 0.04 s)
      through a shuffled E-minor-pentatonic note list, one note every 0.125 beats,
      64 notes per 8-beat cycle, then bit-crushed;
    * `loop_industrial` beat-stretched to one beat, every beat;
    * `bd_haus` (amp 3) on every 0.5 beat.

Approximations (no SuperCollider here)
    * `:dsaw` -> two saws detuned symmetrically; `:bitcrusher` -> S.bitcrush;
    * `beat_stretch: 1` -> resampling (pitch shifts slightly, tempo is right);
    * Sonic Pi `.shuffle` is re-rolled every run — here it is seeded (see SEED)
      so the render is reproducible.
"""
import numpy as np

from engine import synth as S

NAME = "rerezzed"
TITLE = "Rerezzed (Tron: Legacy) — Sam Aaron, Sonic Pi example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/sorcerer/rerezzed.rb"
BPM = 60
LENGTH = 40.0
SEED = 10


def dsaw_voice(freq_curve, detune: float, attack: float = 0.01) -> np.ndarray:
    """Tone with a per-sample frequency curve (i.e. note_slide portamento)."""
    n = len(freq_curve)
    a = S.saw(freq_curve, n)
    b = S.saw(freq_curve * 2.0 ** (-detune / 24.0), n, phase0=0.37)
    c = S.saw(freq_curve * 2.0 ** (detune / 24.0), n, phase0=0.71)
    return (a + b + c) / 3.0 * S.env(n, attack, 0.08)


def build(mix):
    rng = np.random.default_rng(SEED)
    step = S.beats(BPM, 0.125)              # 0.125 beats at 60 BPM = 0.125 s
    cycle = step * 64                       # 8 beats = 8 s

    # ---- the shuffled scale (Sonic Pi: scale(:e1, :minor_pentatonic, num_octaves: 2).shuffle)
    notes = S.scale("e1", "minor_pentatonic", 2)
    order = list(rng.permutation(np.asarray(notes, dtype=float)))

    # ---- build the 64-step gliding frequency curve once, reuse every cycle
    per_step = int(step * S.SR)
    curve_parts = []
    prev = S.hz(order[0])
    for note in order:
        target = S.hz(note)
        curve_parts.append(S.glide_freq(prev, target, per_step, 0.04))
        prev = target
    curve = np.concatenate(curve_parts)

    # three voices, slightly different detune, like the live loop re-rolling detune
    voices = [dsaw_voice(curve, detune=d) for d in (0.08, 0.15, 0.2)]

    n_cycles = int(np.ceil(LENGTH / cycle))
    for k in range(n_cycles):
        t0 = k * cycle
        if t0 >= LENGTH:
            break
        lead = S.bitcrush(voices[k % len(voices)], bits=6, hold=2)
        lead = S.lpf(lead, S.cut(118), q=1.2)
        mix.add(lead, t0, gain=0.5, pan=-0.05)

        # ---- industrial loop, beat_stretched to exactly one beat
        t = t0
        while t < min(t0 + cycle, LENGTH):
            mix.beat_stretch_sample("loop_industrial", t, 1, BPM, amp=0.75, lpf_hz=S.cut(112))
            t += S.beats(BPM, 1)

        # ---- four-on-the-floor-ish kick, every 0.5 beat
        t = t0
        while t < min(t0 + cycle, LENGTH):
            mix.sample("bd_haus", t, amp=1.1, lpf_hz=S.cut(120))
            t += S.beats(BPM, 0.5)
