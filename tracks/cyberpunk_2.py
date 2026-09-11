"""
cyberpunk_2 — port of the Sonic Pi piece `cyberpunk` (2024-01-20) by ikemura23,
rendered headlessly with engine/synth.py.

Upstream source: https://twitter.com/ikemura23/status/1748822961614934090
Local copy: sources/sonic-pi/2024-01-20_cyberpunk.rb

The file has no `use_bpm`, so Sonic Pi's default 60 BPM applies: one beat = 1 s.
Every live_loop syncs to a 1-beat metronome (:met), so all loops stay locked to
the same 16-beat grid:

    :met          sleep 1  (the clock)
    :amen         `loop_amen_full, beat_stretch: 8` on beats 0-8, then the same
                  sample with `start: 0, finish: 0.75` on beats 8-16 (16-beat loop)
    :drum_splash  `drum_splash_soft` every 16 beats
    :s            `:tech_saws`, one continuous note per 4-beat block: :eb2 held
                  with `note_slide: 0.1, sustain: 4, release: 0`, gliding once per
                  beat to :eb2+7, :eb2+10, :eb2+5, then 4 beats rest (8-beat loop)
    :s2           `:dpulse` at amp 0.15 with the SAME pitch sequence as :s
                  (a doubled, quieter pulse layer)
    :s3           starts with `stop` -> never runs; SKIPPED here on purpose.

LENGTH = 48 s = three passes of the 16-beat grid (Sonic Pi would loop forever).

Approximations (no SuperCollider here)
    * `:tech_saws` -> 5 polyBLEP saws detuned +-0.13/-0.06/0 semitones,
      normalised to unit peak (Sonic Pi's supersaw stack);
    * `:dpulse` -> two pulse waves (width 0.5) detuned +-0.1 semitones;
    * `note_slide: 0.1` -> S.glide_freq() linear 0.1 s glides, the four 1-beat
      segments concatenated into one continuous 4 s frequency curve;
    * `release: 0, sustain: 4` -> hard cut at 4 s (a ~3 ms anti-click fade is the
      only smoothing);
    * `beat_stretch: 8` -> resample the sample so it lasts 8 beats. NOTE on the
      second amen hit: Sonic Pi computes beat_stretch's rate from the FULL
      sample and only then applies start/finish, so the 0..0.75 slice rings for
      0.75 * 8 = 6 beats followed by 2 beats of silence — which is exactly why
      the original writes `sleep 6; sleep 2`. Ported the same way (slice first,
      then the full-stretch rate), not by stretching the slice to 8 s.
      (loop_amen_full is 6.86 s of source audio -> rate = 6.857/8 = 0.857.)
    * `play ... do |s| ... end` block sleeps technically advance the Sonic Pi
      thread, which would make :s/:s2 7-beat loops (3 s of controls + `sleep 4`);
      the reads-as-written 8-beat grid (4 s note + 4 s rest) is ported here, per
      the piece's obvious design — the drone lines up with the amen halves.
    * default amp 1.0 kept for both samples; the two synth voices are mixed at
      the original relative level (:s2 = 0.15 x :s).
"""
import numpy as np

from engine import synth as S

NAME = "cyberpunk_2"
TITLE = "Cyberpunk — ikemura23, Sonic Pi (2024-01-20)"
SOURCE = "https://twitter.com/ikemura23/status/1748822961614934090"
BPM = 60                  # Sonic Pi default — the source has no use_bpm
LENGTH = 48.0             # 3 x 16-beat grid
PEAK = 0.9
CYCLE = 16                # beats per :amen / :drum_splash pass
BEAT = S.beats(BPM, 1.0)  # exactly 1.0 s

KEY = S.midi("eb2")                       # 39
PITCH_STEPS = [KEY, KEY + 7, KEY + 10, KEY + 5]   # eb2 -> +7 -> +10 -> +5


def _ramp_out(x: np.ndarray, dur_s: float = 0.003) -> np.ndarray:
    """Anti-click fade at the very end (release: 0 is a hard cut otherwise)."""
    k = min(int(dur_s * S.SR), len(x) - 1)
    if k > 1:
        x[-k:] *= np.linspace(1.0, 0.0, k)
    return x


def glide_curve(steps_midi, n: int, slide_s: float = 0.1) -> np.ndarray:
    """One continuous frequency curve: 4 x 1-beat segments, 0.1 s slides."""
    freqs = [S.hz(m) for m in steps_midi]
    per = int(BEAT * S.SR)
    parts = [S.glide_freq(freqs[i], freqs[i + 1], per, slide_s)
             for i in range(len(freqs) - 1)]
    parts.append(np.full(n - sum(len(p) for p in parts), freqs[-1]))
    curve = np.concatenate(parts)
    if len(curve) != n:
        curve = np.interp(np.linspace(0.0, 1.0, n),
                          np.linspace(0.0, 1.0, len(curve)), curve)
    return curve


def tech_saws(freq_curve: np.ndarray, n: int) -> np.ndarray:
    """Sonic Pi :tech_saws — a stack of slightly detuned saws."""
    out = np.zeros(n)
    for d in (-0.13, -0.06, 0.0, 0.06, 0.13):
        out += S.saw(freq_curve * 2.0 ** (d / 12.0), n, phase0=0.17 * abs(d) * 10)
    return out / max(np.abs(out).max(), 1e-9)


def dpulse(freq_curve: np.ndarray, n: int, detune: float = 0.1,
           width: float = 0.5) -> np.ndarray:
    """Sonic Pi :dpulse — two slightly detuned pulse waves."""
    a = S.pulse(freq_curve * 2.0 ** (detune / 12.0), n, width, phase0=0.0)
    b = S.pulse(freq_curve * 2.0 ** (-detune / 12.0), n, width, phase0=0.31)
    return (a + b) / max(np.abs(a + b).max(), 1e-9)


def synth_block(mix: S.Mix, t: float, gain: float):
    """One 4-beat :s / :s2 note (sustain 4, release 0, note_slide 0.1)."""
    n = int(4 * BEAT * S.SR)
    curve = glide_curve(PITCH_STEPS, n)
    env = S.env(n, 0.004, 0.001)          # flat sustain, hard cut (release: 0)
    saws = _ramp_out(tech_saws(curve, n) * env)
    pulses = _ramp_out(dpulse(curve, n) * env)
    mix.add(saws, t, gain=gain)                       # :s   (amp 1.0)
    mix.add(pulses, t, gain=gain * 0.15, pan=0.03)    # :s2  (amp 0.15)


def build(mix: S.Mix):
    amen = S.SAMPLES.get("loop_amen_full")
    # beat_stretch: 8 rate is computed from the FULL sample (see docstring)
    amen_rate = (len(amen) / S.SR) / S.beats(BPM, 8)

    passes = int(np.ceil(LENGTH / (CYCLE * BEAT)))
    for p in range(passes):
        base = p * CYCLE * BEAT
        if base >= LENGTH - 1e-9:
            break

        # ---------------- :amen ----------------
        mix.beat_stretch_sample("loop_amen_full", base, 8, BPM, amp=0.9)
        mix.sample("loop_amen_full", base + 8 * BEAT, rate=amen_rate,
                   start=0.0, finish=0.75, amp=0.9)   # rings 6 s, 2 s gap

        # ---------------- :drum_splash ----------------
        mix.sample("drum_splash_soft", base, amp=0.6)

        # ---------------- :s + :s2 ----------------
        synth_block(mix, base, gain=0.36)
        synth_block(mix, base + 8 * BEAT, gain=0.36)
        # (beats 4-8 / 12-16 of each pass are the written `sleep 4` rests)
