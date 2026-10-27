---
name: video-ads-avatar
description: Generates a complete AI avatar video ad from an ad copy/script and reference images, using apimart.ai's Veo 3.1 API end to end — uploading avatar reference images, splitting the copy into 8-second clips, crafting a Veo 3.1 prompt per clip (voice, delivery, and camera all derived from the avatar and format, using a proven prompt library from a purchased AvatarHype course), generating each clip, downloading them, and stitching them into one final .mp4 ready for CapCut editing. Supports five formats: selfie (handheld phone), talking head (positioned facing camera), podcast (single host, studio set), dual cast (two-person interview, generated per-speaker and cut together), and voiceover (avatar shown silently doing varied day-in-the-life scenes/POV shots as b-roll, with the real narration recorded separately — uses a generated 3x3 character sheet to keep the avatar consistent across scenes). Use this skill whenever the user pastes ad copy plus avatar reference images and asks to generate, create, or produce a video ad, UGC ad, avatar video, talking-avatar clip, podcast-style clip, or voiceover/day-in-the-life/b-roll style video — even if they don't say "apimart" or "Veo3" by name. Also trigger on mentions of apimart, Veo 3 / Veo 3.1, "avatar realista", "vídeo con IA para anuncio", "character sheet", "dual cast", "AvatarHype", or requests to turn a script/copy into a spokesperson video. Also handles a distinct second job: appending a matching CTA to a video that already works as an ad (voice-matched via a descriptive Veo profile or, for a truly imperceptible result, real cloning via ElevenLabs — see "Adding a CTA to an existing video" below) — trigger on "añádele un CTA a este video", "este video ya funciona, solo necesito el CTA", or similar. Also handles cloning an existing video with other avatars ("clona este video con otro avatar", "el mismo video con varios avatares") and silent animated avatar clips for montages — see "Clone a video with other avatars" below.
---

# Video Ads Avatar (apimart.ai / Veo 3.1)

Turns an ad script + reference images of the user's avatar into a finished video ad, using apimart.ai's REST API (no MCP server exists for apimart — this is done via direct HTTP calls).

## Why this workflow exists

The user has a trained GPT that crafts Veo 3.1 prompts and hands them straight to Veo, which (for talking formats) generates video *and* voice together from the prompt alone — no separate TTS/lipsync step. This skill replicates that prompt-crafting step directly in Claude so the whole pipeline — avatar upload, prompt writing, generation, polling, download, stitching — happens in one pass instead of bouncing between ChatGPT and apimart's dashboard by hand.

