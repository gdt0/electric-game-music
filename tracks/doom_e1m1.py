"""
doom_e1m1 — DOOM (1993): E1M1 "At Doom's Gate".

Source (found on the internet, note data as C code):
    https://github.com/robsoncouto/arduino-songs/blob/master/doom/doom.ino
    local copy: sources/arduino-songs/doom.ino
    composition by Robert "Bobby" Prince (id Software, 1993); the Arduino note array is
    robsoncouto's transcription.

Faithful parts: the whole note array of the sketch, at its own tempo (225 BPM) —
frequencies are the literal Hz values from the NOTE_* defines, durations the sketch's
divider / dotted-note values.

Additions by this project: the lead is driven (tanh saturation) for the palm-muted
guitar feel, doubled an octave down, with a fast double-kick punk backbeat — the .ino
itself is melody only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.arduino_songs import parse_ino  # noqa: E402
from tracks import _chiptune as C  # noqa: E402

NAME = "doom_e1m1"
TITLE = "E1M1 'At Doom's Gate' (DOOM) — robsoncouto/arduino-songs"
SOURCE = "https://github.com/robsoncouto/arduino-songs/blob/master/doom/doom.ino"

BPM, _EVENTS = parse_ino(C.ino_path("doom"))
LENGTH = 99.0


def build(mix):
    C.render_melody(mix, _EVENTS, BPM, gain=0.44, duty=0.42, sub=True, drive=0.85,
                    vibrato=0.006, release=0.035, sub_gain=0.5)
    C.backbeat(mix, 0.0, LENGTH, BPM, style="double", kick_amp=0.46, snare_amp=0.26,
               hat_amp=0.055, hat_every=0.5)
    C.crash(mix, 0.0, amp=0.26)
    C.crash(mix, 48.0, amp=0.18)
