# Realism playbook — prompt system v2

What actually separates "obviously AI" from "a real phone video" in Veo 3.1 output, and which layer of the
system controls it. Read this before writing a job config; `prompt-formula.md` explains the individual fields.

The prompt is not the only lever. In order of impact: **1) the reference photo, 2) the audio/timing layer,
3) the physical-behavior cues, 4) the scene/camera text.** v1 only worked on (4).

## The pipeline, layer by layer

| Layer | What it controls | Where it lives |
|---|---|---|
| Reference photo | Skin texture, framing, aspect ratio, expression at frame 0, background, light. Veo copies all of it and the text cannot override it (see SKILL.md, "reference photo wins"). | `pipeline.py prep-reference` |
| Audio | Room tone, mic character, no music. Without it Veo gives a studio-clean voice, and every clip has a different noise floor, which shows at each seam. | preset `audio` block |
| Timing | When speech starts and ends. Without it lines get cut at the 8s cap, or Veo fills leftover seconds with stray ad-libbed words. | preset `timing` block + lint |
| Behavior | Blinks, breathing, sway, hands, gaze, clothing. The "alive" feeling. | presets `eyes`, `body`, `skin` |
| Camera physics | Real handheld drift vs. robotic lock. | preset `camera` |
| Light | One motivated source with falloff vs. flat even light (reads as synthetic). | preset `light` |
| Guards | No subtitles, no watermark, no extra hands/people. | preset `avoid` |

## What v2 changed and why

- **Labeled blocks in fixed order** (Setting, Subject, Camera, Look, Performance, Dialogue, Voice, Audio, Timing, guard). Same content every clip, easier to debug from `prompts_used.json`.
- **Audio block.** Phone-mic recording of a small room, no music. Identical in every clip, which also evens out the noise floor between clips.
- **Timing block + lint.** Speech starts ~0.5s in and ends before the last second; the rest is a closed-mouth hold. `nothing is said before or after this line` targets the stray-words defect. The lint enforces a word budget (~6.5s of speech per clip).
- **`says in Spanish:`** in the Dialogue line, instead of leaving the language implicit.
- **No-subtitles guard.** Quoted speech sometimes gets rendered as burned-in captions.
- **Handheld physics instead of "completely static".** A phone at arm's length always drifts. A locked frame is a tell.
- **Motivated, directional light** instead of "soft even lighting" (an AI tell). No ring light.
- **Skin/eyes/body cues.** Pores, flyaway hairs, catchlights, blinks, breathing, clothing folds, and "exactly two hands, five fingers each".
- **Dropped the "Continuing as the same person…" phrase.** Veo has no memory between calls. Replaced with "Same person, outfit, hairstyle, room and light as in the reference image" in Subject, which points at the thing Veo does see.
- **Scene text is positive.** Naming what to exclude ("no car, no seats…") primes Veo to draw it. Describe what IS there in `scene_lock`.

## Job config additions (all optional)

```json
{
  "prompt_style": "v2",                 // default. "legacy" = exact old v1 prompt
  "realism": "phone_selfie",            // preset by format if omitted; "off" disables
  "scene_lock": "Standing indoors close to a bare plain light-beige wall directly behind her, wearing a plain white t-shirt.",
  "camera_realism": "Selfie framing, head and upper torso, she talks directly to the camera.",
  "characters": { "avatar1": { "speech_wpm": 185 } },
  "clips": [ { "pre_action": "glances down, then up to the lens", "post_dialogue_action": "and smiles slightly." } ]
}
```

- Presets: `phone_selfie` (selfie), `phone_propped` (talking_head), `studio_podcast` (podcast, dual_cast).
- Override any block: `"realism": {"preset": "phone_selfie", "light": "Warm lamp on the right...", "eyes": null}` (`null` drops the block). Blocks: `camera, light, skin, eyes, body, speech, timing, audio, image, avoid`.
- Keep `scene_lock` + `camera_realism` short (~30 words each). The preset already carries the realism cues; repeating them dilutes the prompt.
- `speech_wpm` per character sets the lint's speech-time estimate (default 150 wpm; a `voice_profile` that says "185 words per minute" is picked up automatically).

## Scene variety across a long campaign (optional, talking formats)

A campaign of 8+ clips with one single fixed background can start to read as "one take chopped into pieces" rather than several real moments. A character can define extra named `variants` on top of its default `avatar_images` — each is its own reference photo/setting, uploaded and attached only to the clips that ask for it:

```json
"characters": {
  "avatar1": {
    "avatar_images": ["ref_wall.jpg"],
    "variants": {"kitchen": ["ref_kitchen.jpg"], "couch": ["ref_couch.jpg"]},
    ...
  }
},
"clips": [
  {"id": 4, "character": "avatar1", "avatar_variant": "kitchen", "scene_lock": "In a lived-in kitchen, morning light through a window on the left.", "dialogue": "..."}
]
```

