"""
synth.py — small software-synth / sequencer engine for rendering
code-composed electronic + game music to 44.1 kHz stereo WAV.

Only numpy + scipy (biquad filtering). Samples are decoded with ffmpeg.

Sonic Pi compatibility notes
----------------------------
* Note names follow the Sonic Pi convention (`c4` == MIDI 60, `a4` == 440 Hz).
* `cutoff` values are MIDI note numbers, exactly like Sonic Pi (`cut(30)` low,
  `cut(130)` wide open) — use the `cut()` helper to convert to Hz.
* `sleep`/`beat` units are quarter notes at the track tempo, like Sonic Pi.
"""
from __future__ import annotations

import os
import subprocess
import wave

import numpy as np
from scipy.signal import fftconvolve, lfilter

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.normpath(os.path.join(HERE, "..", "samples"))
CACHE_DIR = os.path.join(SAMPLES_DIR, ".cache")

_NOTE_TABLE = {
    "c": 0, "cs": 1, "db": 1, "d": 2, "ds": 3, "eb": 3, "e": 4, "f": 5,
    "fs": 6, "gb": 6, "g": 7, "gs": 8, "ab": 8, "a": 9, "as": 10, "bb": 10, "b": 11,
}
_SCALES = {
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}
_CHORDS = {
    "minor": [0, 3, 7], "m7": [0, 3, 7, 10], "minor7": [0, 3, 7, 10],
    "major": [0, 4, 7], "major7": [0, 4, 7, 11], "dim": [0, 3, 6],
    "sus4": [0, 5, 7], "7": [0, 4, 7, 10], "minor9": [0, 3, 7, 10, 14],
}


# --------------------------------------------------------------------------- #
# pitch helpers
# --------------------------------------------------------------------------- #
def midi(note) -> float:
    """`e2` / `:e2` / 40 -> MIDI note number (Sonic Pi convention: c4 == 60)."""
    if isinstance(note, (int, float, np.integer, np.floating)):
        return float(note)
    s = str(note).strip().lower().lstrip(":")
    i = 0
    while i < len(s) and s[i].isalpha():
        i += 1
    letter, octave = s[:i], s[i:]
    if letter not in _NOTE_TABLE:
        raise ValueError(f"bad note name: {note!r}")
    return (int(octave) + 1) * 12 + _NOTE_TABLE[letter]


def hz(note) -> float:
    """MIDI note (or note name) -> frequency in Hz."""
    return float(440.0 * 2.0 ** ((midi(note) - 69.0) / 12.0))


def cut(midi_cutoff: float) -> float:
    """Sonic Pi `cutoff:` (MIDI note number) -> Hz, clamped to a sane range."""
    return float(np.clip(440.0 * 2.0 ** ((float(midi_cutoff) - 69.0) / 12.0), 20.0, SR * 0.45))


def scale(root, kind: str = "minor_pentatonic", octaves: int = 1):
    base = midi(root)
    out = []
    for o in range(octaves):
        out += [base + i + 12 * o for i in _SCALES[kind]]
    return out


def chord(root, kind: str = "minor"):
    base = midi(root)
    return [base + i for i in _CHORDS[kind]]


def beats(bpm: float, b: float) -> float:
    """Beats (quarter notes) -> seconds at the given tempo."""
    return b * 60.0 / bpm


def pick(seq, rng):
    return seq[rng.integers(0, len(seq))]


# --------------------------------------------------------------------------- #
# oscillators (polyBLEP band-limited saw / pulse)
# --------------------------------------------------------------------------- #
def _freq_array(freq, n: int) -> np.ndarray:
    if np.ndim(freq) == 0:
        return np.full(n, float(freq))
    f = np.asarray(freq, dtype=float)
    if len(f) != n:
        f = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(f)), f)
    return f


def _polyblep(t: np.ndarray, dt: np.ndarray) -> np.ndarray:
    dt = np.maximum(dt, 1e-9)
    y = np.zeros_like(t)
    m = t < dt
    u = t[m] / dt[m]
    y[m] = u + u - u * u - 1.0
    m2 = t > 1.0 - dt
    u2 = (t[m2] - 1.0) / dt[m2]
    y[m2] = u2 * u2 + u2 + u2 + 1.0
    return y


