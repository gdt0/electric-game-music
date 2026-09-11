"""
dark_neon — port of the Sonic Pi example `incubation/dark_neon.rb` by Sam Aaron,
rendered headlessly with engine/synth.py.

Upstream source:
    https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/incubation/dark_neon.rb

Structure (two live loops, 60 BPM)
    :foo   `bd_haus` kick every 0.5 beat (upstream: amp 5, cutoff 50,
           release 0.1 — the amp key is literally duplicated upstream,
           harmlessly) — a driving four-on-the-floor kick;
    :mel   every 4 beats:
             * `:blade` note :cs1 (34.6 Hz), release 4, cutoff 110, amp 1,
               wrapped in a `:wobble` FX (phase 1, wave 0 saw LFO,
               invert_wave 1, cutoff_min 60 -> cutoff_max 80 MIDI);
             * `bass_trance_c` at rate 0.5, pitch 0, window_size 0.125,
               time_dis 0.125, amp 8, release 0.2, wrapped in
               `:reverb room 1` around a `:bitcrusher mix 0.4`.

Approximations (no SuperCollider here)
    * `:blade` -> 6-saw detuned supersaw stack (±0.06..0.36 semitone) with a
      slow vibrato plus an initial pitch swoop and a whole-note decay, so the
      4-beat note swells/pulses instead of sounding like a static drone; its
      own cutoff (S.cut(110)) is applied, then the wobble: a per-sample
      inverted-saw LFO at 1 Hz sweeping S.cut(80) down to S.cut(60) through
      S.lpf_curve(q=3) — matching wave 0 + invert_wave 1;
    * window_size == time_dis == 0.125 s means contiguous grains, i.e. the
      plain sample — so `rate: 0.5` playback (start of the sample) is a
      faithful approximation;
    * `:bitcrusher mix 0.4` -> 0.6*dry + 0.4 * S.bitcrush(bits 7, hold 2);
    * `:reverb room 1` -> S.reverb(room=1, mix=0.35);
    * cutoff / cutoff_min / cutoff_max are MIDI note numbers -> S.cut();
    * FX nesting order kept: sample -> bitcrusher -> reverb (outside-in);
    * original amps (kick 5 / bass 8 / blade 1) rebalanced for the headless
      bus (3.2 / 2.0 / 2.4); the piece is fully deterministic, so the fixed
      seed rng (np.random.default_rng(3)) is instantiated but draws nothing.
"""
import numpy as np

from engine import synth as S

NAME = "dark_neon"
TITLE = "Dark Neon — Sam Aaron, Sonic Pi example"
SOURCE = ("https://github.com/sonic-pi-net/sonic-pi/blob/dev/"
          "etc/examples/incubation/dark_neon.rb")
BPM = 60
LENGTH = 40.0            # ten 4-beat passes of :mel
RNG_SEED = 3             # fixed seed, documented; nothing random in this piece

BLADE_DETUNE = (-0.33, -0.19, -0.06, 0.10, 0.22, 0.36)   # semitones


def blade(note, dur_s: float, cutoff_midi: float, release: float) -> np.ndarray:
    """`:blade` approximation: detuned supersaw with slow pitch movement,
    envelope (attack / whole-note decay / release), then its own low-pass at
    the played cutoff. The wobble FX is applied on top by the caller, exactly
    like the with_fx wrapping in the original."""
    n = max(int(dur_s * S.SR), 8)
    f = S.hz(note)
    tt = np.arange(n) / S.SR
    vibrato = 0.12 * np.sin(2 * np.pi * 0.35 * tt + 1.1)   # ~±12 cents, slow
    swoop = -0.35 * np.exp(-tt / 0.5)                      # glides up ~35 cents
    freq = f * 2.0 ** ((vibrato + swoop) / 12.0)
    out = np.zeros(n)
    for i, cents in enumerate(BLADE_DETUNE):
        out += S.saw(freq * 2.0 ** (cents / 12.0), n, phase0=0.09 * i)
    out /= len(BLADE_DETUNE)
    out *= S.env(n, 0.05, release, decay=dur_s)
    return S.lpf(out, S.cut(cutoff_midi), q=0.8)


def wobble(x: np.ndarray, phase_s: float, cutoff_min_midi: float,
           cutoff_max_midi: float, q: float = 3.0) -> np.ndarray:
    """`:wobble` FX: inverted sawtooth LFO (wave 0 + invert_wave 1) sweeping
    the low-pass cutoff from cutoff_max down to cutoff_min each phase."""
    tt = np.arange(len(x)) / S.SR
    p = np.mod(tt / max(phase_s, 1e-3), 1.0)
    c_hi, c_lo = S.cut(cutoff_max_midi), S.cut(cutoff_min_midi)
    return S.lpf_curve(x, c_hi - (c_hi - c_lo) * p, q=q)


def trance_bass(amp: float, release: float) -> np.ndarray:
    """`bass_trance_c` chain at rate 0.5: playback -> release fade ->
    bitcrusher (mix 0.4) -> reverb room 1, i.e. the original FX nesting."""
    seg = S.resample(S.SAMPLES.get("bass_trance_c"), 0.5)
    seg = seg * S.env(len(seg), 0.002, release)
    seg = 0.6 * seg + 0.4 * S.bitcrush(seg, bits=7, hold=2)
    return S.reverb(seg, room=1.0, mix=0.35) * amp


def kick(amp: float, cutoff_midi: float, release: float) -> np.ndarray:
    """`bd_haus` through its cutoff (MIDI note 50) with a 0.1 s release fade."""
    seg = S.lpf(S.SAMPLES.get("bd_haus"), S.cut(cutoff_midi), q=0.7)
    return seg * S.env(len(seg), 0.001, release) * amp


def build(mix):
    rng = np.random.default_rng(RNG_SEED)   # fixed seed; nothing drawn here
    mel = S.beats(BPM, 4.0)                 # :mel loop period
    half = S.beats(BPM, 0.5)                # :foo loop period

    # :mel voices are identical every pass (same args each live_loop run) —
    # render them once and bus them at each 4-beat interval.
    note = blade("cs1", S.beats(BPM, 4.0), 110, 4.0)
    blade_sig = wobble(note, 1.0, 60, 80) * 2.4
    bass_sig = trance_bass(2.0, 0.2)
    kick_sig = kick(3.2, 50, 0.1)

    # :foo — four-on-the-floor kick every 0.5 beat
    t = 0.0
    while t < LENGTH - 1e-6:
        mix.add(kick_sig, t)
        t += half

    # :mel — wobbled :blade + processed :bass_trance_c every 4 beats
    t = 0.0
    while t < LENGTH - 1e-6:
        mix.add(blade_sig, t)
        mix.add(bass_sig, t)
        t += mel
