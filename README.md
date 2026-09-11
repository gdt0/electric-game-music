# Electric game music, as code

**Code-only electronic / game music**, found on the internet and rendered from source with
a small self-contained synth engine — on a headless server with no SuperCollider and no DAW.

The album is final: five tracks, each one an upstream piece of *source code* (not an audio
file) that this repo re-implements and renders, plus a seamless loop pack for game/app use.

## Tracks

| Track | Style | Tempo | Length | Source (code) | Audio |
|---|---|---|---|---|---|
| **Rerezzed** | Tron: Legacy electro — one held dsaw step-gliding through a shuffled E-minor-pentatonic list every 0.125 beats, bitcrushed, over the industrial loop + bd_haus | 60 | 40 s | [`sorcerer/rerezzed.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/sorcerer/rerezzed.rb) | `audio/rerezzed.mp3` |
| **Blockgame** | 130 BPM electro game loop (by DJ_Dave) — `bd_tek` kick grid, 3-layer clap, 32nd hats, beep arp with pan sweep, tech-saw bass through slicer + reverb | 130 | 44 s | [`algomancer/blockgame.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/algomancer/blockgame.rb) | `audio/blockgame.mp3` |
| **Cyberpunk** | 40 BPM slowed Amen-break groove — break stretched over 8 beats, gliding tech-saw bass, dsaw arp under reverb + echo, FM bass 16ths | 40 | 48 s | [`2024-03-08_CyberPunk.rb`](https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-03-08_CyberPunk.rb) | `audio/cyberpunk.mp3` |
| **Cyberpunk II** | hypnotic minimal variant — stretched Amen + splash, tech-saw bass sliding one step per beat, doubled by a quiet dpulse layer | 60 | 48 s | [`2024-01-20_cyberpunk.rb`](https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-01-20_cyberpunk.rb) | `audio/cyberpunk_2.mp3` |
| **E1M1 "At Doom's Gate"** | DOOM (1993) — the full transposed note array at 225 BPM, driven lead (tanh saturation) doubled an octave down, double-kick backbeat | 225 | 99 s | [`doom.ino`](https://github.com/robsoncouto/arduino-songs/blob/master/doom/doom.ino) | `audio/doom_e1m1.mp3` |

Each `tracks/*.py` docstring states exactly what is faithful to the upstream code and what
had to be approximated: without SuperCollider, Sonic Pi synths (`:dsaw`, `:tech_saws`,
`:fm`, `:pulse`, `:beep`) are rebuilt from oscillators, filters and envelopes;
`beat_stretch` becomes resampling; `note_slide` / `cutoff_slide` become per-sample
frequency / cutoff curves; and Sonic Pi's random `.choose` / `.shuffle` / `rrand` are
seeded so every render is reproducible. For the Arduino tune the note data is untouched
(`tools/arduino_songs.py` parses the `NOTE_*` Hz defines and divider durations) — the drum
groove is an addition by this project, since those sketches are single-voice.

## Seamless loops (`loops/`)

Every track is also rendered as a **seamless, exactly-barred loop** for games and apps:
`loops/<name>.mp3` + `loops/manifest.json`.

```bash
python3 tools/loops.py            # render/refresh the loop pack
python3 tools/loops.py blockgame  # one loop
python3 tools/loops.py --check    # seam-quality table
```

A track is rendered for `loop_length + 3 s`; everything after the loop end (reverb tails,
echo spill, drum decay) is added back onto the loop start, so the end flows into the start
exactly as the music continues. `manifest.json` gives, per loop, its `bpm`, `loop_beats`,
`loop_seconds`, exact sample count, `seam_jump_ratio` (seam discontinuity ÷ 99.5th
percentile of sample-to-sample steps — under 1.0 means the seam is gentler than the
signal's own motion) and the upstream source URL.

| Loop | Cycle | Length | Seam |
|---|---|---|---|
| blockgame | 16 beats | 7.38 s | 0.15× |
| rerezzed | 8 beats | 8.00 s | 0.01× |
| cyberpunk_2 | 16 beats | 16.00 s | 0.00× |
| cyberpunk | 16 beats @ 40 BPM | 24.00 s | 0.00× |
| doom_e1m1 | whole tune | 96.80 s | 0.01× |

Engines should use the PCM file (`loops/<name>.wav`, gitignored, regenerated locally):
mp3 encoders add their own padding. **Blockgame's loop is the one wired into the Pinglish
app** (see `docs/pinglish.md`).

## Engine

`engine/synth.py` — numpy + scipy only:

* Sonic Pi note convention (`e2` == MIDI 40) and Sonic Pi `cutoff:` values as MIDI note
  numbers (`S.cut(30)` ≈ 46 Hz … `S.cut(130)` ≈ 15 kHz);
* polyBLEP band-limited saw / pulse / square, plus triangle, sine, noise;
* ADSR envelopes, portamento (`S.glide_freq`) and time-varying filters (`S.lpf_curve`,
  `S.hpf_curve`) for filter sweeps and squelch;
* FX: `echo`, `reverb` (convolution), `bitcrush`, `slicer`, `wobble`, `compress`;
* the Sonic Pi sample library (`samples/*.flac`, fetched from upstream) with `rate`,
  `start` / `finish`, `lpf` / `hpf`, plus `beat_stretch_sample`.

## Render it yourself

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install scipy            # numpy + ffmpeg required too
.venv/bin/python render.py             # all tracks -> audio/*.wav + audio/*.mp3
.venv/bin/python render.py blockgame   # one track
.venv/bin/python render.py --list      # track table
.venv/bin/python test_smoke.py         # engine self-test
.venv/bin/python tools/analyze.py audio/blockgame.wav   # loudness / spectrum report
```

## Credits and licensing

* **Sam Aaron** — `rerezzed` (Sonic Pi example library); it is an arrangement of Daft
  Punk's *Rerezzed* (*Tron: Legacy*).
* **DJ_Dave** — `blockgame` (Sonic Pi "Algomancer" example).
* **ikemura23** — `cyberpunk`, `cyberpunk_2` ([sonic-pi-code](https://github.com/ikemura23/sonic-pi-code)).
* **robsoncouto** — the DOOM transcription ([arduino-songs](https://github.com/robsoncouto/arduino-songs));
  *E1M1 "At Doom's Gate"* is composed by Robert "Bobby" Prince (id Software, 1993).
* `samples/` are the Sonic Pi sample library, included for the same personal, educational
  use. Renders are approximations for listening and study — not official releases.
* Engine, tools and port code: MIT (`LICENSE`).