def _phase(freq, n: int, phase0: float = 0.0):
    f = _freq_array(freq, n)
    ph = phase0 + np.cumsum(f) / SR
    return f, ph - np.floor(ph)


def saw(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    f, t = _phase(freq, n, phase0)
    return (2.0 * t - 1.0) - _polyblep(t, f / SR)


def pulse(freq, n: int, width: float = 0.5, phase0: float = 0.0) -> np.ndarray:
    f, t = _phase(freq, n, phase0)
    dt = f / SR
    sig = np.where(t < width, 1.0, -1.0)
    sig = sig + _polyblep(t, dt) - _polyblep(np.mod(t - width, 1.0), dt)
    return sig


def square(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    return pulse(freq, n, 0.5, phase0)


def tri(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    _, t = _phase(freq, n, phase0)
    return 2.0 * np.abs(2.0 * t - 1.0) - 1.0


def sine(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    _, t = _phase(freq, n, phase0)
    return np.sin(2.0 * np.pi * t)


def noise(n: int, rng=None) -> np.ndarray:
    rng = rng or np.random.default_rng()
    return rng.uniform(-1.0, 1.0, n)


# --------------------------------------------------------------------------- #
# envelopes
# --------------------------------------------------------------------------- #
def env(n: int, attack: float = 0.005, release: float = 0.05, decay: float = 0.0) -> np.ndarray:
    e = np.ones(max(n, 1))
    na = min(int(attack * SR), n)
    if na > 1:
        e[:na] = np.linspace(0.0, 1.0, na)
    if decay > 0:
        nd = min(int(decay * SR), n)
        if nd > 0:
            e[:nd] *= np.exp(np.linspace(0.0, -2.3, nd))
    nr = min(int(release * SR), n)
    if nr > 1:
        e[n - nr:] *= np.exp(np.linspace(0.0, -6.9, nr))
    return e


def glide_freq(f_start, f_end, n: int, glide: float) -> np.ndarray:
    """Frequency curve that slides from f_start to f_end over `glide` seconds."""
    ng = max(int(glide * SR), 1)
    if ng >= n:
        return np.linspace(f_start, f_end, n)
    return np.concatenate([np.linspace(f_start, f_end, ng), np.full(n - ng, f_end)])


# --------------------------------------------------------------------------- #
# filters (RBJ biquads; cutoff may be a per-sample curve)
# --------------------------------------------------------------------------- #
def _rbj_lpf(f: float, q: float):
    w0 = 2.0 * np.pi * min(max(f, 15.0), SR * 0.45) / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * max(q, 0.05))
    b = np.array([(1.0 - cw) / 2.0, 1.0 - cw, (1.0 - cw) / 2.0])
    a = np.array([1.0 + alpha, -2.0 * cw, 1.0 - alpha])
    return b / a[0], a / a[0]


def _rbj_hpf(f: float, q: float):
    w0 = 2.0 * np.pi * min(max(f, 15.0), SR * 0.45) / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * max(q, 0.05))
    b = np.array([(1.0 + cw) / 2.0, -(1.0 + cw), (1.0 + cw) / 2.0])
    a = np.array([1.0 + alpha, -2.0 * cw, 1.0 - alpha])
    return b / a[0], a / a[0]


def lpf(x: np.ndarray, cutoff_hz: float, q: float = 0.707) -> np.ndarray:
    b, a = _rbj_lpf(cutoff_hz, q)
    return lfilter(b, a, x)


def hpf(x: np.ndarray, cutoff_hz: float, q: float = 0.707) -> np.ndarray:
    b, a = _rbj_hpf(cutoff_hz, q)
    return lfilter(b, a, x)


def lpf_curve(x: np.ndarray, cutoff_curve, q: float = 0.707, block: int = 512) -> np.ndarray:
    """Time-varying low-pass (cutoff_curve: scalar or per-sample Hz array)."""
    c = _freq_array(cutoff_curve, len(x))
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        seg = x[i:i + block]
        b, a = _rbj_lpf(float(np.mean(c[i:i + block])), q)
        out, zi = lfilter(b, a, seg, zi=zi)
        y[i:i + block] = out
    return y


def hpf_curve(x: np.ndarray, cutoff_curve, q: float = 0.707, block: int = 512) -> np.ndarray:
    c = _freq_array(cutoff_curve, len(x))
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        seg = x[i:i + block]
        b, a = _rbj_hpf(float(np.mean(c[i:i + block])), q)
        out, zi = lfilter(b, a, seg, zi=zi)
        y[i:i + block] = out
    return y


# --------------------------------------------------------------------------- #
# effects
# --------------------------------------------------------------------------- #
def echo(x: np.ndarray, time_s: float, feedback: float = 0.5, mix: float = 0.4) -> np.ndarray:
    """Feed-forward delay: the tail rings past the end of the input."""
    delay = max(int(max(time_s, 0.001) * SR), 1)
    n_taps, g = 1, mix
    while g * feedback > 0.004 and n_taps < 32:
        g *= feedback
        n_taps += 1
    y = np.zeros(len(x) + delay * n_taps)
    y[:len(x)] += x
    g = mix
    for k in range(1, n_taps + 1):
        off = k * delay
        y[off:off + len(x)] += g * x
        g *= feedback
    return y


def reverb(x: np.ndarray, room: float = 0.8, mix: float = 0.3, damp: float = 0.5,
           seed: int = 11) -> np.ndarray:
    dur = 0.15 + 1.6 * float(np.clip(room, 0.05, 1.2))
    n = int(dur * SR)
    t = np.arange(n) / SR
    env_ir = np.exp(-t * (3.0 / dur)) * (1.0 - np.exp(-t / 0.004))
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * env_ir
    ir = lpf(ir, 1800.0 + 7000.0 * (1.0 - float(np.clip(damp, 0, 1))))
    ir /= max(np.abs(ir).max(), 1e-9)
    wet = fftconvolve(x, ir)
    wet /= max(np.abs(wet).max(), 1e-9)
    wet *= max(np.abs(x).max(), 1e-9) * 2.0
    out = np.zeros(max(len(x), len(wet)))
    out[:len(x)] += (1.0 - mix) * x
    out[:len(wet)] += mix * wet
    return out


def bitcrush(x: np.ndarray, bits: int = 8, hold: int = 2) -> np.ndarray:
    y = np.round(np.array(x, dtype=float) * (2 ** (bits - 1))) / (2 ** (bits - 1))
    if hold > 1:
        n = len(y) - len(y) % hold
        y = np.repeat(y[:n].reshape(-1, hold)[:, 0], hold)
        if n < len(x):
            y = np.concatenate([y, np.full(len(x) - n, y[-1] if len(y) else 0.0)])
    return y


def slicer(x: np.ndarray, phase_s: float = 0.25, wave: int = 1, amp: float = 1.0) -> np.ndarray:
    """Sonic Pi-ish `slicer` FX: rhythmic amplitude gating."""
    n = len(x)
    if phase_s <= 0:
        return x
    steps = np.arange(n) / (phase_s * SR)
    frac = np.mod(steps, 1.0)
    if wave == 0:                                  # saw
        g = frac
    elif wave == 2:                                # triangle
        g = 1.0 - np.abs(2.0 * frac - 1.0)
    elif wave == 3:                                # noise
        g = np.random.default_rng(3).uniform(0.0, 1.0, n)
    else:                                          # pulse gate
        g = (frac < 0.5).astype(float)
    return x * ((1.0 - amp) + amp * g)


def wobble(x: np.ndarray, rate_hz: float = 1.0, cutoff_min: float = 300.0,
           cutoff_max: float = 2000.0, wave: int = 0, q: float = 2.0) -> np.ndarray:
    t = np.arange(len(x)) / SR
    p = np.mod(t * rate_hz, 1.0)
    if wave == 0:      # saw
        lfo = p
    elif wave == 2:    # triangle
        lfo = 1.0 - np.abs(2.0 * p - 1.0)
    else:              # sine
        lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * p)
    curve = cutoff_min + (cutoff_max - cutoff_min) * lfo
    return lpf_curve(x, curve, q=q)


def compress(x: np.ndarray, threshold: float = 0.6, ratio: float = 6.0) -> np.ndarray:
    y = np.array(x, dtype=float)
    peak = np.abs(y).max()
    if peak > 0:
        y /= peak
    a = np.abs(y)
    over = a > threshold
    y[over] = np.sign(y[over]) * (threshold + (a[over] - threshold) / ratio)
    return y


def _soft_clip(x: np.ndarray, drive: float = 1.2) -> np.ndarray:
    return np.tanh(x * drive) / np.tanh(drive)


# --------------------------------------------------------------------------- #
# sample bank
# --------------------------------------------------------------------------- #
class SampleBank:
    def __init__(self, directory: str = SAMPLES_DIR):
        self.dir = directory
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._cache: dict[str, np.ndarray] = {}

    def _flac_path(self, name: str) -> str:
        for ext in (".flac", ".wav", ".ogg"):
            p = os.path.join(self.dir, name + ext)
            if os.path.exists(p):
                return p
        raise FileNotFoundError(f"sample not found: {name}")

    def get(self, name: str) -> np.ndarray:
        if name in self._cache:
            return self._cache[name]
        cache_path = os.path.join(CACHE_DIR, name + ".npy")
        if os.path.exists(cache_path):
            x = np.load(cache_path)
        else:
            src = self._flac_path(name)
            raw = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                capture_output=True, check=True).stdout
            x = np.frombuffer(raw, dtype="<f4").astype(np.float64)
            np.save(cache_path, x)
        self._cache[name] = x
        return x

    def duration(self, name: str) -> float:
        return len(self.get(name)) / SR


