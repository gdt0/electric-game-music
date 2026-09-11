"""
arduino_songs.py — parse the note arrays out of `robsoncouto/arduino-songs` .ino files.

Those sketches encode a whole tune as C arrays:

    int tempo = 130;
    int melody[] = { NOTE_E5,16, NOTE_E5,8, NOTE_D5,16, REST,16, NOTE_CS5,-4, ... };

`NOTE_*` are literal frequencies in Hz, the number after each note is the divider
(4 = quarter, 8 = eighth, 16 = sixteenth…), and a *negative* divider means a dotted
note (× 1.5). `REST` (0) is a pause. This module turns all of that into
`[(freq_hz | None, beats), ...]`.

Usage:
    from tools.arduino_songs import parse_ino
    tempo, notes = parse_ino("sources/arduino-songs/doom.ino")
"""
from __future__ import annotations

import re

_NOTE_RE = re.compile(r"(NOTE_[A-Z]+[0-9]|REST)\s*,\s*(-?\d+)")
_DEFINE_RE = re.compile(r"#define\s+(NOTE_[A-Z]+[0-9])\s+(\d+)")
_TEMPO_RE = re.compile(r"int\s+tempo\s*=\s*(\d+)")


def parse_ino(path: str):
    """-> (tempo_bpm, [(freq_hz or None, duration_in_beats), ...])"""
    text = open(path).read()

    freq_map = {name: int(val) for name, val in _DEFINE_RE.findall(text)}
    tempo_match = _TEMPO_RE.search(text)
    tempo = int(tempo_match.group(1)) if tempo_match else 120

    # only look inside the melody[] / notes[] array declaration
    body = text[text.index("melody[]"):] if "melody[]" in text else text
    body = body[: body.index("};")] if "};" in body else body

    notes = []
    for name, divider in _NOTE_RE.findall(body):
        d = int(divider)
        beats = 4.0 / abs(d)
        if d < 0:
            beats *= 1.5                      # dotted note
        if name == "REST":
            notes.append((None, beats))
        else:
            notes.append((float(freq_map[name]), beats))
    return tempo, notes


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        tempo, notes = parse_ino(p)
        total = sum(b for _, b in notes)
        print(f"{p}: tempo={tempo} | {len(notes)} events | {total:.1f} beats "
              f"({total * 60 / tempo:.1f} s) | {sum(1 for f, _ in notes if f)} pitched")
