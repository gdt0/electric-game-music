"""
vampire_killer — Castlevania (NES): "Vampire Killer", the Stage 1 theme.

Source (found on the internet, note data as C code):
    https://github.com/robsoncouto/arduino-songs/blob/master/vampirekiller/vampirekiller.ino
    local copy: sources/arduino-songs/vampirekiller.ino
    composition by Kinuyo Yamashita / Satoe Terashima (Konami, 1986); the Arduino
    note array is robsoncouto's transcription.

Faithful parts: the sketch's whole note array is rendered unchanged — every frequency
(the NOTE_* defines are literal Hz) and every divider / dotted-note duration, at the
sketch's own tempo (130 BPM).

Additions by this project (the .ino is a single-voice buzzer tune):
    * pulse "chip" lead + sub-octave voice (the classic two-channel texture);
    * a rock backbeat built from Sonic Pi drum samples.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.arduino_songs import parse_ino  # noqa: E402
from tracks import _chiptune as C  # noqa: E402

NAME = "vampire_killer"
TITLE = "Vampire Killer (Castlevania) — robsoncouto/arduino-songs"
SOURCE = "https://github.com/robsoncouto/arduino-songs/blob/master/vampirekiller/vampirekiller.ino"

BPM, _EVENTS = parse_ino(C.ino_path("vampirekiller"))
LENGTH = 62.0


def build(mix):
    C.render_melody(mix, _EVENTS, BPM, gain=0.42, duty=0.5, sub=True, drive=0.35,
                    vibrato=0.005, release=0.045)
    C.backbeat(mix, 0.0, LENGTH, BPM, style="rock", kick_amp=0.5, snare_amp=0.3,
               hat_amp=0.085, hat_every=0.5)
    C.crash(mix, 0.0, amp=0.24)
    C.crash(mix, 30.0, amp=0.16)
