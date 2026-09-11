# Electric game music, as code

Found on the internet, rendered from source. This repo collects **code-only electronic /
game music** — tunes that exist as *source code* rather than audio files — and renders
each one to audio with a small self-contained synth engine, on a headless server with no
SuperCollider and no DAW.

Three upstream code libraries are represented:

| Source | What it is | Tracks here |
|---|---|---|
| [sonic-pi-net/sonic-pi](https://github.com/sonic-pi-net/sonic-pi) `etc/examples/` | the Sonic Pi example library (synth/pattern live-code) | Rerezzed, Tron Bike, Blockgame, Time Machine, Acid, Dark Neon |
| [ikemura23/sonic-pi-code](https://github.com/ikemura23/sonic-pi-code) | one live-coder's Sonic Pi songbook | Cyberpunk, Cyberpunk II |
| [robsoncouto/arduino-songs](https://github.com/robsoncouto/arduino-songs) | buzzer tunes as Arduino C note arrays | Vampire Killer, Bloody Tears, DOOM E1M1 |

## Tracks

| Track | Style | Tempo | Length | Source (code) | Audio |
|---|---|---|---|---|---|
| **Rerezzed** | Tron: Legacy electro, bitcrushed gliding dsaw | 60 | 40 s | [`sorcerer/rerezzed.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/sorcerer/rerezzed.rb) | `audio/rerezzed.mp3` |
| **Tron Bike** | dark light-cycle drone, sliding chord tones | 60 | 36 s | [`magician/tron_bike.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/tron_bike.rb) | `audio/tron_bike.mp3` |
| **Blockgame** | 130 BPM electro game loop (by DJ_Dave) | 130 | 44 s | [`algomancer/blockgame.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/algomancer/blockgame.rb) | `audio/blockgame.mp3` |
| **Time Machine** | arcade 32nd-note blips + TB-303 sub | 60 | 44 s | [`wizard/time_machine.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/wizard/time_machine.rb) | `audio/time_machine.mp3` |
| **Acid** | TB-303 acid rave | 60 | 36 s | [`magician/acid.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/acid.rb) | `audio/acid.mp3` |
| **Dark Neon** | wobble-bass neon drive | 60 | 40 s | [`incubation/dark_neon.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/incubation/dark_neon.rb) | `audio/dark_neon.mp3` |
| **Cyberpunk** | 40 BPM slowed Amen-break cyberpunk groove | 40 | 48 s | [`2024-03-08_CyberPunk.rb`](https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-03-08_CyberPunk.rb) | `audio/cyberpunk.mp3` |
| **Cyberpunk II** | hypnotic minimal variant, sliding tech-saw bass | 60 | 48 s | [`2024-01-20_cyberpunk.rb`](https://github.com/ikemura23/sonic-pi-code/blob/main/2024/2024-01-20_cyberpunk.rb) | `audio/cyberpunk_2.mp3` |
| **Vampire Killer** | Castlevania (NES) stage 1 | 130 | 62 s | [`vampirekiller.ino`](https://github.com/robsoncouto/arduino-songs/blob/master/vampirekiller/vampirekiller.ino) | `audio/vampire_killer.mp3` |
| **Bloody Tears** | Castlevania II (NES) | 144 | 108 s | [`bloodytears.ino`](https://github.com/robsoncouto/arduino-songs/blob/master/bloodytears/bloodytears.ino) | `audio/bloody_tears.mp3` |
| **E1M1 "At Doom's Gate"** | DOOM (1993), driven lead + double kick | 225 | 99 s | [`doom.ino`](https://github.com/robsoncouto/arduino-songs/blob/master/doom/doom.ino) | `audio/doom_e1m1.mp3` |
| **IDM Breakbeat** | amen-slicing IDM loop (last 1/n of the break, sometimes reversed) | 60 | 40 s | [`magician/idm_breakbeat.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/idm_breakbeat.rb) | `audio/idm_breakbeat.mp3` |
| **Jungle** | 50 BPM distorted + filtered Amen loop | 50 | 48 s | [`illusionist/jungle.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/illusionist/jungle.rb) | `audio/jungle.mp3` |

Every `tracks/*.py` file opens with a docstring stating exactly what is faithful to the
upstream code and what had to be approximated: there is no SuperCollider here, so Sonic Pi
synths (`:dsaw`, `:tb303`, `:fm`, `:prophet`, `:blade`, `:tech_saws`, `:beep`, `:pulse`,
`:dpulse`) are re-implemented from oscillators, filters and envelopes; `beat_stretch`
becomes resampling; `note_slide`/`cutoff_slide` become per-sample frequency / cutoff
curves; and Sonic Pi's random `.choose`/`.shuffle`/`rrand` are seeded so renders are
reproducible. For the Arduino tunes the drum groove is an addition by this project (those
sketches are single-voice buzzer melodies); the note data itself is untouched.

## Seamless loops (`loops/`)

Every track is also rendered as a **seamless, exactly-barred loop** ready to drop into a
game or app: `loops/<name>.mp3` plus `loops/manifest.json`.

```bash
python3 tools/loops.py            # render/refresh the whole loop pack
python3 tools/loops.py jungle     # just one
python3 tools/loops.py --check    # seam quality table
```

How the seam works: a track is rendered for `loop_length + 3 s`, and everything that
happens after the loop end (reverb tails, echo spill, drum decay) is added back onto the
start of the loop — so the loop's end flows into its start the way the music continues.
`manifest.json` records, per loop: `bpm`, `loop_beats`, `loop_seconds`, exact `samples`,
a `seam_jump_ratio` (the discontinuity at the seam divided by the 99.5th percentile of
sample-to-sample steps — below 1.0 means the seam is gentler than the signal's own
motion), and the upstream source URL.

| Loop | Cycle | Length | Seam |
|---|---|---|---|
| jungle | 4 beats | 4.80 s | 0.06× |
| blockgame | 16 beats | 7.38 s | 0.15× |
| idm_breakbeat / rerezzed / tron_bike | 8 beats | 8.00 s | 0.01–0.05× |
| time_machine / dark_neon / cyberpunk_2 | 16 beats | 16.00 s | 0.00–0.24× |
| acid | 18 beats | 18.00 s | 0.08× |
| cyberpunk | 16 beats (40 BPM) | 24.00 s | 0.00× |
| vampire_killer | whole tune | 58.15 s | 0.00× |
| doom_e1m1 | whole tune | 96.80 s | 0.01× |
| bloody_tears | whole tune | 106.35 s | 0.00× |

Game engines should prefer the PCM file (`loops/<name>.wav`, regenerated locally and
gitignored) because mp3 encoders add their own padding; the packaged mp3s are for
listening and sharing.

## Engine

`engine/synth.py` — numpy + scipy only:

* notes in **Sonic Pi convention** (`e2` == MIDI 40) and Sonic Pi `cutoff:` values as MIDI
  note numbers (`S.cut(30)` ≈ 46 Hz … `S.cut(130)` ≈ 15 kHz);
* polyBLEP band-limited saw / pulse / square, plus triangle, sine, noise;
* ADSR envelopes, portamento (`S.glide_freq`) and **time-varying filters**
  (`S.lpf_curve` / `S.hpf_curve`) — used for 303 squelch, filter sweeps and wobble;
* FX: `echo`, `reverb` (convolution), `bitcrush`, `slicer`, `wobble`, `compress`;
* the Sonic Pi sample library (`samples/*.flac`, fetched from upstream) with `rate`,
  `start` / `finish`, `lpf` / `hpf`, plus a `beat_stretch_sample` helper.

Two tools do the heavy lifting for the Arduino tunes:

* `tools/arduino_songs.py` — parses `NOTE_*` frequency defines and divider/dotted-note
  durations straight out of an `.ino` sketch;
* `tracks/_chiptune.py` — chip lead (pulse + sub-octave + optional drive) and a drum
  backbeat helper.

## Render it yourself

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install scipy            # numpy + ffmpeg required too
.venv/bin/python render.py             # every track -> audio/*.wav + audio/*.mp3
.venv/bin/python render.py acid        # one track
.venv/bin/python render.py --list      # track table
.venv/bin/python test_smoke.py         # engine self-test
.venv/bin/python tools/analyze.py audio/acid.wav   # loudness / spectrum report
```

## Credits and licensing

* Sonic Pi example compositions: **Sam Aaron** (`rerezzed`, `tron_bike`, `time_machine`,
  `acid`, `dark_neon`) and **DJ_Dave** (`blockgame`) — `etc/examples/` of
  [sonic-pi-net/sonic-pi](https://github.com/sonic-pi-net/sonic-pi) (MIT repo).
  `rerezzed` is an arrangement of Daft Punk's *Rerezzed* (*Tron: Legacy*).
* **ikemura23** — [`sonic-pi-code`](https://github.com/ikemura23/sonic-pi-code)
  (Cyberpunk, Cyberpunk II).
* **robsoncouto** — [`arduino-songs`](https://github.com/robsoncouto/arduino-songs)
  (transcriptions). The underlying compositions belong to their authors: *Vampire Killer*
  and *Bloody Tears* are Konami (Kinuyo Yamashita / Satoe Terashima / Kenichi Matsubara),
  *E1M1 "At Doom's Gate"* is Robert "Bobby" Prince (id Software).
* Samples in `samples/` are the Sonic Pi sample library, included for the same
  educational, personal use.
* Renders in `audio/` are approximations made for listening and study, not official
  releases. Engine, tools and ports are MIT (see `LICENSE`).
