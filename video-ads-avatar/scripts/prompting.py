"""
Prompt system v2 for Veo 3.1 talking-avatar clips (selfie / talking_head /
podcast / dual_cast).

Why this exists: the v1 prompt was one run-on paragraph (descriptor + voice +
camera + delivery + line). Real campaigns showed what it never controlled:
  * no audio layer at all (room tone / mic character) -> studio-clean "AI" voice
    and mismatched noise floors at every clip seam;
  * no "no subtitles" guard -> Veo sometimes burns the quoted line as captions;
  * no timing -> lines started late, ran into the 8s cap and got cut mid-word,
    or Veo filled leftover seconds with stray ad-libbed words;
  * "completely static unmoving frame" on a phone selfie (real phones drift);
  * flat "soft even lighting" (reads as synthetic), no skin/eye/body cues;
  * a "Continuing as the same person..." phrase that asks Veo for memory it
    does not have.

v2 builds the prompt as labeled blocks in a fixed order, from a realism preset
(overridable per job) plus the job's own scene/camera text. Everything shared
across clips is inserted verbatim into every clip (the only real consistency
lever, see SKILL.md). Old jobs keep working: set "prompt_style": "legacy" to get
the exact v1 output.
"""

import re

CLIP_SECONDS = 8.0          # Veo renders a fixed ~8s per clip
LEAD_IN_S = 0.5             # breath / glance before the first word
TAIL_HOLD_S = 1.0           # closed-mouth hold after the last word (no stray words)
SPEECH_BUDGET_S = CLIP_SECONDS - LEAD_IN_S - TAIL_HOLD_S   # 6.5s of actual speech
DEFAULT_WPM = 150           # calm conversational Spanish
HARD_SPEECH_LIMIT_S = 7.3   # beyond this the line WILL be cut or rushed

POSSESSIVE = {"she": "her", "he": "his", "they": "their"}

# ---------------------------------------------------------------------------
# Realism presets. Each block is one short, concrete instruction. {p} = his/her/their.
# Written to add what the reference image cannot show (motion, sound, timing)
# and to push AWAY from the polished-synthetic look, per references/realism-playbook.md.
# ---------------------------------------------------------------------------

_COMMON = {
    "skin": (
        "Real unretouched skin: visible pores, fine facial hair, small blemishes, slight shine, natural "
        "under-eye shadows, a few flyaway hairs; no beauty filter."
    ),
    "eyes": "Eyes with catchlights, natural blinks, small gaze shifts, brows and cheeks moving with the words.",
    "speech": (
        "Conversational, not reading a script: a soft breath before starting, natural pitch and pace variation, "
        "tiny pauses at commas; every word spoken exactly once, none added, changed or repeated."
    ),
    "timing": (
        "Timing: starts speaking about half a second in, finishes the last word before the final second, then "
        "holds a relaxed closed-mouth look; nothing is said before or after this line."
    ),
    "avoid": "No subtitles, captions, on-screen text, watermark or logo; no extra people or hands.",
}

_PHONE_LIGHT = (
    "One believable light source (window or lamp): one side of the face slightly brighter, soft falloff on the "
    "other; natural contrast, not evenly lit, no ring light."
)
_PHONE_AUDIO = (
    "Audio: voice recorded by the phone microphone with natural small-room tone and light reverb; no music, "
    "no sound effects, no other voices."
)
_PHONE_IMAGE = "Phone-camera look: mild sharpening and compression, natural white balance, no filters or color grade."

