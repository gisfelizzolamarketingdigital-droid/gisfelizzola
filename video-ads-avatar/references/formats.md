# The five ad formats

`references/avatarhype-library.md` is the source of truth for proven wording — camera movements, voice recipes, accents, gestures, and the "voz en off" action/setting tables all come from there. This file explains how each format maps onto the job config and pipeline script; consult the library for the actual phrases to use when filling in `avatar_descriptor`, `voice_profile`, `camera_realism`, `delivery`, and `visual_override`.

All talking formats (everything except `voiceover`) want **"Single continuous take, no cuts or scene changes"** somewhere in `camera_realism` — the pipeline script appends it automatically if you forget, because Veo tends to insert an unwanted scene cut mid-clip without it (library section B).

## selfie

The avatar is holding their own phone. Base camera line from the library (section B, "El más usado"):

```
camera_realism: "(static camera, no movement) realistic arm movements and subtle micro-movements."
```

Add "she's holding her phone in one hand at arm's length, front camera framing" to `avatar_descriptor` or `camera_realism` for the actual selfie framing. One `characters` entry, one clip per dialogue segment.

## talking_head

Positioned facing the camera, not holding a phone. Use the same base camera line as selfie but without the phone-in-hand framing — reads as more deliberate/produced.

```
camera_realism: "(static camera, no movement) realistic arm movements and subtle micro-movements."
```

or, for a fully locked-off feel: `"Locked-off static shot, camera completely still on a tripod, no movement at all."` (library section B).

## podcast

Single avatar in a podcast-style setting. Not a distinct technique in the library (which only documents multi-person podcast formats) — build it as the same UGC talking-avatar technique with a studio-style setting folded into `avatar_descriptor` (desk, microphone, warm lighting, acoustic panels or bookshelf in the background).

## dual_cast — two people, cut together (matches library's "Podcast · 2 personas")

**This is the technique to use when the user says "dual cast" / "como una entrevista"** — each person is generated *separately* (their own clip, their own voice, camera quiet), then the clips are cut together in order, exactly like real interview editing. This is what the pipeline script already does natively: two `characters` entries, clips alternating `"character": "avatar1"` / `"avatar2"` in speaking order.

Library-proven lines to fold into each character's `avatar_descriptor` or a clip's `delivery`:
- `"She/he is looking to the right/left side of the frame, as if talking to someone sitting next to her/him."` — so it reads as a conversation, not two people talking straight into the void.
- `"Single speaker: only the person from the reference image talks."` — prevents Veo from generating a second voice for someone off-frame.

**Getting a consistent second guest:** don't just flip the first guest's reference image (produces a mirrored, obviously-fake duplicate room). Instead use the library's **"Segundo invitado"** image prompt (section B → Podcast · 2 personas) — it takes the first guest's photo purely as a *setting/style* reference and regenerates the same room from the opposite angle with a completely different person in it:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py generate-image \
  --prompt "<the library's exact Segundo invitado prompt, with [describe a la persona...] filled in>" \
  --images /path/to/first_guest_ref.jpg \
  --output-dir /path/to/output/<campaign>/ \
  --filename second_guest.png
```

Then use `second_guest.png` as that second character's own reference photo in `avatar_images`. Image generation is very cheap (~$0.01-0.014/image), so this is essentially free compared to the video clips.

### Advanced variant: both people in one frame (library's actual "Dualcast")

The library also documents a *different*, harder technique: both people together in a single reference image, and a single video generation where one speaks and the other listens/reacts in the same shot (`"The person on the LEFT is actively speaking... The person on the RIGHT is only listening, occasionally nodding..."`, library section C → Dualcast). This needs a combined two-person reference image (not currently automated by `pipeline.py`) and isn't wired into `build_prompt`'s per-character loop. If the user specifically wants this same-shot look rather than cut-together editing, treat it as a manual/advanced request: generate the combined reference image via apimart's image API by hand, then submit a single video generation with the LEFT/RIGHT prompt structure from the library — don't try to force it through the normal `characters`/`clips` job config, it doesn't fit that model.

## voiceover — the avatar never talks on camera

This is the library's "voz en off" format, and it works differently from every other format: **the avatar is silent on camera** (`no talking, mouth closed`) — the real narration is recorded separately and laid over the clips afterward in CapCut. `pipeline.py` enforces this: when `job.format` is `"voiceover"`, it builds every clip as a silent b-roll shot and never puts spoken dialogue into the Veo prompt. Each clip's `dialogue` field is instead written out in order to `narration_script.txt` in the output folder — that's the script the user (or a separate TTS pass) reads for the voice-over track.

**Every clip requires `visual_override`** (the script raises an error otherwise) — a description combining an *acción* + *sitio/luz*, e.g. `"She looks at herself in the bathroom mirror just woken up, messy hair, sleepy expression. Soft morning light through the window."` Pull these from the library's extensive tables (section C → Voz en off): acciones (rutina/mañana/casa, belleza, calle/lifestyle, producto/UGC, fitness, emociones, comida), sitio+luz, plano/ángulo, and movimiento de cámara — mix and match to fit each line of the (separately-recorded) narration.

Set `no_face: true` on a clip when it's a POV/insert shot with no face at all (e.g. close-up of hands writing) — this tells the script not to attach the character's reference images for that clip, since there's no identity to anchor. Leave it unset (default `false`) for on-camera shots, which still get the reference images attached for consistency.

**Identity consistency across many different scenes** is the hard part of this format — a single frontal selfie doesn't give Veo enough to work with across wildly different angles/settings. Generate a character sheet first (SKILL.md step 3b, using the library's exact 3×3 character-sheet prompt via `pipeline.py character-sheet`) and add it to `avatar_images` alongside the original photo.

`camera_realism` here should be a movement line from the library's "Movimiento de cámara" table (section C), e.g. `"Slow subtle push-in"` or `"Tracking shot following alongside her as she walks"` — the script appends "cinematic, no talking. Keep the SAME person from the reference." and "No text, no watermark." automatically around whatever `visual_override` you write, matching the library's proven template exactly:

```
[movimiento de cámara] Single continuous take... cinematic, no talking. Keep the SAME person from the reference. [acción]. [sitio + luz]. No text, no watermark.
```
