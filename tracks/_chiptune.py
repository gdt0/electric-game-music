"""
_chiptune.py — shared helpers for rendering `robsoncouto/arduino-songs` tunes.

Those .ino sketches are single-voice buzzer tunes: a stream of (frequency, divider)
pairs at a fixed tempo. This module renders them as a chiptune-ish arrangement:

    lead   — band-limited pulse with light vibrato (and optional drive)
    sub    — the same line an octave down, the classic two-channel chip texture
    beat   — optional backbeat built from Sonic Pi drum samples

The drum groove is an *addition* by this project (the .ino files contain melody only);
the note data itself is untouched.
"""
from __future__ import annotations

import os

import numpy as np

from engine import synth as S
from tools.arduino_songs import parse_ino

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ino_path(name: str) -> str:
    return os.path.join(ROOT, "sources", "arduino-songs", f"{name}.ino")


def lead_voice(freq_hz: float, seconds: float, duty: float = 0.5, sub: bool = True,
               vibrato: float = 0.004, vibrato_hz: float = 5.5, drive: float = 0.0,
               attack: float = 0.004, release: float = 0.05, detune: float = 0.004,
               sub_gain: float = 0.42) -> np.ndarray:
    n = max(int(seconds * S.SR), 16)
    t = np.arange(n) / S.SR
    f = freq_hz * (1.0 + vibrato * np.sin(2.0 * np.pi * vibrato_hz * t + (freq_hz % 7.0)))
    sig = 0.72 * S.pulse(f, n, width=duty)
    if detune:
        sig += 0.28 * S.pulse(f * (1.0 + detune), n, width=max(0.5 - duty, 0.05), phase0=0.5)
    if sub:
        sig += sub_gain * S.pulse(f / 2.0, n, width=0.5, phase0=0.25)
    if drive:
        sig = np.tanh(sig * (1.0 + 4.0 * drive)) / np.tanh(1.0 + 4.0 * drive)
    return sig * S.env(n, attack, min(release + 0.02, max(seconds * 0.3, 0.02)))


def render_melody(mix, events, bpm: float, gate: float = 0.9, gain: float = 0.5,
                  pan: float = 0.0, **voice_kw) -> float:
    """Place every (freq, beats) event; returns the end time in seconds."""
    t = 0.0
    for freq, beats_ in events:
        dur = S.beats(bpm, beats_)
        if freq:
            mix.add(lead_voice(float(freq), max(dur * gate, 0.02), **voice_kw), t, gain=gain, pan=pan)
        t += dur
    return t


def backbeat(mix, start_s: float, end_s: float, bpm: float, style: str = "rock",
             kick_amp: float = 0.5, snare_amp: float = 0.3, hat_amp: float = 0.09,
             hat_every: float = 0.5, snare_beats=(1, 3), hat_delay: float = 0.0) -> None:
    """Add a 4/4 drum groove (Sonic Pi samples) between two times."""
    beat = S.beats(bpm, 1)
    i = 0
    t = start_s
    while t < end_s - 1e-6:
        b = i % 4
        if b in (0, 2):
            mix.sample("drum_bass_hard", t, amp=kick_amp, pan=0.0)
            if style == "double":
                mix.sample("drum_bass_hard", t + beat * 0.75, amp=kick_amp * 0.65)
            elif style == "rock":
                mix.sample("drum_bass_hard", t + beat * 0.5, amp=kick_amp * 0.5)
        if b in snare_beats:
            mix.sample("drum_snare_hard", t, amp=snare_amp, pan=-0.08)
            mix.sample("drum_snare_hard", t, rate=1.25, amp=snare_amp * 0.45, pan=0.14)
        if hat_amp > 0 and hat_every > 0:
            off = hat_delay
            k = 0
            while off < 1.0:
                mix.sample("drum_cymbal_closed", t + beat * off, amp=hat_amp,
                           pan=0.3 if k % 2 else -0.3)
                off += hat_every
                k += 1
        t += beat
        i += 1


def crash(mix, t: float, amp: float = 0.22, pan: float = 0.0) -> None:
    mix.sample("drum_splash_soft", t, rate=1.4, amp=amp, pan=pan)
    mix.sample("drum_splash_soft", t, rate=1.2, amp=amp * 0.8, pan=-pan)
