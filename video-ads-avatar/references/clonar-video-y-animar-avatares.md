# Clone a video with other avatars · animate avatars in silence · photo recipe for realistic avatars

Added in toolkit v1.2.1 (tested 2026-10 with six different people; every clip below passed a visual identity/realism review).

## 1. Clone a video that already works with another avatar (`scripts/clone_video.py`)

**What it does:** takes ONE reference video and N avatar photos and returns N clips with the **same gestures, hand movements,
head movements and rhythm**, performed by each person in *their own* setting (the background comes from the avatar photo, not from the
reference). One working video becomes many versions with different faces.

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/clone_video.py --dry-run --video original.mp4 --avatars a.png b.png c.png --out-dir clones/
python3 ~/.claude/skills/video-ads-avatar/scripts/clone_video.py           --video original.mp4 --avatars a.png b.png c.png --out-dir clones/ --who woman
```

- **Cost:** ~US$0.40 per 7-8 s clip (Kling 2.6 Motion Control, std, 720p). Always run `--dry-run` first and tell the user the number.
- **Privacy — ask before running:** apimart cannot host video, so a local `--video` is uploaded to a *temporary public* host
  (litterbox.catbox.moe, deleted after 24 h). If the reference video must not leave the computer, the user hosts it and you pass `--video-url`.
  Photos go to apimart (as in the rest of this skill).
- **Photos that work:** full-bleed 9:16 selfie-style, face centred in the upper-middle, head + shoulders visible, similar framing to the
  reference (if the reference is a close selfie, don't use a full-body photo). Make them with the recipe in section 3.
- **What you get:** silent clip, same length as the reference, 720p. **The lips follow the ORIGINAL speech** — so either lay a new voice-over
  on top (the clone then reads as "a person talking") or use it as a silent demo. It does not translate or re-voice.
- **Which engine for what** (earlier tests, 2026-09-30): if the new script says *exactly* what the reference says → Kling Motion Control
  (this script; exact gestures, lips match). If the script is different or the language changes → Seedance 2.0 with video + audio + image
  (`seedance-2.0-mini` ~US$0.19, copies gestures and follows the new audio) — not scripted yet; build it by hand with the same apimart
  `/videos/generations` call. Always ask the user whether they want the exact gestures cloned.
- **Verify before delivering:** extract 3 frames per clone (start / middle / end) next to the original and check identity, hands (5 fingers),
  and that the gesture timing matches.

## 2. Animate avatars in silence (`scripts/animate_avatar.py`)

For the "people" shots of an ad — a montage of faces, a wall of avatars, b-roll of a person — not for talking avatars.

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/animate_avatar.py --images a.png b.png c.png --out-dir clips/
```

- Default model **seedance-2.0-mini**: ~US$0.16 per 8 s, 720p, passes the face filter. `--model veo3.1-fast` is sharper (1080p, ~US$0.08)
  but its content-safety filter **refused 5 of 6 realistic faces**; refusals are not charged and the script retries them with `--fallback`.
- Each clip is silent with a natural action (blink, smile forming, glance, hand to glasses/cap). Pass `--action` to set one.
- Add `--descs "Latina woman, 29, kitchen" ...` if identity drifts; it is optional.
- Footage ratio: 8 s per clip is plenty for 0.5-2 s cuts; for a 10 s tile slow the clip to 0.85× in the edit instead of looping it.

## 3. Photo recipe for avatars that people don't believe are AI

Image model bake-off, same prompt, 4 models (apimart): **`gpt-image-2.5-flare` was the most natural** (pores, asymmetry, real light);
`seedream-5-0-pro` natural but slightly polished; `gemini-3-pro-image-preview` good but staged a mirror selfie; `flux-2-max` exaggerated freckles.

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py generate-image --model gpt-image-2.5-flare --size 9:16 \
  --output-dir refs/ --filename ana.png --prompt "<prompt>"
```

Prompt skeleton (English; fill the PERSON + SETTING):

> Candid unedited vertical iPhone front-camera selfie photo, handheld at arm's length, the person looks into the lens, face centered in the
> upper-middle of the frame with head and shoulders visible, slight wide-angle phone distortion, natural unretouched skin with visible pores,
> fine lines, small imperfections, flyaway hair strands, natural catchlights in the eyes, mild phone-camera noise and softness, casual
> off-center candid feel, relaxed neutral face with a very slight natural smile, mouth closed. Not a studio portrait, not retouched, no filters.
> No text, no watermark. **[PERSON: age, ethnicity, hair, glasses/cap, clothes]. [SETTING: car, gym lobby, podcast corner, cafe terrace, kitchen
> in the morning… with ONE believable light source].**

Rules that mattered: one named light source; a real setting with a few out-of-focus objects; neutral mouth closed (avoid transient
expressions — Veo/Seedance copy frame 0); vary age, skin tone and setting across a cast so they don't read as one person.
Deliver the finished clips through `editar-anuncios` (see its `references/anuncio-voz-en-off.md` for a voice-over ad built from them).