PRESETS = {
    # Held by the subject at arm's length: real handheld physics.
    "phone_selfie": {
        **_COMMON,
        "camera": (
            "Phone front camera held at arm's length: natural hand tremor, tiny reframing drift, slight autofocus "
            "and exposure breathing, mild wide-angle lens, no gimbal smoothness."
        ),
        "light": _PHONE_LIGHT,
        "body": (
            "Visible breathing, slight head and shoulder sway, clothing folding as the person moves; one hand holds "
            "the phone out of frame, the other gestures loosely; exactly two hands, five fingers each."
        ),
        "audio": _PHONE_AUDIO,
        "image": _PHONE_IMAGE,
    },
    # Phone propped on something: still, but never robotic-locked.
    "phone_propped": {
        **_COMMON,
        "camera": (
            "Phone propped at chest-to-eye height, nearly still: faintest micro-drift, slight autofocus and "
            "exposure breathing, mild wide-angle lens, no gimbal smoothness."
        ),
        "light": _PHONE_LIGHT,
        "body": (
            "Visible breathing, slight head and shoulder sway, clothing folding as the person moves; both hands free, "
            "gesturing loosely at chest height; exactly two hands, five fingers each."
        ),
        "audio": _PHONE_AUDIO,
        "image": _PHONE_IMAGE,
    },
    # Seated interview / podcast, tripod camera, lav or boom mic.
    "studio_podcast": {
        **_COMMON,
        "camera": "Tripod camera at eye level with subtle natural micro-drift, real lens depth of field, no cinematic moves.",
        "light": (
            "Practical warm lights from the set (lamp, window) with natural falloff on the face; natural contrast, "
            "not evenly lit."
        ),
        "body": (
            "Visible breathing, seated posture shifting slightly, clothing folding as the person moves; hands "
            "gesturing loosely near the table edge; exactly two hands, five fingers each."
        ),
        "audio": (
            "Audio: voice captured by the podcast microphone, warm and close, natural room tone; no music, "
            "no sound effects, no other voices."
        ),
        "image": "Natural video look: mild sharpening, natural white balance, no filters or heavy color grade.",
    },
}

FORMAT_TO_PRESET = {
    "selfie": "phone_selfie",
    "talking_head": "phone_propped",
    "podcast": "studio_podcast",
    "dual_cast": "studio_podcast",
}

BLOCK_KEYS = ("camera", "light", "skin", "eyes", "body", "speech", "timing", "audio", "image", "avoid")


def resolve_realism(job):
    """Returns (preset_name, blocks dict) for the job, or (None, {}) if realism is 'off'.

    job["realism"] may be: absent (preset chosen from format), a preset name, "off",
    or {"preset": "...", "<block>": "override text" | null (drop that block)}.
    """
    spec = job.get("realism")
    if spec == "off":
        return None, {}
    overrides = {}
    if isinstance(spec, dict):
        overrides = {k: v for k, v in spec.items() if k != "preset"}
        name = spec.get("preset") or FORMAT_TO_PRESET.get(job.get("format"), "phone_selfie")
    elif isinstance(spec, str):
        name = spec
    else:
        name = FORMAT_TO_PRESET.get(job.get("format"), "phone_selfie")
    if name not in PRESETS:
        raise ValueError(f"Unknown realism preset '{name}'. Options: {', '.join(PRESETS)} or 'off'.")
    blocks = dict(PRESETS[name])
    for key, val in overrides.items():
        if key not in BLOCK_KEYS:
            raise ValueError(f"Unknown realism block '{key}'. Options: {', '.join(BLOCK_KEYS)}.")
        if val is None:
            blocks.pop(key, None)
        else:
            blocks[key] = val
    return name, blocks


def _sentence(text):
    text = (text or "").strip()
    if text and not text.endswith((".", "!", "?", '"')):
        text += "."
    return text


