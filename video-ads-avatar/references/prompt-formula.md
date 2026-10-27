# Veo 3.1 prompt formula for avatar ad clips

Veo 3.1 generates video *and* audio (voice, ambient sound) together from the text prompt — there's no separate TTS or lipsync step. That means the prompt has to do three jobs at once: describe the shot, describe the *voice*, and tell Veo exactly what to say and how to say it.

The reference images (up to 3, passed via `image_urls`) already anchor the avatar's face, build, and general look — so the prompt doesn't need to re-describe physical appearance in detail. Spend the prompt's words on what the images can't show: **voice, performance, setting, camera, and delivery.**

**Prompt system v2 (default) is described in `references/realism-playbook.md`** — it adds the realism layers (audio, timing, camera physics, light, skin/eyes/body, guards) around the fields below and is what `pipeline.py` now sends. This file still explains how to fill in the individual fields.

The pipeline script (`scripts/pipeline.py`) assembles the final prompt per clip from per-character fields (`avatar_descriptor`, `voice_profile`, `accent`, `pronoun`, reused verbatim across every clip that character appears in), a shared job-level `camera_realism` (see `references/formats.md` for the template per format), and per-clip fields (`delivery`, `dialogue`, optional `visual_override`, optional `post_dialogue_action`). This file is about how to *fill in* the character-level and per-clip fields well; `formats.md` covers `camera_realism` and the format-specific structure.

**Exception:** everything below assumes the avatar speaks on camera. For the `voiceover` format the avatar is silent on camera and none of the voice/dialogue guidance applies to the video prompt — see `formats.md` for that format's very different structure (voice/accent still matter, but only for the separately-recorded narration track, not the Veo prompt).

## 1. Avatar + setting (`avatar_descriptor`, once per campaign)

Who they are (age range, vibe — not a full physical description) and where they are. Decide this once for the whole ad; it gets reused word-for-word in every clip.

## 2. Voice profile (`voice_profile`, once per campaign)

Look at the reference image and *decide what this person sounds like* — don't leave it to Veo's default, which produces a flat, generic, obviously-synthetic read. `references/avatarhype-library.md` (section B → "La voz") has the proven recipe: **género + edad (in his/her 20s/40s/60s) + gravedad (deep, low or bright, high) + textura (gravelly, raspy / smooth, clean, soft, breathy) + entrega (calm and slow / energetic and fast / warm / authoritative)**, written as a `Voice: ...` line. It also has 8 ready-made recipes by age/gender (young/mid-30s, male/female) — start from the closest one and adjust rather than writing from scratch.

Derive the pick from the avatar's apparent age and persona, not a generic default — a soft-featured young avatar and a "señora mayor" need genuinely different voices; that's the single biggest fix for the "obviously AI" voice problem. These are directions, not rules — read the actual reference image and adjust; the point is the voice should feel like it belongs to *that specific face*.

**Accent:** unless the user specifies otherwise, the avatar speaks neutral Latin American Spanish (`Spanish with a neutral Latin American accent.`, the script's default if `voice_profile`/`accent` doesn't already mention an accent). The library (section B → "El idioma y los acentos") has 5 proven accent lines — use the exact wording, don't paraphrase them:

- **España · Madrid neutro**: `Spanish with a neutral Peninsular (Madrid) accent, informal and conversational, like a real casual chat in Spain.`
- **Argentina · rioplatense**: `Spanish with an Argentine Rioplatense (Buenos Aires) accent, including the typical "sh" sound for "ll" and "y".`
- **Colombia · bogotano**: `Spanish with a clear, neutral Colombian (Bogotá) accent.`
- **México · central (CDMX)**: `Spanish with a Mexican central, Mexico City accent.`
- **Latinoamérica · neutro (default)**: `Spanish with a neutral Latin American accent.`

Put the chosen line in the character's `accent` field (or already inside `voice_profile`, if it's easier to write them as one sentence).

## 3. Camera + realism cues (`camera_realism`, once per campaign)

Shot type, *and* explicit anti-"AI look" cues — this is the single biggest lever for making the clip feel like a real phone video instead of an obviously generated one. `references/avatarhype-library.md` (section B → "Los movimientos de cámara") has a proven library of camera-movement lines to start from (static/quiet, slow push-in, handheld sutil, pull-back, orbit, tracking, etc.) — each one already includes the instruction that stops Veo from sneaking in a cut mid-clip; the pipeline script also appends `"Single continuous take, no cuts or scene changes."` automatically if you forget it, but prefer picking a real library line over writing a fresh one.

On top of the movement, still lean into imperfection cues:

- Frame it as **amateur/phone footage**, not a produced shot: "shot on an iPhone front camera, casual selfie video", not "professional videography".
- Ask for **imperfections**: natural skin texture with visible pores, slightly imperfect handheld framing, natural (not studio) lighting, subtle motion blur.
- Avoid words that push toward the polished/synthetic end: "flawless", "glowing", "perfect lighting" — these make the AI-look worse, not better. ("cinematic" is fine and even expected for `voiceover`-format b-roll — see `formats.md`.)