SAMPLES = SampleBank()


def resample(x: np.ndarray, rate: float) -> np.ndarray:
    if abs(rate - 1.0) < 1e-9:
        return x
    if rate < 0:
        x = x[::-1]
        rate = -rate
    n_out = max(int(len(x) / rate), 1)
    src = np.arange(len(x))
    idx = np.arange(n_out) * rate
    idx = np.clip(idx, 0, len(x) - 1)
    return np.interp(idx, src, x)


# --------------------------------------------------------------------------- #
# mixing bus
# --------------------------------------------------------------------------- #
class Mix:
    """Stereo bus; `add` places a mono fragment at a time offset with panning."""

    def __init__(self, seconds: float):
        self.n = int(seconds * SR)
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)

    def add(self, x: np.ndarray, t: float = 0.0, gain: float = 1.0, pan: float = 0.0):
        if x is None or len(x) == 0:
            return
        i = int(t * SR)
        if i >= self.n:
            return
        x = np.asarray(x, dtype=float)
        m = min(len(x), self.n - i)
        if m <= 0:
            return
        th = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * (np.pi / 4.0)
        self.L[i:i + m] += gain * np.cos(th) * x[:m]
        self.R[i:i + m] += gain * np.sin(th) * x[:m]

    def sample(self, name: str, t: float, rate: float = 1.0, start: float = 0.0,
               finish: float = 1.0, amp: float = 1.0, pan: float = 0.0,
               lpf_hz: float | None = None, hpf_hz: float | None = None,
               gain: float = 1.0) -> np.ndarray:
        s = SAMPLES.get(name)
        a, b = int(start * len(s)), int(finish * len(s))
        seg = s[max(a, 0):max(b, 1)]
        if rate != 1.0:
            seg = resample(seg, rate)
        if lpf_hz:
            seg = lpf(seg, lpf_hz)
        if hpf_hz:
            seg = hpf(seg, hpf_hz)
        self.add(seg, t, gain=gain * amp, pan=pan)
        return seg

    def beat_stretch_sample(self, name: str, t: float, n_beats: float, bpm: float, **kw):
        """Approximate Sonic Pi `beat_stretch` by resampling the sample to length."""
        s = SAMPLES.get(name)
        target = beats(bpm, n_beats)
        rate = (len(s) / SR) / max(target, 1e-3)
        return self.sample(name, t, rate=rate, **kw)

    def out(self, peak: float = 0.92) -> np.ndarray:
        st = np.stack([self.L, self.R])
        m = max(np.abs(st).max(), 1e-9)
        st = _soft_clip(st / m * 1.02)
        st = st / max(np.abs(st).max(), 1e-9) * peak
        return st.astype(np.float32)


def write_wav(path: str, stereo: np.ndarray, sr: int = SR):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = np.clip(stereo.T, -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