def build_prompt_v2(job, clip, character, continuous_take_suffix, default_accent, has_multi_ref=False):
    """Labeled-block Veo prompt for one talking clip. Order matters: what the shot IS
    (setting, subject, camera, light, look) -> what happens (performance, line) ->
    how it sounds (voice, audio) -> guards (timing, avoid)."""
    _, blocks = resolve_realism(job)
    pronoun = character.get("pronoun", "she")
    poss = POSSESSIVE.get(pronoun, "their")
    fmt = lambda s: s.replace("{p}", poss)

    lines = []

    # A clip's own scene_lock overrides the job-level one -- pairs with a
    # character's "avatar_variant" (a second reference photo/setting) so a long
    # campaign can vary location without losing the realism preset. See
    # references/realism-playbook.md "Scene variety across a long campaign".
    scene = (clip.get("scene_lock") or job.get("scene_lock") or "").strip()
    if scene:
        lines.append("Setting: " + _sentence(scene))

    visual_override = (clip.get("visual_override") or "").strip()
    subject = visual_override or character["avatar_descriptor"].strip()
    if not visual_override:
        subject = _sentence(subject) + " Same person, outfit, hairstyle, room and light as in the reference image."
    lines.append("Subject: " + subject)

    camera = (job.get("camera_realism") or "").strip()
    cam_parts = []
    if camera:
        cam_parts.append(_sentence(camera))
    if blocks.get("camera"):
        cam_parts.append(fmt(blocks["camera"]))
    cam_text = " ".join(cam_parts)
    if "continuous take" not in cam_text.lower() and "no cuts" not in cam_text.lower():
        cam_text += " " + continuous_take_suffix
    lines.append("Camera: " + cam_text.strip())

    look = " ".join(fmt(blocks[k]) for k in ("light", "skin", "eyes", "image") if blocks.get(k))
    if look:
        lines.append("Look: " + look)

    perf = []
    if clip.get("pre_action"):
        perf.append(_sentence(clip["pre_action"]))
    perf.append(_sentence(clip["delivery"]))
    if blocks.get("body"):
        perf.append(fmt(blocks["body"]))
    lines.append("Performance: " + " ".join(perf))

    pron_cap = pronoun.capitalize() if pronoun in ("she", "he") else "They"
    dialogue = f'{pron_cap} says in Spanish: "{clip["dialogue"].strip()}"'
    post = clip.get("post_dialogue_action")
    lines.append("Dialogue: " + dialogue + (" " + post.strip() if post else ""))

    voice = character["voice_profile"].strip()
    accent = character.get("accent", default_accent)
    if "accent" not in voice.lower() and "spanish" not in voice.lower():
        voice += " " + accent
    voice_parts = [_sentence(voice)]
    if blocks.get("speech"):
        voice_parts.append(blocks["speech"])
    lines.append("Voice: " + " ".join(voice_parts))

    if blocks.get("audio"):
        lines.append(fmt(blocks["audio"]))
    if blocks.get("timing"):
        lines.append(blocks["timing"])

    if has_multi_ref:
        lines.append(
            "The shot shows ONLY this one real person, normally and continuously, in a single unbroken take -- "
            "never a grid, contact sheet, collage, multiple angles, or duplicated/ghosted faces at any point, "
            "including the very end of the clip."
        )
    if blocks.get("avoid"):
        lines.append(blocks["avoid"])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lint: catches the mistakes that cost real money BEFORE submitting anything.
# ---------------------------------------------------------------------------

POLISH_WORDS = re.compile(
    r"\b(cinematic|flawless|perfect(?:ly)?|stunning|beautiful|gorgeous|glowing|hyper-?realistic|ultra[- ]?hd|"
    r"4k|8k|masterpiece|studio lighting|professional videography)\b",
    re.IGNORECASE,
)
STATIC_LOCK = re.compile(r"\b(completely static|static unmoving|unmoving frame|perfectly still|no movement at all)\b", re.IGNORECASE)
NAMED_NEGATIVES = re.compile(r"\bno (?:car|vehicle|seats?|windows?|furniture|people|person|plants?)\b", re.IGNORECASE)


def speech_wpm(job, character):
    if character.get("speech_wpm"):
        return float(character["speech_wpm"])
    m = re.search(r"(\d{2,3})\s*words per minute", character.get("voice_profile", ""), re.IGNORECASE)
    if m:
        return float(m.group(1))
    return float(job.get("speech_wpm", DEFAULT_WPM))


def count_words(text):
    return len(re.findall(r"[\wÀ-ÿ]+", text or "", re.UNICODE))


PACE_SAFETY = 1.08  # measured: a voice described as 185 wpm actually ran ~171 wpm (19 words = 6.7s, not 6.2s)


def est_speech_seconds(text, wpm):
    """Estimated spoken duration. Veo runs ~8% slower than the wpm you describe, so pad the estimate."""
    return count_words(text) / (wpm / 60.0) * PACE_SAFETY