## 4. Delivery: tone + body language (`delivery`, per clip — this one changes every time)

This is the one piece that should genuinely vary clip to clip, because it's driven by *what that specific line says*. Before writing it, read the dialogue segment and ask: what is she feeling as she says this, and what would her face/body naturally do?

- **Tone**: vulnerable, urgent, proud, conspiratorial, matter-of-fact, excited — whatever the line's content actually calls for.
- **Body language**: leaning toward camera, eyes softening or widening, a small smile breaking through, hands gesturing, shoulders relaxing — concrete physical detail, not just an adjective. `references/avatarhype-library.md` (section B → "Las micro-acciones · gestos") has a ready vocabulary of natural gestures (adjusts their cap, fixes their hair, shrugs, taps their chin thoughtfully, etc.) if a scripted gesture fits better than an improvised one.
- **Timing matters**: the library's rule is that a gesture happening *before* the line goes before the dialogue quote (which is where `delivery` already sits in the assembled prompt) — but a gesture happening *during or after* the line (e.g. "she smiles as she finishes") needs to go *after* the quote instead. Use the optional per-clip field `post_dialogue_action` for that case (e.g. `"and smiles warmly at the camera."`) rather than cramming it into `delivery`.

A script that opens on financial struggle and closes on triumph should *not* use the same delivery for both lines — the opening line calls for something quieter and more vulnerable, the closer for something brighter and more confident.

## 5. The exact dialogue (`dialogue`, per clip)

Word-for-word what the avatar says in this clip — the actual ad copy segment, verbatim. Don't paraphrase or summarize it. Keep each line to what naturally fits in ~8 seconds (roughly 18-20 words) — an over-stuffed line gets rushed or cut off by Veo.

## Keeping voice/character consistency across clips

Veo has no memory between separate generation calls — each clip is generated independently, which is why the voice or look can drift partway through an ad if you're not careful. Two things fight this:

1. **Word-for-word reuse.** A character's `avatar_descriptor` and `voice_profile` must be *identical* across every clip they appear in, and `camera_realism` identical across the whole job (all characters share it) — the pipeline script enforces this by construction (the same strings are inserted into every relevant clip's prompt), so as long as you fill those fields in once per character and don't touch them per-clip, this is handled for you. In `dual_cast`, this applies independently per character even though their clips are interleaved.
2. **Continuity phrasing (v1/legacy only).** In `"prompt_style": "legacy"` the script automatically prepends a continuity phrase to the delivery text of every clip after a character's *own* first appearance (not the job's first clip overall) — an extra nudge that reinforces it's the same take, not a new character. You don't need to write this yourself.

If you ever *do* write a raw prompt by hand instead of going through the job config (e.g. for a one-off test), replicate both of these manually.

## Example

Ad copy segment: *"Este es el código sagrado que empecé a repetir cuando ya no sabía de dónde sacar dinero para pagar mis deudas…"*

Reference image: young woman, soft features, gentle expression, casual home setting.

```
avatar_descriptor: "A young Latina woman in her mid-20s, long straight dark brown hair, natural freckled skin, wearing a maroon tank top, standing in a bright minimalist white hallway with soft natural daylight."

voice_profile: "Her voice is soft, delicate, and tender, slightly breathy, speaking gently and unhurried."
(accent left blank -> defaults to neutral Latin American Spanish)

camera_realism: "Shot like authentic amateur footage on an iPhone front camera — slightly imperfect handheld framing, natural skin texture with visible pores and subtle imperfections, soft natural window light, no studio lighting, subtle motion blur."

clip 1 delivery: "She speaks with quiet, vulnerable, confessional energy, eyes slightly downcast then lifting to meet the camera, like she's opening up about something personal for the first time."
clip 1 dialogue: "Este es el código sagrado que empecé a repetir cuando ya no sabía de dónde sacar dinero para pagar mis deudas…"
```

## Common mistakes to avoid

- Over-describing physical appearance in the prompt — this fights with the reference images and can produce a face that drifts from clip to clip instead of matching them.
- Skipping or genericizing the voice profile — without a voice tailored to the avatar's apparent age/persona, Veo defaults to a flat, generic, noticeably-synthetic read.
- Using the same `delivery` for every clip regardless of what the line says — this produces a flat, emotionally-incoherent performance even when the voice itself sounds fine.
- Writing the dialogue as indirect speech ("she talks about how...") instead of the literal quoted line — Veo needs the actual words to say.
- Using "cinematic"/"flawless"/"perfect lighting"-type language — it pushes the result further into the over-polished, obviously-AI-generated look instead of away from it.
- (v2) Putting the whole scene in `camera_realism` with "no car, no seats…" negations or "completely static frame" — describe the setting positively in `scene_lock` and keep `camera_realism` to one short line; `pipeline.py preview` lints for it.
- Rewriting `avatar_descriptor`/`voice_profile`/`camera_realism` slightly differently per clip "to keep it fresh" — this is exactly what causes the character to drift; keep them identical.