Generate each variant photo with `prep-reference` (same person/outfit, different `--setting`), same realism rules as the primary reference. A clip without `avatar_variant` keeps using `avatar_images` ("default"). `scene_lock` on the clip overrides the job-level one for that clip only, so the Setting line in the prompt matches the photo actually attached — leaving the job-level `scene_lock` in place while switching only `avatar_variant` produces a prompt that contradicts its own reference image (the photo wins, per SKILL.md, so the text is just wasted words at best).

This is a deliberate trade, not a default: more reference photos to manage, and each variant is its own small identity-consistency test (look at it before trusting it). Reserve it for campaigns long enough that the repetition would actually show — most campaigns under ~6 clips don't need it.

## Workflow

1. **Prepare the reference** (skip only if the photo is already an unretouched, full-bleed 9:16, neutral-mouth phone photo in the right setting):
   ```bash
   python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py prep-reference \
     --image /path/ref.jpg --setting "<ONE setting + light, positive wording>" --output-dir <campaign>/refs
   ```
   Look at the result: same person? Pores visible? Mouth neutral and closed? Setting right? ~$0.014.
2. **Write the job** with `scene_lock`, short `camera_realism`, per-clip `delivery`.
3. **`pipeline.py preview --config job.json`**. Free. Read the prompts and the lint. Fix errors.
4. **One test clip** before the full campaign (existing cost discipline).
5. `generate`, then the existing self-review (start/middle/end frames, per-clip transcript).

## Lint rules (run automatically before `generate`, or via `preview`)

Errors (block submission): a line that will not fit 8s; quote marks inside the dialogue; duplicate clip ids; missing delivery.
Warnings: line over the 6.5s speech budget; "completely static/unmoving" frame on a selfie; excluded objects named in scene text; polish words (cinematic, flawless, perfect, stunning, 4k…); identical gesture/delivery in consecutive clips.

## Vocabulary bank (for `delivery`, `pre_action`, `post_dialogue_action`)

Vary these clip to clip; a repeated gesture reads as a loop. Combine with the gesture list in `avatarhype-library.md`.

- **Gaze:** glances away as if remembering, then back to the lens; looks slightly down at the phone screen for a beat; eyes widen on the key word.
- **Head/face:** small nod on the stressed word; head tilts on a question; a half-smile that breaks through; brows lift on the hook; a short exhale through the nose before starting.
- **Hands:** counts on fingers; open palm outward when explaining; tucks hair behind an ear; brushes hair off the face; small pointing gesture toward the lens.
- **Posture:** weight shifts from one foot to the other; leans in a little toward the lens on the hook; straightens up on the CTA.
- **Energy by role:** hook = direct, slightly leaning in; problem = quieter, slower; turn = brighter, faster; CTA = warm, steady, eye contact held.

## Measured on a real test (same avatar, same 19-word line)

A = old v1 prompt, B = v2 prompt + old reference, C = v2 prompt + `prep-reference` photo. ~$0.17 of clips.

| | A (v1) | B (v2, old ref) | C (v2, prepped ref) |
|---|---|---|---|
| Look | flat even light, smooth pink airbrushed skin, frame locked | still smooth skin, handheld movement, **frame 0 is the kissy pose from the reference** | directional light with wall falloff, visible pores/freckles, flyaway hairs, natural gestures |
| Words correct | 19/19 | 19/19 | 19/19 |
| First word / last word ends | 0.26s / 7.58s | 0.82s / 7.66s | **0.50s / 7.17s** (as instructed) |
| Room left after the last word | 0.4s | 0.3s | **0.8s** |

Takeaways: the prepped reference was the biggest visible jump; v2 alone (B) adds movement and timing but inherits the reference's smooth skin and pose; timing control works (C matches the instruction almost to the tenth of a second); text accuracy did not regress.

- **Speech runs ~8% slower than the wpm you describe** (a "185 wpm" voice ran ~171 wpm: 19 words = 6.7s, not 6.2s). The lint pads its estimate by 8% for this reason.
- **Low-frequency rumble in the last 0.3-0.8s** of the clips (visible in a spectrogram, present in the old v1 clip too, so not caused by v2). **Now cut automatically** (see "Tail trim" below). Verified on the test clip C: tail level -19.0 dBFS -> -27.6 dBFS, all 19 words intact, last word still ends at 7.2s.
- **Duplicated tattoo:** the bow tattoo (only on the right forearm) appeared on both arms in several frames of every version. If a distinctive mark matters, drop it from `avatar_descriptor` (the reference already shows it) or state "only on the right forearm, no marks on the other arm" and check frames.
- The audio was judged by transcript and spectrogram only; **listen to the clips yourself** to judge voice naturalness.

## Tail trim (automatic, after download)

