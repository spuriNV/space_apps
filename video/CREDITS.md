# Credits: CropLytics 30-second commercial (v1)

File: `video/croplytics-30s-v1.mp4` (captions also in `video/croplytics-30s-v1.srt`). Built by `video/scripts/build.mjs` from the sources below. No AI-generated images or video are used anywhere in the spot.

## Synthetic audio disclosure (Space Apps 2026 "SI" rule)

The voice-over in v1 is **synthetic speech**: a placeholder made with Microsoft Edge text-to-speech (`edge-tts`, voice `en-US-AndrewNeural`, rate -4%). It will be replaced by an ElevenLabs voice (also synthetic) or a human read. The same statement is in the MP4's `comment` and `description` metadata and on the end card ("Voice-over is synthetic (text-to-speech)").

Script (54 words): "Every season, the same question. What do I plant next? CropLytics reads your field with NASA Earth data. From the crop down to the groundwater. What happened here. What's likely this winter. What a switch costs: about two acre-feet, not five. One page for your adviser, checked against OpenET. CropLytics. Your field. Your call."

## Live-action stock footage (farmer scenes)

All from Mixkit, each item checked as **"Mixkit Stock Video Free License"** (commercial and personal use, no attribution required; items under Mixkit's *Restricted* licence, which forbids commercial use, were rejected). Licence: <https://mixkit.co/license/#videoFree>. Credited anyway. All people shown are adults; none is identifiable as a real farmer, and no footage implies an endorsement.

| Shot | Clip | Author (Mixkit contributor) | Source | Used |
|---|---|---|---|---|
| 2, looking out over the field | A cowboy standing in a field at sunset (#521) | franklandgrave | <https://mixkit.co/free-stock-video/a-cowboy-standing-in-a-field-at-sunset-521/> | 6.0–8.0 s, slow push-in |
| 3, thoughtful hand to the hat | Rancher looking around on a ranch at sunset (#42382) | Mixkit | <https://mixkit.co/free-stock-video/rancher-looking-around-on-a-ranch-at-sunset-42382/> | 0.6–2.1 s |
| 4, phone in a dry field | Man checks his smartphone after training (#594) | franklandgrave | <https://mixkit.co/free-stock-video/man-checks-his-smartphone-after-training-594/> | 2.0–3.0 s, cropped to the hands and phone |
| 6, laptop at the table | Senior man using laptop at home (#32139) | azhorov | <https://mixkit.co/free-stock-video/senior-man-using-laptop-at-home-32139/> | 1.1–1.85 s (720p source, upscaled) |

Grade on the stock shots only: warmer colour temperature, slightly lower saturation, lifted blacks (`colortemperature`, `eq`, `curves` in ffmpeg).

Considered and not used: Mixkit #7734 "Sunset while a tractor works" and #15088 "Tractor driving along a dusty field" (both Free licence; the tractor opener was dropped to keep the farmer part short); #38427, #16033, #5416 and #48954 (Restricted licence, not usable commercially).

## NASA imagery

| Shot | Image | Credit |
|---|---|---|
| 1, opener | ISS astronaut photograph ISS062-E-81143, 4 March 2020, Sacramento Valley with the Sutter Buttes and the Sacramento River (400 mm lens, Nikon D5) | Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center. <https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?mission=ISS062&roll=E&frame=81143> |

The photo is cropped to 16:9 and its contrast and saturation are raised to cut the atmospheric haze. No NASA insignia, logotype or seal appears anywhere in the spot; "NASA Space Apps Challenge 2026" and "NASA Earth data" are plain text.

## App footage

Real screen recordings of the live app <https://croplytics-app.onrender.com>, recorded on 15 Nov 2026 after the frontend redesign (commits 40fcbed and 885f57d) was live, with live API data (the recorder refuses the app's example-data fallback):
- Shot 5 (phone): Safari on an iPhone 15 simulator (iOS 17.5), driven by `video/scripts/record-phone.sh`; the device frame is drawn in the edit.
- Shots 7–11 (laptop): Chrome at 1600×900 CSS px (1920×1080 device px), recorded with Chrome's screencast by `video/scripts/record-laptop.mjs`.

The 2022 row in shot 8 has a thin yellow outline added in the page for the recording. Everything else is the app as served. The satellite basemap in the recordings is Esri World Imagery: "Basemap imagery: Esri, Maxar and contributors". Data named on screen: NASA HLS (Landsat and ESA Sentinel-2), NASA GPM IMERG, NASA GRACE-FO, NASA POWER, NOAA CPC outlooks, CDEC reservoir storage, and OpenET (the comparison).

## Music

"Dreaming Big" by Ahjay Stelino, Mixkit (track #31), **Mixkit Stock Music Free License** (commercial use, no attribution required). <https://mixkit.co/free-stock-music/> · file <https://assets.mixkit.co/music/31/31.mp3>. Used from 1:15 to its ending, ducked about 9 dB under the voice.

## Fonts

Zilla Slab (Typotheque for Mozilla) and Libre Franklin (Impallari Type), both SIL Open Font License 1.1, from Google Fonts (<https://github.com/google/fonts>). Files and licences in `video/fonts/`.