The user also has **`references/avatarhype-library.md`** — a personal transcription of the prompt library from a course they bought (AvatarHype's "Creativos UGC Realistas"). It contains proven, tested wording for camera movements, voice recipes, accents, gestures, and format-specific techniques. **Treat it as the primary source for phrasing, not this skill's own invented text** — where its wording conflicts with something written here, the library wins; consult it before writing `camera_realism`, `voice_profile`, or `visual_override` content. It's the user's own material, prepared specifically to feed this skill — don't go looking for or reproducing the original course itself beyond what's already extracted there.

## Before starting: check the API key

> **Where keys live (toolkit v1.2.3+):** in one persistent file, `~/.bcc-toolkit/.env` (Windows: `C:\Users\<user>\.bcc-toolkit\.env`), shared by all the toolkit's skills and kept across plugin updates (the plugin folder is replaced on every update, so a `.env` saved inside it would be lost). The scripts also still read this skill's own `.env`. Never ask for, print or paste a key; check with `editar-anuncios/scripts/env_check.py` (it only says set/missing).

The key lives in `.env` next to this skill (`~/.claude/skills/video-ads-avatar/.env`, `APIMART_API_KEY=...`) — the script reads it from there, or from an `APIMART_API_KEY` environment variable if set. Either way: never ask the user to paste the raw key in chat, and never write it into any file yourself, even if they paste it or ask you to — direct them to open the `.env` file themselves (e.g. `open -a TextEdit ~/.claude/skills/video-ads-avatar/.env`) and replace the placeholder. This is a hard rule, not a preference.

If the script reports the key is missing or still a placeholder, stop and point the user at that file. Don't proceed until they confirm it's set.

`scripts/elevenlabs_voice.py` reads its own key the same way from the same `.env` file (`ELEVENLABS_API_KEY=...`) — needed only for the "add a CTA to an existing video" workflow below when real voice cloning is required, not for normal avatar-ad generation.

## Step-by-step workflow

### 1. Figure out the format

Ask (or infer from what the user already told you) which of the five formats this is — they drive real differences in the job config, not just cosmetic ones:

- **selfie** — avatar holding their own phone, handheld selfie framing.
- **talking_head** — avatar positioned in a fixed spot facing the camera (not holding a phone).
- **podcast** — single avatar, seated in a podcast studio set.
- **dual_cast** — two avatars in a podcast/interview set; each is generated separately (own clip, own voice) and cut together in speaking order — this matches the library's "Podcast · 2 personas" technique. (The library also documents a harder, same-single-frame two-person variant it calls "Dualcast" — see `references/formats.md` if the user specifically wants that instead of cut-together editing.)
- **voiceover** — avatar shown *silently* (no talking) doing varied day-in-the-life activities as b-roll, some of which may be POV/insert shots with no face at all (e.g. hands writing); the real narration is recorded separately and added in CapCut. Needs a **character sheet** generated first — see step 3b.

Read `references/formats.md` for the exact `camera_realism` template and gotchas for each format before building the job config — don't guess at these, they encode real lessons about what makes each format read as authentic vs. obviously staged.

**The reference photo's actual scene wins over a generic format label.** If the reference image already shows a specific setting (e.g. a selfie taken while driving, sunglasses on, one hand on the wheel), that scene *is* the campaign's scene — don't reinterpret an ad-copy format note like "plano medio" into a different, more generic setting (e.g. switching to `talking_head` in a neutral room) just because the copy doc didn't spell out the scene. Keep the format and setting consistent with what the photo shows across the *entire* campaign, clip to clip — a real UGC selfie ad doesn't drift from "holding the phone while driving" to "sitting still facing a fixed camera" partway through. If the ad copy's suggested format genuinely conflicts with the reference photo's scene, ask the user which one should win rather than silently picking one.

### 2. Gather inputs from the user (in chat)

You need:
- The ad **copy/script** — the exact words the avatar(s) should say. For `dual_cast`, the user will hand you lines already attributed per speaker (e.g. "PERSONA 1: ... / PERSONA 2: ...") — keep that mapping.
- **1-3 reference images per avatar** (pasted in chat) — one avatar for selfie/talking_head/podcast/voiceover, two for dual_cast.
- Optionally: aspect ratio (default **9:16 vertical**), model (default **veo3.1-fast** — cheap, ~$0.083/clip; only switch to `veo3.1-quality` at ~$0.60/clip if the user asks for a final high-quality pass), and a campaign name for the output folder.

Save any reference images the user pastes to local files (e.g. `output/<campaign>/refs/<char_id>.jpg`) so the script can upload them.

**Check the reference photo for a transient expression before using it as-is.** A candid selfie often catches a mid-blink, tongue-out, exaggerated, or otherwise one-off expression — Veo tends to carry that exact expression into the opening frame of every clip generated from it, which reads as a mistake once it's a talking avatar. If the photo has one of these, generate a corrected version first with a neutral resting expression before treating it as the character's reference:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py generate-image \
  --prompt "Keep the exact same person, face, hair, outfit, and setting from the reference image. Change only her facial expression to a natural, neutral, relaxed resting expression with her mouth closed — not smiling exaggeratedly, not sticking her tongue out, not mid-blink. Same lighting, same pose, same background." \
  --images /path/to/original_ref.jpg \
  --output-dir /path/to/output/<campaign>/refs/ \
  --filename avatar1_neutral.png
```

Use the corrected image (not the original) as the character's primary reference going forward — the original can still ride along as a secondary reference image if useful, since the images cap is 3.

### 3. Analyze each avatar once, per campaign

For each character, look at their reference image and decide, once, for the whole video:

- **`avatar_descriptor`** — who they are (age range, vibe) and the setting, one line.
- **`voice_profile`** — what they *sound* like: pitch, texture, pace, derived from their apparent age and persona (an older woman gets an older, more measured voice; a young energetic avatar gets a brighter, quicker one) — this is the single biggest fix for the "obviously AI" voice problem. Leave the accent unstated to get the **neutral Latin American Spanish** default, or specify one explicitly.
- **`pronoun`** — "she"/"he"/"they", used by the script when it auto-generates the accent clause and the "X says:" wrapper.

Read `references/prompt-formula.md` for the full guidance and examples before doing this — don't skip it.

These pieces are reused **verbatim, word-for-word** for that character across every clip they appear in — that's what keeps them consistent from clip to clip. Veo has no memory between separate generation calls, so identical wording each time (handled automatically by the pipeline script) is the only real lever for consistency; don't write a fresh descriptor per clip.

### 3a. Prepare the reference photo first (realism pass) — the biggest single realism lever

Veo copies the reference photo's skin texture, framing, aspect ratio, background, light AND facial expression at frame 0. A smooth/retouched photo, a boxy crop, or a kissy/posed expression caps the realism of every clip, no matter how good the text prompt is. Unless the photo is already an unretouched, full-bleed 9:16 phone photo with a neutral closed mouth in the right setting, run:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py prep-reference \
  --image /path/to/ref.jpg --setting "<ONE setting + light, described positively>" --output-dir /path/to/output/<campaign>/refs
```

It re-shoots the same person as an unretouched phone photo (visible pores, flyaway hairs, one directional light, neutral relaxed face, full 9:16). ~$0.014. **Look at the result before using it** (same person? textured skin? right setting?), then use it as `avatar_images`. Full system and rationale: `references/realism-playbook.md` — read it before writing any job config.

### 3b. Generate a character sheet whenever a campaign has more than ~3-4 clips of the same character

Before writing any clip prompts, run:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py character-sheet --image /path/to/ref.jpg --output-dir /path/to/output/<campaign>/
```

This calls apimart's image API with a fixed, carefully-worded prompt (baked into the script — don't rewrite it) that produces a 3×3 grid of the same identity from 9 angles/expressions. Add **both** the reference photo and `character_sheet.png` to that character's `avatar_images` (fits within the 3-image cap).

This is **mandatory for `voiceover`** (cuts between many different scenes and activities, hardest case for identity drift from a single frontal selfie), but don't treat it as voiceover-only: real-world testing on an 8-clip `talking_head`/`selfie` campaign still produced face drift and anatomy glitches (an extra hand appearing mid-clip) using only the single reference photo, generated independently per clip with no shared anchor beyond that one image. Default to generating the character sheet for **any campaign with several clips of the same character**, regardless of format — it's cheap (~$0.01-0.014) relative to what a bad video clip costs (~$0.08-0.60), and it's the single biggest lever against a character's face subtly changing partway through the ad. Skip it only for genuinely tiny jobs (1-2 clips) where drift has little room to happen.

**Known failure: black letterbox bars top/bottom even though the clip container is correctly 9:16.** Real case: a reference photo shot at ~1122x1402 (~0.8 aspect, closer to square than to 9:16 vertical) produced clips that were genuinely 1080x1920 files, but the actual visible content inside them was boxed into a centered ~0.8-ratio region with black bars filling the rest -- Veo reproduced the REFERENCE PHOTO's own aspect ratio/framing instead of generating a true full-bleed vertical composition. Check this before generating a full campaign: if the user's reference photo isn't already close to 9:16 (a full-body or waist-up vertical phone photo usually is; a landscape-ish or square bust portrait usually isn't), generate a corrected reference image first via `pipeline.py generate-image` -- same person/scene/outfit, explicitly composed to fill a full 9:16 vertical frame (more headroom and more of the room/desk visible top-to-bottom, not just a tighter crop of the same boxy composition) -- and validate it with a single test clip before committing to the full multi-clip generation.

**The reference photo's own background wins over a contradicting `camera_realism` scene description, every time — pick a reference that already shows the setting you want.** Real case: `camera_realism` explicitly said "plain light-colored wall, casual home setting," but the avatar's reference photo was a selfie taken inside a car. Result across a 14-clip campaign: some clips rendered her against a wall, some in the car, and within the car ones the seat position itself was inconsistent (read as front seat in some clips, back seat in others) — an inconsistency the user caught immediately and that undermines the entire point of cloning a reference ad's look. This is the exact same class of failure as the letterbox-bars and bleed-through notes above (reference image content overriding prompt text), just for the SCENE instead of aspect ratio or a caption. Fix: if the source material you're cloning has a specific setting (plain wall, car, desk), generate a corrected reference photo showing THAT setting explicitly (same person/outfit/tattoo, described background) via `pipeline.py generate-image` before running the full campaign — don't rely on `camera_realism` text alone to override what the reference photo visibly shows. Validate with one test clip that the setting actually stays put before committing to the full run.

**Known side effect of passing more than one `avatar_images` entry: reference bleed-through near the end of the clip.** With two reference images (photo + character sheet), Veo sometimes visibly morphs the final frames of a clip toward the character sheet grid itself — a blurry multi-face collage bleeding into the shot right before it ends. Two layers of defense, both automatic in `pipeline.py`, neither sufficient alone:

1. **Prompt-level**: whenever a clip's character has more than one `avatar_images` entry, `build_prompt` appends an explicit instruction that the shot must show only one real person, never a grid/collage/duplicated faces, "including the very end of the clip."
2. **Post-hoc trim**: the script re-encodes and trims the last 1.3 seconds off that downloaded clip before stitching (see `trim_end`).

Real campaign data point (27-clip run, both defenses in place at 1.0s trim): 7 clips still showed the artifact on inspection, all but one only in the very last ~0.2-0.3s of the (already-trimmed) clip — the 1.0s margin was cutting it too close. Bumped to 1.3s. **Don't treat either fix as guaranteed** — always do the START/MIDDLE/END visual check in step 5b below on the actual downloaded clips before stitching, specifically sampling multiple points in the last ~2s (not just one frame at the very end), and regenerate any clip that still shows it.

Use `scripts/scan_clip_endings.py --clips-dir <clips folder> --output /tmp/scan.jpg` to do this scan across a whole campaign in one shot instead of hand-writing ffmpeg/PIL contact-sheet code each time (this is exactly what that manual code looked like, now bundled). Read the resulting image yourself — the script only assembles it.

**A 1.3s trim can cut into real dialogue on a clip that never had bleed-through in the first place** (real case: a clip with no bleed history got the blanket 1.3s trim during an unrelated re-stitch, and it silently ate the last word of its sentence — the bleed onset and the word's end were only ~100-300ms apart, too tight a margin either way). Trim amount should track whether a SPECIFIC clip actually showed the artifact, not be applied blanket-uniformly to every multi-ref clip regardless of its own history. If a clip has never shown bleed-through, don't casually widen its trim "to be safe" — that safety margin is exactly what risks the dialogue instead.

### 4. For each clip: analyze the line, then write its delivery (and visual, for voiceover)

For every dialogue segment, read the words and decide what emotion they carry and how the body should express it — don't reuse one generic "delivery" for the whole ad. Write a `delivery` string per clip covering:
- **Tone** — how it should land emotionally (vulnerable, urgent, proud, conspiratorial...), driven by what that specific line says.
- **Body language / expression** — what the face and posture are doing while they say it — concrete, not decorative.

**`voiceover` format works differently — read this even if `delivery` above feels familiar.** The avatar never talks on camera in this format: every clip is silent b-roll (`no talking, mouth closed`), and the real narration is recorded separately and laid over the clips afterward in CapCut — this is the library's proven "voz en off" technique, not a simplification. Concretely:

- Every clip needs `visual_override` set (the script errors if it's missing) — a description combining an *acción* + *sitio/luz*, pulled from the library's tables (section C → Voz en off) rather than invented from scratch.
- Decide per line whether the avatar's face should be visible doing something representative of the line, or whether it's a POV/insert shot with no face at all (e.g. a line about writing → close-up of hands writing). For a no-face shot, also set `"no_face": true` on that clip so the script doesn't attach reference images to it. Not every line needs an avatar shot; mix it up the way a real day-in-the-life edit would.
- `delivery` isn't used for this format's clips — `camera_realism` (a movement line from the library) plus `visual_override` (acción + sitio/luz) carry the whole shot.
- `dialogue` is still required per clip, but it's narration text, not spoken audio — the script writes it out in order to `narration_script.txt` in the output folder instead of putting it in the Veo prompt.

The pipeline script (prompt system v2, see `references/realism-playbook.md`) already adds the realism layers to every talking clip — phone-camera physics, motivated light, skin/eye/body cues, phone-mic audio, timing (speech starts ~0.5s in, ends before the last second, nothing said outside the line) and a no-subtitles guard — so `delivery` only needs the tone/body-language content for that specific line. (v1's "Continuing as the same person…" phrase is gone in v2: Veo has no memory between calls; v2 anchors on "same person, outfit, room and light as in the reference image" instead. Set `"prompt_style": "legacy"` to get the old prompt exactly.) For a gesture that happens *during or after* the line rather than before it, use the optional `post_dialogue_action` field instead of folding it into `delivery` (see `references/prompt-formula.md`).

**Write real detail, not a placeholder-length line.** A one-clause `camera_realism` or `avatar_descriptor` ("plano medio, luz cálida") leaves Veo to invent the rest, which is exactly where unrealistic results creep in — a driving selfie with a wrong-looking or static background, sunglasses with no reflections, a room with no sense of depth, or a stray extra limb. Spell out the scene-specific realism cues that actually apply: if she's driving, describe the road/scenery visibly moving past the window and the road reflected in her sunglasses lenses; if indoors, describe the specific light source and what it's doing to the skin/hair; if a hand is in frame, describe what it's doing so Veo doesn't invent a second one. This is more prompt-writing effort per campaign, not per clip — the shared fields (`avatar_descriptor`, `scene_lock`) only need to be this detailed once, then get reused verbatim. **With v2, put scene detail in `scene_lock` (positive wording: describe what IS there, never "no car, no seats…", which primes Veo to draw them) and keep `camera_realism` to one short line** — the realism preset already supplies handheld drift, light, skin, audio and timing, and repeating them (or adding "completely static frame" / "soft even lighting") dilutes or contradicts them. `pipeline.py preview` lints for exactly these mistakes.

Vary the **delivered vocal tone** clip to clip as much as the body language — a line about doubt/vulnerability should sound quieter and slower even though `voice_profile` (pitch/texture) stays fixed; a confident CTA line should sound brighter and more energetic. `delivery` is the field that carries this — don't let every line default to the same flat energy just because `voice_profile` is shared across the campaign.

### 4b. Hard per-clip duration cap — split long dialogue into multiple clips

**Veo renders a fixed ~8 seconds per clip, full stop — it does not stretch to fit however much `dialogue` text you give it.** Real case: a single clip given a ~30-word CTA paragraph came back only 8s long, audio cut off mid-word partway through the first sentence, because Veo simply generated 8 seconds of speech and stopped — it did not error, warn, or refuse the job, it silently produced a truncated result that looked superficially fine (valid file, no error status) until transcribed.

Before writing `dialogue` for any clip, estimate its spoken duration from words-per-second and keep each clip at or under ~8s of speech:
- If you measured the actual speaking pace from a reference video (see step 3's voice analysis), use that rate directly.
- Without a measured rate, assume a calm/measured pace of ~135-140 words per minute (~2.3 words/sec) as a safe default — **~18 words is the ceiling for one clip**, and it's safer to target 14-17 to leave margin.
- Split longer dialogue at natural clause/comma boundaries (never mid-clause) into as many clips as needed, all sharing the same character (same `voice_profile`/`avatar_descriptor`/reference image, reused verbatim) so the continuity phrase and consistent voice/visual carry across the join — exactly the same mechanism that already keeps a multi-clip campaign consistent clip to clip.
- After generating, verify total spoken duration (sum of clip durations, or a transcript) actually covers the full intended text — don't assume a clip that "came back fine" (valid file, no error) actually said everything you asked for.

### 5. Build the job config, preview it, then run the pipeline script

Write a JSON job file (see schema below). **First run the free dry run** — it prints every assembled prompt with its word count and estimated speech time, and lints the job (lines that won't fit 8s, quote marks in dialogue, "completely static" frames, excluded objects named in scene text, polish words, repeated gestures):

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py preview --config /path/to/job.json
```

Fix every error, read the warnings, then run (`generate` re-runs the same lint and refuses to spend on errors; `--skip-lint` overrides):

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py generate --config /path/to/job.json
```

The script assembles the final Veo prompt for each clip from these pieces (character's avatar+voice+accent, shared camera/format setting, per-clip delivery+dialogue, optional visual_override) — don't hand-write the full prompt text yourself, and don't hand-roll curl/ffmpeg commands either; the script handles apimart's async task polling, retries, prompt assembly, and clip concatenation consistently. It also writes `prompts_used.json` in the output folder with the exact final prompt sent for each clip.

**Job config schema:**

```json
{
  "campaign_name": "nombre-corto-sin-espacios",
  "format": "selfie",
  "model": "veo3.1-fast",
  "aspect_ratio": "9:16",
  "resolution": "1080p",
  "output_dir": "~/video-ads-avatar/output/nombre-corto-sin-espacios",
  "scene_lock": "OPTIONAL but recommended (v2): the ONE unchanging setting, outfit and props, positive wording, ~30 words. Reused verbatim in every clip.",
  "camera_realism": "Short shared framing line (v2: ~one sentence; the realism preset adds handheld physics, light, audio, timing). Legacy jobs can still put the whole scene + camera here.",
  "realism": "OPTIONAL: preset name (phone_selfie | phone_propped | studio_podcast | off) or {\"preset\": ..., \"<block>\": \"override\" | null}. Defaults from format.",
  "prompt_style": "OPTIONAL: v2 (default) | legacy (exact old prompt)",
  "trim_tails": "OPTIONAL: true (default) | false. Transcript QA + cut of the end-of-clip rumble; tail_margin_s (default 0.3) sets the margin",
  "reference_prepped": "OPTIONAL: true if avatar_images came from prep-reference -- only affects the campaign_log entry, not generation",
  "campaign_notes": "OPTIONAL free text carried into the campaign_log entry, e.g. 'reusing the arcangeles avatar'",
  "characters": {
    "avatar1": {
      "avatar_images": ["/absolute/path/to/ref1.jpg"],
      "avatar_descriptor": "Reusable one-line avatar + setting description.",
      "voice_profile": "Reusable one-line voice description (pitch/texture/pace), derived from the avatar's apparent age/persona.",
      "pronoun": "she",
      "variants": {"OPTIONAL, v2 talking formats only -- see 'Scene variety' in realism-playbook.md": ["/path/to/second_setting_ref.jpg"]}
    }
  },
  "clips": [
    {"id": 1, "character": "avatar1", "delivery": "Tone + body language for this specific line.", "dialogue": "Exact dialogue line for clip 1."},
    {"id": 2, "character": "avatar1", "delivery": "...", "dialogue": "...", "visual_override": "Talking formats: only for insert/POV shots, replaces the avatar shot. Voiceover format: required on every clip (acción + sitio/luz).", "no_face": false, "post_dialogue_action": "Optional: a gesture happening during/after the line, e.g. 'and smiles warmly at the camera.'", "avatar_variant": "OPTIONAL: a key from this character's 'variants' above, for this clip only", "scene_lock": "OPTIONAL: overrides the job-level scene_lock for this clip only -- pairs with avatar_variant"}
  ]
}
```

For `dual_cast`, add a second entry to `characters` (e.g. `avatar2`) and alternate `"character": "avatar1"` / `"character": "avatar2"` across `clips` in speaking order — the script tracks first-appearance-per-character automatically so the continuity phrase is added correctly for each of them independently.

For `voiceover`, every clip needs `visual_override`; add `"no_face": true` on clips that are pure POV/insert shots (hands, objects, no face) so the script skips attaching reference images for those specifically.

`avatar_images` accepts local file paths (the script uploads them via apimart's `/v1/uploads/images` endpoint to get public URLs) or already-public URLs directly. `accent` is optional per character — omit it to use the neutral Latin American Spanish default (`Spanish with a neutral Latin American accent.`), or use one of the 5 proven accent lines from `references/prompt-formula.md`.

### 5b. Self-review every clip before stitching — don't ship the first result blind

Veo's output isn't reliable enough to trust unseen. Before treating a batch of clips as done, check each downloaded clip both visually and by ear:

- **Visual — pull frames from the START, MIDDLE, *and* END of the clip**, not just the first couple seconds: `ffmpeg -i clip_XX.mp4 -vf "select=eq(n\,0)+eq(n\,60)" -vsync vfr /tmp/check_%d.png` catches the opening but misses defects that only appear near the end — the reference-bleed-through artifact above (now auto-trimmed, but still worth spot-checking) was only visible in the last ~1 second of the clip, invisible at 0s or 4s. For the end specifically, sample **several** points (e.g. duration-1.8s, -1.2s, -0.6s, -0.2s), not just one frame at duration-0.3s -- a real 27-clip campaign had the artifact surface only in the single frame closest to the (already auto-trimmed) end on 6 of 7 affected clips; one sample point would have missed most of them. Check for:
  - **Anatomy glitches**: extra or duplicated limbs/hands, warped fingers, a face that briefly distorts.
  - **Identity drift**: does this still look like the same person as the reference photo / character sheet, not a subtly different face?
  - **Format/scene drift**: does this clip still match the established scene (e.g. still holding the phone at the same selfie angle, still driving with the same background) rather than sliding into a different framing than the other clips?
  - **Reference bleed-through**: any part of the shot warping toward a flat gray studio background or a multi-angle grid — the character sheet leaking into frame.
- **Audio — actually listen to the clip (or get a transcript) and compare it word-for-word against the `dialogue` you wrote.** Veo can duplicate, drop, or garble a word (e.g. "una una persona" instead of "una persona") even when the visual take is otherwise great — this is easy to miss by only inspecting still frames, and it's exactly the kind of defect a client will hear immediately. Don't skip this check just because the frames looked clean. **Transcribe clips individually at this stage, not only the final stitched video later.** A single clip is a tiny, fast upload (seconds) vs. re-transcribing a full multi-minute assembled video (1-3+ minutes each time, on AssemblyAI) — catching a duplicated word here, before stitching/tightening/rendering, is both faster to detect and cheaper to fix (regenerate one clip) than catching it after the whole edit is built (regenerate the clip, then redo every downstream step that already ran on the bad version).

**Build the visual check from one contact sheet, not by hand-picking ffmpeg timestamps per clip:**

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py review --config job.json
```

Writes `<output_dir>/review.jpg` (or `_1.jpg`, `_2.jpg`... past 10 clips) with every clip's START/MIDDLE/END frame in one grid, labeled with the clip id and its transcript-QA status from `clip_qa.json` when available. Free, local ffmpeg only, no API calls. Read the image(s) yourself for the checks above — the script only assembles it. `--clips 5 8` restricts it to specific ids after fixing something.

If a clip has any of these problems, don't include it as-is — regenerate just that clip:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py regenerate --config job.json --clips 5 8
```

This clears the saved task/file for those ids only and resubmits them (the rest of the campaign is untouched, same idempotent logic as any other resume). To fix the actual defect, edit that clip's `delivery`/`dialogue`/`visual_override` in job.json first (e.g. explicitly stating "one hand holding the phone, the other hand resting on the steering wheel, no other hands visible" if a third hand appeared), then run `regenerate`. This costs another clip's worth (~$0.08-0.60) but is cheap next to shipping a visibly broken ad — tell the user when you're doing this and why, don't just silently swap it in. A duplicated/garbled word is a script-delivery problem, not a visual one — re-running the same clip won't reliably fix it either (Veo's TTS isn't deterministic), so flag it to the user rather than assuming a silent re-roll will resolve it, and don't assume it's fixable by trimming silence in editing — a duplicated word usually has no clean gap to cut at.

**Also proofread every `dialogue` string against the source script before submitting**, not just after — a wrong pronoun or word (e.g. writing "tu intención" when the established ritual phrase across the campaign is "mi intención") gets spoken exactly as written, and Veo has no way to know it's a typo.

**A negative instruction that contradicts the reference image itself tends to lose.** Real case: a reference frame grabbed from a source video had burned-in caption text ("SENSACIÓN DE PAZ") and a human silhouette baked into the picture; the prompt said "no on-screen text" and "no human figure or face" — Veo mostly ignored both and rendered an almost-frozen reproduction of the reference, captions included. When you need Veo to change something the reference photo itself shows, don't just add a negative clause and hope — either (a) pick a cleaner reference frame that doesn't contain the element you want gone (the real fix for baked-in captions specifically — grab a frame from a moment/source without them, or crop them out first), or (b) if the element is actually fine to keep (e.g. a recurring silhouette/motif that's part of the source's own visual identity), stop fighting it and allow it, and reserve the negative instruction for what's genuinely avoidable. Also explicitly demand motion ("real, continuous camera movement throughout, never a static or frozen frame") when working from a single still reference — otherwise Veo may just hold close to that one frame for the whole clip instead of generating new footage.

**A `task_failed` / content-policy block on an innocuous line is often a false positive worth retrying — but if it repeats on the exact same short line, restructure instead of retrying a third time. `generate` now does the first part automatically.** Real case: a 7-word clip ("y cómo invocarlos para recibir su ayuda,") got blocked twice in a row with `"Blocked by a specific content policy (e.g. public figures, minors, audio copyright)"` — nothing in the text remotely matches that description, `credits_cost` was 0 both times (not charged), and every other clip using the same avatar/character passed fine. `generate` detects this pattern and resubmits the exact same clip once, automatically (tracked in `policy_retries.json` so a resumed run never retries the same clip twice). If it fails a **second** time, that's the real signal that the isolated short line itself is tripping the filter — the fix is to merge it into a neighboring clip, not retry again, and the failure message tells you the exact command:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py merge-clips --config job.json --drop 5 --into 6
```

Folds clip 5's dialogue into clip 6 (in speaking order, whichever comes first), drops clip 5 from the campaign for good, and resubmits clip 6 with the merged line — one command instead of hand-editing the job and resubmitting. Refuses (unless `--force`) if the two clips are different characters, or if the merged line would run over the ~7.3s an 8-second clip can actually hold (see 4b below) — in that case shorten one of the two lines by hand first. `--no-generate` just records the merge without resubmitting immediately.

**The blanket multi-ref trim (`trim_end`, default 1.3s) is a bigger real risk than its own docs suggested — check it on EVERY clip, not just ones flagged for bleed-through.** Real campaign data point: 4 of 14 clips (all with zero bleed-through history) had their trim cut into the tail end of real dialogue, silently dropping the last word ("video.", "te ayudan.", "albedrío.", "sola."). The fix each time was the same: re-fetch the clip from its still-valid `task_id` (via `poll_task` + `download`, no recharge) and re-trim with a much smaller margin (0.15-0.3s) instead of 1.3s — the raw untrimmed download is very often completely clean with the real content intact, the blanket trim was the only thing that broke it. **After any multi-ref campaign, transcribe every clip individually (not just visually scan endings) and treat a suspiciously-clipped final word as a trim problem first, before assuming it's a generation defect requiring a costly regeneration.**

**A defect that regenerates differently each time (not converging) is the line itself, not bad luck — after 2 failed regenerations, switch strategy instead of trying a 3rd time.** Real case: one line got a duplicated phrase on attempt 1, then "2 veces" nonsense appended on attempt 2 with a *different* stray phrase prepended on attempt 3 — three attempts, three unrelated defects, no convergence. Meanwhile a different line got two DIFFERENT stray lead-in words across two attempts ("comerciales," then "mundiales,") before a small fixed set of retries — both of THOSE were fixed for free by trimming the stray lead-in in post (`ffmpeg -ss <t-just-before-real-content>`) once the word timestamps showed it was isolated at the very start. Bucket the fix by defect *location*: a stray phrase at the very start or end is almost always free to fix with a precise ffmpeg trim (get exact word timestamps first, don't guess); a stray phrase or garbled content genuinely mid-sentence isn't trim-fixable without a visible jump cut, and there the better move is splitting that line into two shorter clips (shorter lines seem to glitch less) rather than a straight re-roll.

**A full-video transcription can show a discrepancy that doesn't exist in the source clip — check the individual clip again before trusting it.** Real case: transcribing the final concatenated video showed a missing word in 3 different clips that had each already been individually verified as complete and correct; re-transcribing those same clip files in isolation (no concatenation) showed them clean again. The hard, abrupt audio transition between two independently-generated clips (different room tone/mic noise floor from clip to clip) appears to occasionally confuse AssemblyAI's word-boundary detection right at the seam, producing a phantom dropped or added word that isn't actually in the audio. Before treating a full-video-transcript discrepancy as a real defect, re-transcribe the specific clip(s) involved on their own — if they come back clean, it was very likely an ASR artifact of the concatenation, not something to chase further.

**Tail trim is automatic now.** After downloading, `generate` transcribes every clip, checks it against its `dialogue` (step above, done for you: results in `clip_qa.json`) and cuts Veo's end-of-clip rumble at last word + 0.3s — only on clips whose transcript matches the dialogue; mismatches are reported and left untouched (regenerate those). Details, options and the manual `trim-tails` command (for older campaigns): `references/realism-playbook.md`, "Tail trim". You still do the visual START/MIDDLE/END check.

### 6. Report progress and hand off the result

Video generation takes real time (each clip can take a few minutes). While the script runs, tell the user what's happening rather than going silent. When it finishes, the script prints the path to `final_video.mp4` — send it to the user with `SendUserFile` (status: proactive if they're not actively watching, normal if they are) so they can pull it into CapCut. For `voiceover` format, also send `narration_script.txt` alongside it and remind the user the clips are silent on purpose — they (or a separate TTS pass) still need to record the narration and lay it over the clips in CapCut. Mention the per-clip cost incurred (script prints this) so they know what was spent.

If any clip fails (apimart returns an error status or the task times out), the script reports which clip id failed and why, and still stitches together whatever succeeded — don't silently drop a failed clip without telling the user; ask whether to retry just that clip.

## Clone a video with other avatars, animate avatars in silence, realistic avatar photos (v1.2.1)

Three extra jobs, all documented in **`references/clonar-video-y-animar-avatares.md`** — read it before running them:
- `scripts/clone_video.py` — "clona este video con otro avatar / el mismo video con varios avatares": same gestures and rhythm, different person (Kling Motion Control, ~US$0.40 per clip; **ask before uploading the reference video to the temporary host**, run `--dry-run` first).
- `scripts/animate_avatar.py` — silent living clips of avatar photos for montages, walls of faces and b-roll of people (Seedance mini by default; Veo's face filter refuses most realistic faces).
- Photo recipe + model bake-off for avatars nobody believes are AI (`pipeline.py generate-image --model gpt-image-2.5-flare --size 9:16`).

## Adding a CTA to an existing video that already works as an ad

Different job from the rest of this skill: the user already has a finished video that performs well and just wants a CTA appended, seamlessly, without it reading as a bolted-on clip. Validated end-to-end 2026-09 on a real spiritual/angelical voiceover ad. Full recipe:

### 1. Transcribe and let the user pick the cut point AND the CTA content

Transcribe the source video with word timestamps (AssemblyAI, same as always), group it into sentence-level segments with timestamps, and show the **full segmented transcript to the user** — let them tell you where to cut (some videos have "relleno" at the end worth dropping) and, separately, confirm which CTA mode applies:
1. User supplies the exact CTA copy.
2. You draft a CTA matching the video's own content/tone — **show it for approval/correction before generating anything**, never generate off a self-approved draft.
3. A generic CTA for that product (adapt from the product's own reference material, e.g. `references/avatarhype-library.md` or a product knowledge base).

Never assume the niche's own phrasing belongs in the CTA — if the source video isn't from a spiritual niche, don't reach for spiritual language (e.g. "el universo", "todo pasa por una razón") just because past examples used it.

### 2. Decide how the voice gets matched — descriptive vs. real cloning

Two tiers, pick based on how close the match needs to be:

- **Descriptive `voice_profile` fed to Veo** (cheap, fast, no extra account needed): analyze the source's actual voice objectively before writing the description, don't guess from vibes alone. Extract a ~20s mono sample (`ffmpeg -i source.mp4 -ss 5 -t 20 -vn -ac 1 -ar 16000 sample.wav`) and estimate the fundamental frequency with a plain autocorrelation pitch detector (numpy + stdlib `wave` is enough, no need for librosa/scipy) — median F0 under ~150Hz reads as male, roughly 165-255Hz as female, and note whether it's on the low or high end of that. Get speaking rate (words/sec) from the transcript's word timestamps over a clean 60s stretch. Feed both into `voice_profile` as concrete numbers ("medium-low pitch, ~118Hz fundamental, ~138 words/min, calm and measured"), not adjectives alone.
  **Ceiling, tested for real: this gets you a plausible, similar-*category* voice — not the specific person's timbre.** A side-by-side pitch comparison after generation matched almost perfectly (111.9Hz vs the original's 117.6Hz) and the result still didn't sound like the same person to the user's ear. Don't oversell this tier — it's for a fast validation pass or when exact identity match isn't required, not for a final "imperceptible" deliverable.
- **Real voice cloning via `scripts/elevenlabs_voice.py`** (needs `ELEVENLABS_API_KEY` in `.env`, real cost, but this is what actually closes the gap): extract a clean ~45-60s sample of the source narrator with minimal background music (`ffmpeg -i source.mp4 -ss <clean-stretch-start> -t 60 -vn -ac 1 -ar 44100 sample.wav`), then:
  ```bash
  python3 ~/.claude/skills/video-ads-avatar/scripts/elevenlabs_voice.py clone-voice \
    --name "<label>" --samples sample.wav --output-dir <output-dir>/voice
  python3 ~/.claude/skills/video-ads-avatar/scripts/elevenlabs_voice.py generate-speech \
    --voice-id <id-from-clone-voice> --text "<full approved CTA text>" \
    --output <output-dir>/voice/narration.mp3
  ```
  Unlike Veo, ElevenLabs generates the **entire** narration in one call — no 8-second cap, no splitting the CTA into segments for this tier. `clone-voice` only needs to run once per source voice; reuse the saved `voice_id` (in `voice_clone.json`) for later regenerations of the same job (e.g. after a copy edit) instead of re-cloning.

### 3. Build the matching visual — separately from the voice, always

Once voice comes from ElevenLabs (audio only, no video), the CTA's visual is a completely separate concern — don't route it through Veo's talking-format dialogue mechanism, which forces the 8s cap and voice-generation you no longer need. Two options:
- **Reuse b-roll already generated for this job**, muted (e.g. earlier talking-format test clips) — free, already visually validated.
- **Generate fresh matching b-roll**: grab a clean reference frame from right before the chosen cut point (`ffmpeg -ss <cut-point-1s> -i source.mp4 -frames:v 1 ref.jpg`) and either (a) run it through Veo one more time purely for silent b-roll (`camera_realism` describing continued motion, `dialogue` empty/minimal, no voice needed), or (b) generate new still images in the same style via `pipeline.py generate-image` and animate with ffmpeg's `zoompan` (Ken Burns) — cheaper, no video-generation cost at all.
- **For real (non-AI-generated) source footage, check for a clean loopable stretch before generating anything.** Real case: a UGC-style source (real hand writing on paper) had burned-in captions for only the first ~6s, then ~8s of completely clean footage before the chosen cut point. Sample frames across the whole retained portion (`ffmpeg -ss <t> ... -frames:v 1`, several points) to check for this *before* reaching for Veo/image-gen — if a clean stretch exists, loop it with `ffmpeg -stream_loop <n> -i clean.mp4 -t <needed-duration> ...` to cover the CTA's audio duration. This is free, zero generation risk (no anatomy glitches, no reference bleed, no skin-tone/hand mismatch to fight), and looks MORE consistent than anything generated, since it's literally the same footage. Only fall back to generating new visuals when no such clean stretch exists.

**If the reference frame already contains something you want the new footage to NOT have** (e.g. it has the source's own burned-in captions or a specific pose you don't want repeated), see the "negative instruction that contradicts the reference image" note in step 5b above — the same trap applies here.

### 4. Mux voice + visual, caption from the NEW audio's own timing, hand off to editar-anuncios

Mute the visual's own audio and mux in the ElevenLabs narration (`ffmpeg -i visual.mp4 -i narration.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -ar 48000 -shortest combined.mp4`) — **transcribe this narration audio itself** for caption word-timing (AssemblyAI again); the source video's original word timestamps do NOT apply to the new audio, it's a different recording with different pacing.

From here it's `editar-anuncios`'s job: build an EditPlan job with this combined clip, the new captions, and the CTA field (existing CountdownCTA). **Match the source's exact caption style, don't approximate it** — see editar-anuncios/SKILL.md's note on reverse-engineering a caption style precisely (sample several consecutive frames, not one still) before assuming a "close enough" existing variant covers it; a first pass that only matched the highlight *color* but not the stroke/weight/position still read as "a pasted-on clip" to the user.

### 5. Final splice — match resolution AND audio sample rate, not just concatenate

Cut the original at the user's chosen point, get the new CTA segment to the *exact same resolution* as the original (scale down/up as needed — don't leave a resolution jump at the splice), and **force the same audio sample rate on both segments before concatenating** (see editar-anuncios/SKILL.md's "concatenar dos fuentes con distinto sample rate" failure mode — a Remotion render defaults to 48kHz while a real source video is often 44.1kHz, and concatenating without matching them desyncs the whole final file, not just the join point).

**Verify, don't assume:** transcribe the fully assembled final video and check the words right at the splice point flow with natural timing and no gap/overlap — this is what actually confirms the join is inaudible, a visual-only check of the frame at the cut isn't enough.

## Notes on the API (for reference, already baked into the script)

- Auth: `Authorization: Bearer $APIMART_API_KEY` on every request.
- Generate video: `POST https://api.apimart.ai/v1/videos/generations`
- Generate image: `POST https://api.apimart.ai/v1/images/generations` — `pipeline.py character-sheet` (fixed prompt) and `pipeline.py generate-image --prompt "..." --images ref.jpg --output-dir ...` (any prompt, e.g. the library's "Segundo invitado") both use this. Image generation is cheap (~$0.01-0.014/image, gpt-image-2 or nano-banana) — it's the video clips that cost real money, not the image steps.
- Poll: `GET https://api.apimart.ai/v1/tasks/{task_id}`
- Upload image: `POST https://api.apimart.ai/v1/uploads/images`
- apimart has no official MCP server — this is plain REST, wrapped by `scripts/pipeline.py`.

## Performance: polling is concurrent, not one-clip-at-a-time

**`generate` used to take far longer in wall-clock time than the clips actually took to render.** Real case: a 14-clip campaign took 48 minutes even though apimart generates every submitted clip in parallel on its own side — the OLD code polled clips one at a time (`for clip in clips: poll_task(...)`), so clip 2 wasn't even checked until clip 1's task reached a terminal state. That serializes the WAIT even though the WORK is parallel: wall time became the SUM of every clip's generation time instead of the MAX of them. Fixed via `poll_tasks_round_robin()` — every still-pending task gets checked once per sweep, one sleep per sweep, not one sleep per clip. If this regresses (someone reintroduces a per-clip polling loop), the symptom is the same: total time scales with clip COUNT instead of staying roughly flat as clip count grows.

## Multi-ref clips: don't add a character sheet you don't need — it's the actual bleed source (corrected 2026-09)

`trim_end()` no longer runs automatically after every multi-ref clip — but the real fix is upstream of trimming: **only pass more than one `avatar_images` entry (photo + character sheet) when the campaign actually needs it** (varied scenes/settings clip to clip, the `voiceover` format's use case). For a campaign where every clip shares the SAME single setting (e.g. a talking-head ad, one fixed wall/background throughout), a single strong reference photo is enough for identity — adding the character sheet on top adds a second image for Veo to occasionally blend toward, which is the actual mechanism behind the bleed-through artifact, not something a trim should be papering over.

This was learned the hard way in two passes on the same campaign: pass 1 kept the blanket 1.3s trim and it sliced into real dialogue on 4 of 14 clips (dropping the last word) — but the clips LOOKED bleed-free only because the trim had already cut the bleeding tail off before anyone looked; the trim was masking a real, still-present artifact, not preventing a nonexistent one. Pass 2 removed the trim to test that theory and the untrimmed footage confirmed it: severe multi-face grid contamination across most of the last 1-2 seconds in the majority of clips. Pass 3 dropped the character sheet entirely (single `avatar_images` entry, identity carried by one high-quality reference photo alone) and the bleed source was gone — nothing left to trim.

Concretely:
- Default to a SINGLE reference photo for any campaign with one consistent setting throughout (most talking-head/selfie/podcast campaigns). Don't add a character sheet "just to be safe" — it's a deliberate trade (better resistance to identity drift across many DIFFERENT scenes) for a real cost (bleed-through risk), not a free consistency boost.
- Reserve the character sheet for genuinely varied-scene campaigns (`voiceover` format, or any format cutting between clearly different settings/activities) where the extra angles are actually earning their keep.
- If you DO use a character sheet and see bleed on `scripts/scan_clip_endings.py`, trim that specific clip by hand (`trim_end(path, seconds=<amount>)`) rather than reintroducing a blanket automatic trim — tune the amount to that clip's own bleed onset, and re-fetch the untrimmed source from its `task_id` first if you need to retry a smaller margin.
- **Always run `scan_clip_endings.py` on RAW, untrimmed downloads to judge whether bleed is actually present** — checking after a trim already ran (automatic or manual) tells you whether the trim worked, not whether the underlying generation had the problem in the first place.

## Cross-campaign learning log — check it before reusing an avatar

`generate` auto-logs every run to `~/.claude/skills/video-ads-avatar/campaign_log.json` (format, realism preset, whether the reference was prepped, clip count, cost, transcript-QA/trim summary, and `campaign_notes` if you set them in the job). Before writing a new job config for an avatar/character that has run before, check what already happened:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py show-log --keyword <avatar or campaign name>
```

After the visual self-review, record the subjective verdict (the auto-entry alone isn't one) so the *next* campaign with this avatar benefits from it:

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py log-campaign --config job.json --outcome "skin still a bit smooth even with prep-reference, try dropping the light block's 'soft falloff' wording next time"
```

## Cost discipline

The user wants minimum spend for the best achievable realism — not maximum quality regardless of cost. Concretely: default to `veo3.1-fast` always; `veo3.1-quality` (~7x the price) is opt-in only, when the user explicitly asks for a final high-quality pass, never a default assumption. `pipeline.py generate` prints the total estimated cost for the whole job *before* submitting anything (and flags it if it's a quality-model or unusually large run) — read that number and mention it to the user before letting a big job run, the same way you already do manually. Keep test/validation runs to 1 clip where possible; only generate the full multi-clip campaign once the format/voice/realism approach is already validated.

**If apimart runs out of balance mid-job** (`402 Payment Required`, real case: a 20-clip campaign stopped at clip 9), the script now genuinely resumes — it reads `task_ids.json` from the output dir at startup and skips/reuses any clip already submitted there, only charging for what's actually still missing. Tell the user which clip it stopped at and to top up at apimart.ai, then just re-run the exact same `pipeline.py generate --config job.json` command once they have balance — don't hand-edit the config to remove already-submitted clips, the script already handles that. (This resume path used to be broken: it printed a reassuring message about recovering the clips but never actually skipped them on the next run, which would have silently double-charged every already-submitted clip — fixed in `run_generate`.)

**`generate` is now idempotent on the download side too, not just the submit side**: a clip whose local `clip_NN.mp4` already exists and is a valid, playable file is skipped entirely (no poll, no re-download, no re-trim) — only clips missing a valid local file, or whose task_id was just freshly resubmitted (e.g. because you cleared it to fix a defect), actually hit the network. Before this fix, running `generate` again to fix 1-2 clips silently re-downloaded and re-trimmed **all** of them every time — on one real campaign this turned a "fix 2 clips" job into a 10+ minute "re-fetch 27 clips" job, which is also what made it likely for a session boundary to kill the process mid-write and corrupt whatever file was in flight (see the runbook right below). If you ever need to force a genuine re-download of a clip that already has a valid file on disk (rare), delete that `clip_NN.mp4` first — task_id alone won't trigger it anymore.

**Runbook — a `generate` run looks stuck (no new output, no file progress) for several minutes:** this has happened repeatedly right after a session boundary/compaction event orphans the background process — it keeps running but stops making progress, often burning near-zero CPU (check with `ps aux`, then `top -pid <pid>` or just re-check CPU time a minute apart — if it's not climbing, it's not doing real work). Don't just keep waiting or re-polling blindly:
1. Check the specific task directly against apimart instead of trusting the stuck local process: `GET https://api.apimart.ai/v1/tasks/{task_id}` with the same bearer token (`task_id` is in `task_ids.json`). If `status: completed`, the video is done and sitting on apimart's CDN — the local script just never got to downloading it.
2. Kill the stuck process, then either re-run `generate` (now idempotent — safe, see above) to let it pick up from there, or download that one clip's URL directly yourself and drop it at `clips/clip_NN.mp4` if you need to move faster than a full rerun.
3. If the process was killed mid-write on a specific file, that file can be left truncated/corrupt (`moov atom not found`) — always spot-check with `ffprobe` after a kill before trusting `is_valid_video`'s skip-logic on it; a corrupt file with nonzero size but no valid duration will correctly be treated as invalid and re-fetched, but it's worth knowing why one might be sitting there.
