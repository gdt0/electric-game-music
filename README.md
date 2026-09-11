# Electric game music, as code

Found on the internet, rendered from source. This repo collects **code-only electronic /
game music** — pieces that exist as *source code*, not audio files — and renders each one
to audio with a small self-contained synth engine, on a headless server with no
SuperCollider and no DAW.

Every piece here is a **Sonic Pi example composition** ([sonic-pi-net/sonic-pi](https://github.com/sonic-pi-net/sonic-pi),
`etc/examples/`): the upstream `.rb` files are the "album", the `tracks/*.py` files are
faithful ports of those patterns onto this repo's engine, and `audio/*.mp3` are the renders.

## Tracks

| Track | Style | Tempo | Source (code) | Audio |
|---|---|---|---|---|
| **Rerezzed** | Tron: Legacy electro, bitcrushed gliding dsaw | 60 | [`sorcerer/rerezzed.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/sorcerer/rerezzed.rb) | `audio/rerezzed.mp3` |
| **Tron Bike** | dark drone / light-cycle pulse | — | [`magician/tron_bike.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/tron_bike.rb) | `audio/tron_bike.mp3` |
| **Blockgame** | 130 BPM electro game-loop (by DJ_Dave) | 130 | [`algomancer/blockgame.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/algomancer/blockgame.rb) | `audio/blockgame.mp3` |
| **Time Machine** | arcade 32nd-note blips + TB-303 sub | 60 | [`wizard/time_machine.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/wizard/time_machine.rb) | `audio/time_machine.mp3` |
| **Acid** | TB-303 acid rave | 60 | [`magician/acid.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/magician/acid.rb) | `audio/acid.mp3` |
| **Dark Neon** | wobble-bass neon drive | 60 | [`incubation/dark_neon.rb`](https://github.com/sonic-pi-net/sonic-pi/blob/dev/etc/examples/incubation/dark_neon.rb) | `audio/dark_neon.mp3` |

Each `tracks/*.py` header documents exactly what is faithful to the original and what had
to be approximated (there is no SuperCollider here, so Sonic Pi synths like `:dsaw`,
`:tb303`, `:fm`, `:prophet`, `:blade` are re-implemented with oscillators, filters and
envelopes; `beat_stretch` becomes resampling; Sonic Pi's random `.choose`/`.shuffle` is
seeded so renders are reproducible).

## Engine

`engine/synth.py` — ~450 lines, numpy + scipy only:

* notes in **Sonic Pi convention** (`e2` == MIDI 40), and Sonic Pi `cutoff:` values are
  MIDI note numbers, so `S.cut(30)` ≈ 46 Hz while `S.cut(130)` ≈ 15 kHz;
* polyBLEP band-limited saw / pulse / square, plus triangle, sine, noise;
* ADSR envelopes and portamento (`S.glide_freq`, i.e. Sonic Pi `note_slide`);
* RBJ biquad low/high-pass with **time-varying cutoff** (`S.lpf_curve`) — used for
  filter sweeps, TB-303 squelch and wobble bass;
* FX: `echo`, `reverb` (convolution), `bitcrush`, `slicer`, `wobble`, `compress`;
* the Sonic Pi sample library (`samples/*.flac`, fetched from the upstream repo) played
  with `rate` / `start` / `finish` / `lpf` / `hpf`, and a `beat_stretch_sample` helper.

## Render it yourself

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install scipy            # numpy + ffmpeg required too
.venv/bin/python render.py             # all tracks -> audio/*.wav + audio/*.mp3
.venv/bin/python render.py acid        # one track
.venv/bin/python render.py --list      # track table
.venv/bin/python test_smoke.py         # engine self-test
.venv/bin/python tools/analyze.py audio/acid.wav   # per-4s loudness / spectrum report
```

## Credits and licensing

* Example compositions: the Sonic Pi project — `etc/examples/` in
  [sonic-pi-net/sonic-pi](https://github.com/sonic-pi-net/sonic-pi) (MIT-licensed repo).
  `rerezzed`, `tron_bike`, `time_machine`, `acid`, `dark_neon` are by **Sam Aaron**;
  `blockgame` is by **DJ_Dave**. `rerezzed` is an arrangement of Daft Punk's *Rerezzed*
  (*Tron: Legacy*) — the underlying composition belongs to its authors.
* Samples in `samples/` are the Sonic Pi sample library, redistributed here for the same
  educational, personal use.
* Renders in `audio/` are approximations made for listening/study, not official releases.
* Engine and ports: MIT.