`generate` now transcribes every downloaded clip (AssemblyAI, pennies) and cuts it at **last word end + 0.30s** (60 ms audio fade), which removes the end-of-clip rumble. It also acts as the per-clip transcript QA from SKILL.md step 5b: the result is printed and saved to `clip_qa.json` (first/last word times, similarity, status).

Safety rules baked in (a blanket trim once ate last words, so this one is evidence-based):
- Only trims a clip whose transcript matches its dialogue (same word count ±1 and same last word). Otherwise it reports `NOT trimmed` with the reason and leaves the clip alone: a mismatch means Veo dropped/added a word, which is a regeneration decision, not a trim.
- Never cuts if it would gain under 0.15s (e.g. a line that already runs to the end of the clip).
- Keeps the original as `clip_NN.raw.mp4`; a clip that has one counts as processed, so re-running is safe. To retry with another margin: `cp clip_NN.raw.mp4 clip_NN.mp4`, delete the `.raw.mp4`, then re-run `trim-tails --margin X --clips N`.
- A freshly regenerated clip discards its stale `.raw.mp4`.

Run it by hand on any past campaign (needs the job JSON, uses its `output_dir` and dialogue):

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py trim-tails --config job.json --dry-run   # report only
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py trim-tails --config job.json --restitch  # cut + rebuild final_video.mp4
```

Options: `--margin 0.4`, `--clips 3 7`. In the job JSON: `"trim_tails": false` disables it, `"tail_margin_s": 0.3` sets the margin. `generate --no-trim-tails` skips it once. Skipped automatically for `voiceover` (no speech) and when no `ASSEMBLYAI_KEY` is configured (this skill's `.env` or `editar-anuncios/.env`).

Because the v2 timing block leaves ~0.5-1s after the last word, most clips have something to cut; a clip that runs long (line over the speech budget) has nothing to gain and keeps its rumble, which is one more reason to respect the lint's word budget.

## Self-review and recovery tooling

- **`pipeline.py review --config job.json`** — one contact sheet, START/MIDDLE/END frame per clip, labeled with the transcript-QA status from `clip_qa.json`. Free (local ffmpeg only). Replaces hand-picking `ffmpeg -ss` timestamps per clip for SKILL.md step 5b's visual check.
- **`pipeline.py regenerate --config job.json --clips 5 8`** — clears the saved task/file for just those ids and resubmits them; the rest of the campaign is untouched. Edit the clip's `delivery`/`dialogue`/`visual_override` in job.json first to actually fix the defect, then run this.
- **Content-policy false positives are auto-retried once.** `generate` detects a "content polic..." error, resubmits the exact same clip immediately (tracked in `policy_retries.json` so a resumed run never double-retries), and only reports it as failed if it's blocked a second time — at which point the failure message names the exact `merge-clips` command to run, using the actual neighboring clip id.
- **`pipeline.py merge-clips --config job.json --drop 5 --into 6`** — the fix for a clip stuck on a repeated content-policy block: folds clip 5's dialogue into clip 6 (in speaking order), drops clip 5 from the campaign for good (recorded in `merges.json`, an overlay — `job.json` itself is never rewritten), invalidates clip 6's local state, and resubmits it with the merged line. Refuses across different characters or over the ~7.3s speech ceiling unless `--force`; `--no-generate` only records the merge. Every other command (`preview`, `generate`, `trim-tails`, `regenerate`, `review`) reads through the same overlay, so the merge stays consistent everywhere without editing the original job.

## Cross-campaign learning log

`generate` appends one entry to `~/.claude/skills/video-ads-avatar/campaign_log.json` per run: campaign name, format, realism preset, `reference_prepped` (set it in the job if you used `prep-reference`), clip count, cost, and a summary from `clip_qa.json` (clips trimmed, clips with a transcript mismatch). `campaign_notes` in the job (free text) is carried over verbatim — a good place to note "reusing avatar X" or a hunch to check later.

```bash
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py show-log --keyword <avatar/campaign name>   # before writing a new job for a reused avatar
python3 ~/.claude/skills/video-ads-avatar/scripts/pipeline.py log-campaign --config job.json --outcome "..."  # after the visual self-review
```

The auto-logged fields are objective (what ran); `outcome` is the only field that reflects what the result actually looked like, and it's not filled in until someone judges it — an entry with no `outcome` yet just means nobody has reviewed that campaign's result.

## Known limits

- Veo may still drift the face over long campaigns; keep the single-reference rule from SKILL.md (character sheet only for varied-scene work).
- Audio realism has a ceiling: Veo's own voice model. For the final voice on a high-stakes ad, the ElevenLabs cloning route (see the CTA workflow in SKILL.md) is still the best.
- Word-count based speech-time estimates are approximate (±10%). Transcribe the first clip and adjust `speech_wpm` from its real pace.
