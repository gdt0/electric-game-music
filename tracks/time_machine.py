"""
time_machine — port of the Sonic Pi example `wizard/time_machine.rb` by Sam Aaron,
rendered headlessly with engine/synth.py (no SuperCollider on this server).

Upstream source:
https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/wizard/time_machine.rb

All four simultaneous live loops are reproduced:

    :time       synth :tb303, note :e1, release 8, amp 0.8, every 8 beats,
                cutoff ticking (range 90, 60, -10) == 90, 80, 70, 60 (MIDI notes)
    :machine    sample :loop_garzul every 8 beats, rate (knit 1, 3, -1, 1).tick
                == 1, 1, 1, -1 (negative rate = reversed), hpf: 80
    :vortex     32nd-note arpeggio (sleep 0.125 beats): use_synth
                [:pulse, :beep].choose per note, scale(:e1, :minor_pentatonic)
                stepped upward via .tick, release 0.1, amp 2, cutoff .choose
                from (ring 70, 90, 100, 130), whole bus through with_fx :hpf,
                cutoff: 42, amp: 0.8
    :moon_bass  sample :bd_haus, amp 1.5, lpf: 110, every 0.5 beats

At 60 BPM, loop_garzul is exactly 8.00 s == 8 beats, so it is played at rate 1
(once per loop), and the "tick" rings cycle per 8-beat pass exactly like the
live loops re-rolling.

Approximations (Sonic Pi -> numpy synth):
    * :tb303   -> resonant squelchy saw: S.saw at e1 through S.lpf_curve with
      high q (8) whose cutoff follows the 90/80/70/60 MIDI-note cycle via
      S.cut(), times an ~8 s exponential decay envelope (tb303 sustain_level 0).
    * :pulse   -> S.pulse with width 0.3;  :beep -> short S.tri blip.
    * rate -1  -> the decoded sample array reversed (S.resample(seg, -1)).
    * lpf/hpf/cutoff values are MIDI notes, converted with S.cut().
    * .choose is random per run in Sonic Pi — here it is seeded (SEED,
      np.random.default_rng) so the render is reproducible.
"""
import numpy as np

from engine import synth as S

NAME = "time_machine"
TITLE = "Time Machine — Sam Aaron, Sonic Pi example"
SOURCE = ("https://github.com/sonic-pi-net/sonic-pi/blob/dev/"
          "etc/examples/wizard/time_machine.rb")
BPM = 60
LENGTH = 44.0
SEED = 11
PEAK = 0.9


def build(mix):
    rng = np.random.default_rng(SEED)
    B = lambda b: S.beats(BPM, b)           # beats -> seconds (quarter notes)

    # ---- :time — tb303 drone, note :e1, cutoff (range 90, 60, -10).tick ----
    cutoff_ring = [90, 80, 70, 60]          # MIDI note numbers, like Sonic Pi
    t, i = 0.0, 0
    while t < LENGTH - 1e-9:
        n = int(B(8) * S.SR)                # release: 8 == the whole loop pass
        sig = S.saw(S.hz("e1"), n) * S.env(n, attack=0.01, release=B(8))
        cut_curve = np.full(n, S.cut(cutoff_ring[i % 4]))
        sig = S.lpf_curve(sig, cut_curve, q=8.0)
        mix.add(sig, t, gain=0.8)
        t += B(8)
        i += 1

    # ---- :machine — :loop_garzul, rate (knit 1, 3, -1, 1).tick, hpf: 80 ----
    rate_ring = [1.0, 1.0, 1.0, -1.0]       # -1 = reversed pass
    t, i = 0.0, 0
    while t < LENGTH - 1e-9:
        mix.sample("loop_garzul", t, rate=rate_ring[i % 4], hpf_hz=S.cut(80))
        t += B(8)
        i += 1

    # ---- :vortex — 32nd-note arp through hpf cutoff 42 (amp 0.8) ----------
    notes = S.scale("e1", "minor_pentatonic")       # e1 g1 a1 b1 d2 (one octave)
    cutoff_choose = [70, 90, 100, 130]              # (ring 70, 90, 100, 130)
    n = int(0.11 * S.SR)                            # attack 0.002 + release 0.1
    envelope = S.env(n, attack=0.002, release=0.1)
    arp = np.zeros(int((LENGTH + 0.2) * S.SR))      # spare room for last release
    t, k = 0.0, 0
    while t < LENGTH - 1e-9:
        synth = ("pulse", "beep")[int(rng.integers(0, 2))]   # [:pulse,:beep].choose
        note = notes[k % len(notes)]                        # .tick steps upward
        co = cutoff_choose[int(rng.integers(0, 4))]         # .choose
        if synth == "pulse":
            osc = S.pulse(S.hz(note), n, width=0.3)
        else:                                               # :beep
            osc = S.tri(S.hz(note), n)
        sig = S.lpf(osc * envelope, S.cut(co), q=1.5)
        j = int(t * S.SR)
        arp[j:j + n] += sig                                 # amp: 2 pre-fx
        t += B(0.125)                                       # 32nd notes at 60 BPM
        k += 1
    arp = S.hpf(arp, S.cut(42))                     # with_fx :hpf, cutoff: 42
    mix.add(arp, 0.0, gain=0.8)

    # ---- :moon_bass — :bd_haus amp 1.5, lpf: 110, every 0.5 beats ---------
    t = 0.0
    while t < LENGTH - 1e-9:
        mix.sample("bd_haus", t, amp=1.5, lpf_hz=S.cut(110))
        t += B(0.5)
