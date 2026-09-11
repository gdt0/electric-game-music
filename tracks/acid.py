"""
acid — port of the Sonic Pi example `magician/acid.rb` by Sam Aaron,
rendered headlessly with engine/synth.py.

Upstream source: https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/acid.rb

Structure (two live loops, both 18 beats long, so they lock together)
    :drums_n_bass   28 x ( `drum_bass_hard` + `:fm` note e2 + `elec_cymbal` rate 12 ),
                    every 0.5 beat, then a 4-beat break;
    :walk           TB-303 acid line (64 x 0.125 beat over chord e3 minor),
                    then a `:prophet` pad section (chord a3 m7, 32 x 0.125),
                    then TB-303 again (chord e3 minor, 32 x 0.125),
                    then an echo section (chord from e2/e3/e4 m7, 16 x 0.125),
                    with `ambi_lunar_land` washed through a slicer.

Approximations (no SuperCollider here)
    * `:tb303` -> saw through a high-Q low-pass whose cutoff decays from a bright
      accent down to the played cutoff value (the classic squelch);
    * `:fm` -> 2-operator sine FM (divisor 2, depth 1);
    * `:prophet` -> detuned supersaw pad;
    * cutoff values in the original are MIDI note numbers -> S.cut();
    * `.choose` / `rrand` are re-rolled every run in Sonic Pi: seeded here (SEED)
      so the render is reproducible.
"""
import numpy as np

from engine import synth as S

NAME = "acid"
TITLE = "Acid — Sam Aaron, Sonic Pi example"
SOURCE = "https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/acid.rb"
BPM = 60
LENGTH = 36.0            # two full 18-beat passes
SEED = 5


def tb303(note, dur_s: float, cutoff_midi: float, release: float, q: float = 9.0,
          accent: float = 1.0) -> np.ndarray:
    """Squelchy acid voice: saw + decaying resonant low-pass."""
    n = max(int(dur_s * S.SR), 8)
    f = S.hz(note)
    body = S.saw(f, n) * S.env(n, 0.004, release, decay=0.08)
    c_top = S.cut(min(cutoff_midi + 45.0 * accent, 132.0))
    c_low = S.cut(cutoff_midi)
    ramp = min(int(0.16 * S.SR), n)
    curve = np.concatenate([np.linspace(c_top, c_low, ramp), np.full(n - ramp, c_low)])
    return S.lpf_curve(body, curve, q=q)


def fm_bass(note, dur_s: float, release: float, divisor: float = 2.0,
            depth: float = 1.0) -> np.ndarray:
    n = max(int(dur_s * S.SR), 8)
    f = S.hz(note)
    tt = np.arange(n) / S.SR
    env = S.env(n, 0.004, release, decay=0.12)
    return np.sin(2 * np.pi * f * tt + depth * np.sin(2 * np.pi * f * divisor * tt)) * env


def prophet(notes, dur_s: float, cutoff_midi: float, release: float) -> np.ndarray:
    n = max(int(dur_s * S.SR), 8)
    out = np.zeros(n)
    for i, note in enumerate(notes):
        f = S.hz(note)
        for d in (-0.18, 0.0, 0.18):
            out += S.saw(f * 2.0 ** (d / 12.0), n, phase0=0.13 * i)
    out /= max(3.0 * len(notes), 1.0)
    out *= S.env(n, 0.01, release, decay=0.05)
    return S.lpf_curve(out, np.full(n, S.cut(cutoff_midi)), q=1.4)


def build(mix):
    rng = np.random.default_rng(SEED)
    e_minor = S.chord("e3", "minor")            # [e3, g3, b3]
    a_m7 = S.chord("a3", "m7")                  # [a3, c4, e4, g4]
    echo_roots = ["e2", "e3", "e4"]
    cycle = S.beats(BPM, 18)                    # 18 beats = 18 s at 60 BPM

    passes = int(np.ceil(LENGTH / cycle))
    for p in range(passes):
        base = p * cycle
        if base >= LENGTH:
            break

        # ---------------- :drums_n_bass ----------------
        for i in range(28):
            t = base + S.beats(BPM, 0.5) * i
            if t + 1.0 > LENGTH:
                break
            mix.sample("drum_bass_hard", t, amp=0.62)
            mix.add(fm_bass("e2", S.beats(BPM, 0.45), release=0.2), t, gain=0.5, pan=0.05)
            mix.sample("elec_cymbal", t, rate=12.0, amp=0.28, pan=-0.25)

        # ---------------- :walk ----------------
        # TB-303 phrase, 64 x 0.125 beat
        t = base
        for _ in range(64):
            note = e_minor[rng.integers(0, len(e_minor))]
            rel = float(rng.uniform(0.05, 0.3))
            cutv = float(rng.uniform(50, 90))
            mix.add(tb303(note, max(rel, 0.06) * 1.4, cutv, rel, q=10.0, accent=1.0),
                    t, gain=0.5, pan=float(rng.uniform(-0.25, 0.25)))
            t += S.beats(BPM, 0.125)

        # prophet pad, 32 x 0.125
        for i in range(32):
            note = a_m7[rng.integers(0, len(a_m7))]
            rel = float(rng.uniform(0.1, 0.2))
            cutv = float(rng.uniform(40, 130))
            mix.add(prophet([note], 0.35, cutv, rel), t, gain=0.42,
                    pan=float(rng.uniform(-0.4, 0.4)))
            t += S.beats(BPM, 0.125)

        # TB-303 again, brighter, 32 x 0.125
        for _ in range(32):
            note = e_minor[rng.integers(0, len(e_minor))]
            rel = float(rng.uniform(0.05, 0.3))
            cutv = float(rng.uniform(110, 130))
            mix.add(tb303(note, max(rel, 0.06) * 1.4, cutv, rel, q=7.0, accent=1.0),
                    t, gain=0.34, pan=0.2 * (-1) ** rng.integers(0, 2))
            t += S.beats(BPM, 0.125)

        # echo stragglers, 16 x 0.125
        phrase = np.zeros(0)
        for _ in range(16):
            root = echo_roots[rng.integers(0, len(echo_roots))]
            note = S.chord(root, "m7")[rng.integers(0, 4)]
            cutv = float(rng.uniform(50, 129))
            frag = tb303(note, 0.3, cutv, 0.05, q=6.0, accent=0.4)
            mix.add(S.echo(frag, S.beats(BPM, 0.25), feedback=0.45, mix=0.5),
                    t, gain=0.4, pan=float(rng.uniform(-0.5, 0.5)))
            t += S.beats(BPM, 0.125)

        # ambi_lunar_land washed through a slicer (Sonic Pi: sustain 0, release 8, amp 2)
        amb = S.slicer(S.SAMPLES.get("ambi_lunar_land"), phase_s=S.beats(BPM, 0.125),
                       wave=1, amp=0.85)
        mix.add(amb, base, gain=0.28, pan=0.0)