def lint_job(job):
    """Returns list of (level, clip_id_or_None, message); level is 'error' or 'warn'."""
    issues = []
    is_talking = job.get("format") != "voiceover"
    legacy = job.get("prompt_style") == "legacy"
    seen_ids = set()
    prev = {}

    scene_text = " ".join(filter(None, [job.get("camera_realism"), job.get("scene_lock")]))
    if is_talking and scene_text:
        if STATIC_LOCK.search(scene_text) and job.get("format") in ("selfie", "talking_head"):
            issues.append(("warn", None, "camera/scene text locks the frame ('completely static / unmoving'): a real phone selfie always drifts a little. Drop it; the preset adds natural handheld micro-drift."))
        negs = NAMED_NEGATIVES.findall(scene_text)
        if len(negs) >= 2:
            issues.append(("warn", None, f"scene text names objects to exclude ({', '.join(sorted(set(negs)))}). Naming them primes Veo to draw them. Describe what IS there instead (put it in 'scene_lock'), and pick a reference photo that already shows that setting."))
        if POLISH_WORDS.search(scene_text):
            issues.append(("warn", None, f"polish words in camera/scene text ({', '.join(sorted(set(m.lower() for m in POLISH_WORDS.findall(scene_text))))}): they push toward the synthetic look."))

    for clip in job["clips"]:
        cid = clip["id"]
        if cid in seen_ids:
            issues.append(("error", cid, "duplicate clip id"))
        seen_ids.add(cid)
        char = job["characters"].get(clip.get("character"))
        if char is None:
            issues.append(("error", cid, f"unknown character '{clip.get('character')}'"))
            continue

        variant = clip.get("avatar_variant")
        if variant and variant != "default" and variant not in char.get("variants", {}):
            issues.append(("error", cid, f"avatar_variant '{variant}' is not defined in this character's 'variants' (and isn't 'default')."))

        if not is_talking:
            continue

        clip_scene = (clip.get("scene_lock") or "").strip()
        if clip_scene:
            if STATIC_LOCK.search(clip_scene) and job.get("format") in ("selfie", "talking_head"):
                issues.append(("warn", cid, "this clip's scene_lock locks the frame ('completely static / unmoving'): drop it, the preset adds natural handheld micro-drift."))
            if len(NAMED_NEGATIVES.findall(clip_scene)) >= 2:
                issues.append(("warn", cid, "this clip's scene_lock names objects to exclude -- describe what IS there instead."))
            if POLISH_WORDS.search(clip_scene):
                issues.append(("warn", cid, "polish word in this clip's scene_lock."))

        dialogue = clip.get("dialogue", "")
        if '"' in dialogue or "“" in dialogue or "”" in dialogue:
            issues.append(("error", cid, "dialogue contains quote marks; they break the quoted line in the prompt. Remove them."))
        if "\n" in dialogue:
            issues.append(("warn", cid, "dialogue contains a line break."))
        if not clip.get("delivery"):
            issues.append(("error", cid, "missing 'delivery'."))

        wpm = speech_wpm(job, char)
        secs = est_speech_seconds(dialogue, wpm)
        words = count_words(dialogue)
        if secs > HARD_SPEECH_LIMIT_S:
            issues.append(("error", cid, f"~{secs:.1f}s of speech ({words} words @ {wpm:.0f} wpm) will not fit an 8s clip: it will be cut mid-word or rushed. Split at a clause boundary (max ~{int(wpm / 60 * SPEECH_BUDGET_S)} words)."))
        elif secs > SPEECH_BUDGET_S and not legacy:
            issues.append(("warn", cid, f"~{secs:.1f}s of speech ({words} words @ {wpm:.0f} wpm) leaves no closing beat (budget {SPEECH_BUDGET_S:.1f}s). Risk: last word clipped or stray words added. Trim or split."))

        for field in ("delivery", "post_dialogue_action", "pre_action"):
            val = (clip.get(field) or "").strip().lower()
            if val and prev.get((clip.get("character"), field)) == val:
                issues.append(("warn", cid, f"'{field}' is identical to the previous clip of this character; repeated gestures read as a loop. Vary it."))
            if val:
                prev[(clip.get("character"), field)] = val
            if val and POLISH_WORDS.search(val):
                issues.append(("warn", cid, f"polish word in '{field}'."))

    return issues
