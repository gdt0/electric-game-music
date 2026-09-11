"""Smoke test: verify pitch maths, synthesis, FX, samples all produce sound."""
import numpy as np
from engine import synth as S

# --- pitch sanity ---
assert S.midi("e2") == 40 and S.midi(":b1") == 35 and S.midi("c4") == 60
assert abs(S.hz("a4") - 440.0) < 1e-6, S.hz("a4")
assert abs(S.hz("e2") - 82.4069) < 0.01, S.hz("e2")
print("pitch ok | e2 =", round(S.hz("e2"), 2), "Hz | cut(130) =", round(S.cut(130)), "Hz | cut(30) =", round(S.cut(30), 1), "Hz")

# --- oscillators ---
n = S.SR  # 1 second
for name, sig in [("saw", S.saw(220, n)), ("pulse", S.pulse(220, n, 0.3)),
                  ("square", S.square(220, n)), ("tri", S.tri(220, n)),
                  ("sine", S.sine(220, n)), ("noise", S.noise(n))]:
    assert len(sig) == n and np.abs(sig).max() > 0.1, name
print("oscillators ok")

# --- filters ---
x = S.saw(220, n)
lo = S.lpf(x, 400, q=3.0)
hi = S.hpf(x, 2000)
assert np.abs(lo).max() > 0.01 and np.abs(hi).max() > 0.01
cur = np.linspace(S.cut(40), S.cut(120), n)
filt = S.lpf_curve(x, cur, q=4.0)
assert np.abs(filt).max() > 0.01
print("filters ok | lpf rms", round(float(np.sqrt((lo**2).mean())), 4))

# --- fx ---
e = S.echo(S.pulse(440, S.SR // 4), 0.25, feedback=0.5, mix=0.5)
assert len(e) > S.SR // 4
r = S.reverb(S.sine(330, S.SR), room=0.8, mix=0.4)
assert len(r) >= S.SR and np.abs(r).max() > 0.05
b = S.bitcrush(S.sine(220, n), bits=6, hold=3)
sl = S.slicer(S.saw(110, n), 0.25)
w = S.wobble(S.saw(55, n), rate_hz=2.0, cutoff_min=S.cut(50), cutoff_max=S.cut(100))
print("fx ok | echo", len(e), "| reverb rms", round(float(np.sqrt((r**2).mean())), 4),
      "| crush rms", round(float(np.sqrt((b**2).mean())), 4),
      "| wobble rms", round(float(np.sqrt((w**2).mean())), 4))

# --- samples ---
for s in ["bd_haus", "bd_tek", "drum_bass_hard", "drum_snare_hard", "drum_cymbal_closed",
          "drum_splash_soft", "elec_blip", "elec_plip", "elec_cymbal",
          "loop_industrial", "loop_garzul", "bass_trance_c", "ambi_lunar_land"]:
    d = S.SAMPLES.duration(s)
    assert d > 0.01, s
    print(f"  sample {s:20s} {d:6.2f}s")

# --- build a 4s test mix and write it ---
mix = S.Mix(4.0)
B = lambda b: S.beats(132, b)
for i in range(8):
    mix.sample("bd_haus", B(i), amp=1.4)
    if i % 2 == 1:
        mix.sample("drum_snare_hard", B(i), rate=1.5, amp=0.5)
    mix.sample("drum_cymbal_closed", B(i + 0.5), amp=0.3, pan=0.3 if i % 2 else -0.3)
lead = S.pulse(S.hz("a3"), int(S.SR * 0.4), width=0.25) * S.env(int(S.SR * 0.4), 0.01, 0.15)
lead = S.echo(lead, S.beats(132, 0.75), feedback=0.45, mix=0.5)
for i in range(5):
    mix.add(lead, B(i * 1.5), gain=0.35, pan=-0.2 + 0.1 * i)
sub = S.saw(S.hz("a1"), int(B(4))) * S.env(int(B(4)), 0.02, 0.3)
mix.add(S.lpf(sub, S.cut(70), q=2.0), 0.0, gain=1.2)
mix.sample("loop_industrial", B(1), rate=1.0, amp=1.2, lpf_hz=S.cut(110))

out = mix.out()
S.write_wav("/tmp/smoke.wav", out)
print("mix ok | peak", round(float(np.abs(out).max()), 3),
      "| rms", round(float(np.sqrt((out ** 2).mean())), 4))
print("SMOKE TEST PASSED")
