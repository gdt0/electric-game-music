"""
bloody_tears — Castlevania II: Simon's Quest: "Bloody Tears".

Source (found on the internet, note data as C code):
    https://github.com/robsoncouto/arduino-songs/blob/master/bloodytears/bloodytears.ino
    local copy: sources/arduino-songs/bloodytears.ino
    composition by Kenichi Matsubara (Konami, 1988); the Arduino note array is
    robsoncouto's transcription.

Faithful parts: the full note array at the sketch's tempo (144 BPM), unchanged.

Additions by this project: a softer triangle-ish pulse lead with a sub voice, and a
restrained march backbeat (kick 1/3, light snare 2/4, quarter-note hats) so the melody
stays on top.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.arduino_songs import parse_ino  # noqa: E402
from tracks import _chiptune as C  # noqa: E402

NAME = "bloody_tears"
TITLE = "Bloody Tears (Castlevania II) — robsoncouto/arduino-songs"
SOURCE = "https://github.com/robsoncouto/arduino-songs/blob/master/bloodytears/bloodytears.ino"

BPM, _EVENTS = parse_ino(C.ino_path("bloodytears"))
LENGTH = 108.0


def build(mix):
    C.render_melody(mix, _EVENTS, BPM, gain=0.40, duty=0.35, sub=True, drive=0.15,
                    vibrato=0.0045, release=0.06, sub_gain=0.36)
    C.backbeat(mix, 2.0, LENGTH, BPM, style="rock", kick_amp=0.42, snare_amp=0.24,
               hat_amp=0.06, hat_every=1.0)
    C.crash(mix, 0.0, amp=0.2)
    C.crash(mix, 54.0, amp=0.14)
