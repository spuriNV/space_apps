# CropLytics 30-second demo, v5

`croplytics-30s-v5.mp4` (+ `.srt`): 1920x1080, 24 fps, 717 frames (29.875 s), about -16 LUFS. Not committed or pushed (user freeze); source is in `/home/caiden/nasa/video5/`.

## Script (VO spoken by Kokoro `am_adam`, speed 1.0; line 1 at 0.93x, line 7 at 0.97x)
| # | Time | Screen (real recordings of croplytics.xyz) | VO / caption |
|---|---|---|---|
| 1 | 0.0-5.75 | ISS photo ISS062-E-81143 with slow push, cross to the example field in 3D at 2022 (brown, bare) | "2022. The water ran short, and this Colusa rice field sat bare all year." |
| 2 | 5.75-9.5 | Pick: click "Open the example"; map flies to the field | "What should it grow next? CropLytics starts with the real field." |
| 3 | 9.5-13.45 | 3D year, Replay ten years (squares rise), hold on 2022 going brown | "Ten years of NASA satellite passes show how it's really farmed." |
| 4 | 13.45-16.9 | Now: the This week strip animating in | "This week: rain, crop water, and whether you can get on the ground." |
| 5 | 16.9-20.65 | Compare: switch rotation, water bars slide against the limit line | "Compare rotations, and see which still fit a dry year's water." |
| 6 | 20.65-24.7 | First Nations lands layer, click Rumsey Indian Rancheria, Nation panel, funding list | "First Nations farmers get the same tools, and the funding to match." |
| 7 | 24.7-29.9 | End card: wordmark, "Better rotations. Less water.", NASA Space Apps 2026 · Field Shift, credits, "Voice-over is AI-generated (Kokoro TTS)." | "CropLytics. Plan next season with NASA data." |

Crossfades 0.35 s; gentle 1.0 to 1.05-1.14 zoom/pan per clip; captions in a paper box (Libre Franklin) synced to the VO sentences; a generated ambient pad (ffmpeg sine + pink noise) ducked under the VO. AI disclosure: end card and MP4 `comment` metadata.

## Pipeline (all in `/home/caiden/nasa/video5/`)
- `tts.py`: Kokoro (kokoro-onnx, models in `models/`, from the kokoro-onnx model-files-v1.0 release) writes `vo/t1.wav`..`t7.wav` and `vo/timings.json`. `uv run --with kokoro-onnx --with soundfile python tts.py am_adam 1.0 vo`.
- `rec.py <beat>`: headed Chromium on Xvfb (`:140`, 1920x1920 area) captured with ffmpeg x11grab. The page clock is slowed K-fold (injected `performance.now`/rAF/timer warp + CDP animation rate) and every (1.25 K)-th frame is kept (`prep.sh`) so software-WebGL animations play smoothly at 24 fps. Smooth CSS cursor dot with click ripple. Beats: pick, year, week, compare, nation (`runall4.sh`).
- `text.py`: captions and end card rendered to PNG with Chromium. `audio.sh`: VO + pad + ducking + loudnorm. `spec.py` / `build.py`: edit and mux.

## Swapping in ElevenLabs lines
Put `t1.wav`..`t7.wav` in a folder (same line order, mono or stereo, any rate), then `VO_DIR=/path ./audio.sh && python3 build.py`. Lines must fit their slots (starts in `cfg.json` `vo_start`: 0.15, 5.9, 9.65, 13.6, 17.05, 20.8, 24.85 s; each line has about 3.4-5.6 s). Caption timing comes from `vo/timings.json`: re-run `tts.py`-style timing or edit it for the new takes, then `python3 text.py` before `build.py`. Remove "Kokoro" from the end card and metadata if the voice changes.

## Voice options
`am_adam` (chosen: slightly quicker, fits 30 s), `am_michael` (warmer but about 2.4 s longer in total, would need faster speed), `am_fenrir` (shortest). Chosen by timing; not auditioned by ear.

## Known gaps
- Live app header shows an English/Espanol toggle overlapping the "Print for your adviser" step label (the app's own state on 15 Nov 2026).
- Click ripple is subtle; cursor is visible.
